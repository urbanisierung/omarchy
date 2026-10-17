#!/usr/bin/env python3
"""Summarize shell history to find candidates for Omarchy commands, aliases and keybindings.

Reads bash, zsh, fish and atuin history (whatever exists), redacts likely
secrets, and prints a Markdown report. Nothing is sent anywhere.

Usage:
  python3 tools/history-report.py                 # report to stdout
  python3 tools/history-report.py -o report.md    # write to file
  python3 tools/history-report.py --top 40 --history ~/.bash_history_old
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent

# Commands that say nothing about workflows on their own.
NOISE = {"ls", "ll", "la", "lsa", "lt", "cd", "clear", "exit", "pwd", "history", "z", "zd", "c", ".."}
PREFIX_TOOLS = {"sudo", "doas", "time", "nohup", "env", "command", "builtin", "exec"}

SECRET_PATTERNS = [
    (re.compile(r"(?i)\b(pass(word)?|passwd|token|secret|api[_-]?key|auth|bearer)\b(\s*[=:]\s*|\s+)\S+"), r"\1=<REDACTED>"),
    (re.compile(r"(?i)(authorization:\s*)(bearer\s+)?\S+"), r"\1<REDACTED>"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[abpr]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})\b"), "<REDACTED>"),
    (re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+@"), r"\1<REDACTED>@"),
    (re.compile(r"\b[A-Za-z0-9+/_=-]{40,}\b"), "<LONG-STRING>"),
]


def redact(cmd: str) -> str:
    for pattern, repl in SECRET_PATTERNS:
        cmd = pattern.sub(repl, cmd)
    return cmd.replace(str(HOME), "~")


# ---------- loaders: each yields dicts {cmd, ts?, cwd?, exit?, dur?} ----------

def load_bash(path: Path):
    ts = None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("#") and line[1:].isdigit():
            ts = int(line[1:])
            continue
        if line.strip():
            yield {"cmd": line.strip(), "ts": ts}
            ts = None


def load_zsh(path: Path):
    buf = ""
    for line in path.read_bytes().decode(errors="replace").splitlines():
        buf = f"{buf}\n{line}" if buf else line
        if buf.endswith("\\"):
            buf = buf[:-1]
            continue
        m = re.match(r"^: (\d+):\d+;(.*)$", buf, re.S)
        if m:
            yield {"cmd": m.group(2).strip(), "ts": int(m.group(1))}
        elif buf.strip():
            yield {"cmd": buf.strip(), "ts": None}
        buf = ""


def load_fish(path: Path):
    cur = None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("- cmd: "):
            if cur:
                yield cur
            cur = {"cmd": line[7:].replace("\\n", "\n").strip(), "ts": None}
        elif cur and line.strip().startswith("when: "):
            cur["ts"] = int(line.split(":", 1)[1])
    if cur:
        yield cur


def load_atuin(path: Path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        for cmd, ts, cwd, ex, dur in con.execute(
            "select command, timestamp, cwd, exit, duration from history where deleted_at is null order by timestamp"
        ):
            yield {"cmd": cmd.strip(), "ts": ts // 1_000_000_000, "cwd": cwd, "exit": ex, "dur": dur}
    finally:
        con.close()


def discover(extra: list[str], all_sources: bool):
    sources = []
    atuin = HOME / ".local/share/atuin/history.db"
    if atuin.exists():
        sources.append(("atuin", atuin, load_atuin))
        if not all_sources and not extra:
            # atuin usually imported the shell history already; avoid double counts.
            return sources
    histfile = os.environ.get("HISTFILE")
    candidates = [
        ("bash", HOME / ".bash_history", load_bash),
        ("zsh", HOME / ".zsh_history", load_zsh),
        ("zsh", HOME / ".zhistory", load_zsh),
        ("fish", HOME / ".local/share/fish/fish_history", load_fish),
    ]
    if histfile:
        candidates.insert(0, ("zsh" if "zsh" in histfile else "bash", Path(histfile), load_zsh if "zsh" in histfile else load_bash))
    for p in extra:
        path = Path(p).expanduser()
        loader = load_fish if "fish" in path.name else load_zsh if "zsh" in path.name or "zhist" in path.name else load_bash
        candidates.insert(0, (path.name, path, loader))
    seen = set()
    for name, path, loader in candidates:
        if path.exists() and path.resolve() not in seen:
            seen.add(path.resolve())
            sources.append((name, path, loader))
    return sources


# ---------- analysis helpers ----------

def head_words(cmd: str, n: int) -> str:
    try:
        words = shlex.split(cmd, comments=False)
    except ValueError:
        words = cmd.split()
    for i, w in enumerate(words):
        if w in ("&&", "||", "|", ";", "&"):
            words = words[:i]
            break
    while words and (words[0] in PREFIX_TOOLS or re.match(r"^\w+=", words[0])):
        words = words[1:]
    words = [w for w in words if not w.startswith("-")] if n > 1 else words
    return " ".join(words[:n])


def base(cmd: str) -> str:
    return head_words(cmd, 1)


def known_aliases() -> set[str]:
    names = set()
    for f in ("default/bash/aliases", "default/bash/functions"):
        p = REPO / f
        if p.exists():
            txt = p.read_text(errors="replace")
            names |= set(re.findall(r"^\s*alias\s+([\w.-]+)=", txt, re.M))
            names |= set(re.findall(r"^\s*([\w-]+)\s*\(\)", txt, re.M))
    bindir = REPO / "bin"
    if bindir.exists():
        names |= {p.name for p in bindir.iterdir()}
    return names


def table(rows, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ⏎ ") for c in r) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history", action="append", default=[], help="extra history file (repeatable)")
    ap.add_argument("--top", type=int, default=30, help="rows per section")
    ap.add_argument("--min-len", type=int, default=25, help="min length for 'long repeated command' section")
    ap.add_argument("--all-sources", action="store_true", help="read shell history files even when atuin exists")
    ap.add_argument("-o", "--output", help="write report here instead of stdout")
    args = ap.parse_args()

    sources = discover(args.history, args.all_sources)
    entries = []
    for name, path, loader in sources:
        try:
            for e in loader(path):
                e["cmd"] = redact(e["cmd"])
                if e["cmd"]:
                    entries.append(e)
        except Exception as exc:  # keep going with other sources
            print(f"warning: could not read {path}: {exc}")

    if not entries:
        print("No history found. Pass a file with --history.")
        return

    N = args.top
    cmds = [e["cmd"] for e in entries]
    known = known_aliases()
    out = ["# Shell history report", ""]
    out.append("Sources: " + ", ".join(f"{n} ({p.name})" for n, p, _ in sources) + f" — {len(cmds)} commands, {len(set(cmds))} unique.")
    out.append("")

    # 1. Programs
    progs = Counter(base(c) for c in cmds)
    out += ["## Most used programs", "", table(progs.most_common(N), ["program", "count"]), ""]

    # 2. Subcommand patterns (program + first non-flag args)
    for depth in (2, 3):
        pats = Counter(head_words(c, depth) for c in cmds if len(head_words(c, depth).split()) == depth)
        out += [f"## Top {depth}-word patterns", "", table(pats.most_common(N), ["pattern", "count"]), ""]

    # 3. Long exact commands typed repeatedly -> alias / script candidates
    exact = Counter(c for c in cmds if len(c) >= args.min_len)
    rows = [(n, len(c), f"`{c}`") for c, n in exact.most_common(N * 3) if n >= 3]
    rows.sort(key=lambda r: r[0] * r[1], reverse=True)  # keystrokes saved
    out += ["## Long commands typed repeatedly (alias/script candidates)", "",
            "Sorted by count × length, i.e. keystrokes you'd save.", "",
            table(rows[:N], ["count", "len", "command"]), ""]

    # 4. Sequences: commands that tend to follow each other -> workflow candidates
    seq2, seq3 = Counter(), Counter()
    keys = [head_words(c, 2) for c in cmds]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a != b and base(a) not in NOISE and base(b) not in NOISE:
            seq2[(a, b)] += 1
            if i + 2 < len(keys) and keys[i + 2] not in (a, b) and base(keys[i + 2]) not in NOISE:
                seq3[(a, b, keys[i + 2])] += 1
    out += ["## Recurring sequences (workflow candidates)", "",
            table([(n, " → ".join(s)) for s, n in seq2.most_common(N) if n >= 3], ["count", "pair"]), "",
            table([(n, " → ".join(s)) for s, n in seq3.most_common(N) if n >= 3], ["count", "triple"]), ""]

    # 5. System administration areas typical for an Omarchy/Fedora setup
    areas = {
        "packages (dnf/flatpak/rpm/copr)": r"^(sudo\s+)?(dnf|dnf5|flatpak|rpm|rpm-ostree)\b",
        "services (systemctl/journalctl)": r"^(sudo\s+)?(systemctl|journalctl)\b",
        "hyprland (hyprctl/hypr*)": r"^(hyprctl|hyprpm|hyprpaper|hyprlock|hypridle|waybar|pkill\s+waybar|killall\s+waybar)\b",
        "network/bluetooth": r"^(sudo\s+)?(nmcli|nmtui|iwctl|bluetoothctl|bt|tailscale|wg|wg-quick)\b",
        "display/audio/power": r"^(wpctl|pactl|pamixer|brightnessctl|wlr-randr|powerprofilesctl|upower|apple-display-brightness)\b",
        "containers": r"^(sudo\s+)?(docker|podman|toolbox|distrobox|kubectl|k9s)\b",
        "config editing": r"^(n|nvim|vim|vi|nano|code)\s+.*(\.config|hypr|waybar|omarchy|\.bashrc|\.zshrc)",
        "omarchy": r"^(omarchy-\S+|~/.local/share/omarchy)",
    }
    out += ["## System-management areas", ""]
    for label, rx in areas.items():
        r = re.compile(rx)
        hits = Counter(head_words(c, 3) for c in cmds if r.search(c))
        if hits:
            total = sum(hits.values())
            top = ", ".join(f"`{k}` ({v})" for k, v in hits.most_common(8))
            out.append(f"- **{label}** — {total}×: {top}")
    out.append("")

    # 6. Atuin-only extras: failures, slow commands, directories
    rich = [e for e in entries if "exit" in e]
    if rich:
        fails = Counter(head_words(e["cmd"], 2) for e in rich if e.get("exit") not in (0, None, -1))
        out += ["## Frequently failing commands (atuin)", "", table(fails.most_common(N), ["pattern", "failures"]), ""]
        slow = defaultdict(list)
        for e in rich:
            if e.get("dur") and e["dur"] > 0:
                slow[head_words(e["cmd"], 2)].append(e["dur"] / 1e9)
        rows = sorted(((k, len(v), f"{sum(v)/len(v):.1f}s") for k, v in slow.items() if len(v) >= 3 and sum(v) / len(v) > 5),
                      key=lambda r: -float(r[2][:-1]))
        out += ["## Slow recurring commands (atuin, avg > 5s)", "", table(rows[:N], ["pattern", "runs", "avg"]), ""]
        dirs = Counter(redact(e["cwd"]) for e in rich if e.get("cwd"))
        out += ["## Most used working directories (atuin)", "", table(dirs.most_common(N), ["dir", "commands"]), ""]
    else:
        cds = Counter(redact(c.split(None, 1)[1]) for c in cmds if re.match(r"^(cd|z|zd)\s+\S", c))
        out += ["## Most visited directories (cd/z)", "", table(cds.most_common(N), ["dir", "count"]), ""]

    # 7. Already covered?
    covered = [(k, v) for k, v in progs.most_common(N * 2) if k in known]
    out += ["## Programs already covered by Omarchy aliases/functions/bin", "",
            ", ".join(f"`{k}` ({v})" for k, v in covered) or "_none_", ""]

    report = "\n".join(out)
    if args.output:
        Path(args.output).write_text(report)
        print(f"Wrote {args.output}. Review it for anything private before sharing.")
    else:
        print(report)


if __name__ == "__main__":
    main()
