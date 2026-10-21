"""Static shortcut extraction. Configuration is data here, never executable code."""

import glob
import json
import os
import re
import shlex
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

TOKEN = re.compile(
    r"--\[(=*)\[.*?\]\1\]|--[^\n]*|\[(=*)\[.*?\]\2\]|"
    r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|"
    r"[A-Za-z_][\w.]*|\d+|\.\.|[^\s]",
    re.DOTALL,
)
MODIFIER_KEYS = (
    ("Super", 64),
    ("Ctrl", 4),
    ("Alt", 8),
    ("Shift", 1),
    ("Caps", 2),
    ("Mod2", 16),
    ("Mod3", 32),
    ("Mod5", 128),
)
MODIFIERS = {name.upper(): bit for name, bit in MODIFIER_KEYS}
MODIFIERS.update({"WIN": 64, "LOGO": 64, "MOD4": 64, "CONTROL": 4})
KEY_NAMES = {
    "return": "Enter",
    "escape": "Esc",
    "space": "Space",
    "backspace": "Backspace",
    "print": "Print",
    "minus": "−",
    "equal": "=",
    "left": "←",
    "right": "→",
    "up": "↑",
    "down": "↓",
    "mouse:272": "Left mouse",
    "mouse:273": "Right mouse",
    "mouse_down": "Scroll down",
    "mouse_up": "Scroll up",
    "xf86audioraisevolume": "Volume up",
    "xf86audiolowervolume": "Volume down",
    "xf86audiomute": "Mute",
    "xf86audiomicmute": "Mic mute",
    "xf86monbrightnessup": "Brightness up",
    "xf86monbrightnessdown": "Brightness down",
    "xf86audionext": "Next track",
    "xf86audioprev": "Previous track",
    "xf86audioplay": "Play / pause",
    "xf86audiopause": "Play / pause",
}


def tokens(text):
    return [
        (m.group(), m.start(), m.end())
        for m in TOKEN.finditer(text)
        if not m.group().startswith("--")
    ]


def literal(value):
    if value[:1] in ("'", '"') and value[-1:] == value[:1]:
        escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
        return re.sub(r"\\(.)", lambda m: escapes.get(m[1], "\\" + m[1]), value[1:-1])
    match = re.fullmatch(r"\[(=*)\[(.*?)\]\1\]", value, re.DOTALL)
    return match[2].removeprefix("\n") if match else None


def resolve(expression, variables):
    """Resolve literals, string variables, concatenation and getenv; nothing else."""
    parts = [t[0] for t in tokens(expression)]
    result = []
    i = 0
    while i < len(parts):
        value = literal(parts[i])
        if value is not None:
            i += 1
        elif parts[i] in variables:
            value = variables[parts[i]]
            i += 1
        elif (
            parts[i] == "os.getenv"
            and i + 3 < len(parts)
            and parts[i + 1] == "("
            and parts[i + 3] == ")"
        ):
            name = literal(parts[i + 2])
            value = os.environ.get(name) if name else None
            i += 4
        else:
            return None
        if value is None:
            return None
        result.append(value)
        if i == len(parts):
            return "".join(result)
        if parts[i] != "..":
            return None
        i += 1
    return None


def call_args(items, opening, text):
    """Split balanced calls, including nested tables and Lua callbacks."""
    stack = [")"]
    args = []
    start = items[opening][2]
    for i in range(opening + 1, len(items)):
        word, left, right = items[i]
        if word in ("(", "{", "["):
            stack.append({"(": ")", "{": "}", "[": "]"}[word])
        elif word in ("function", "if", "do"):
            stack.append("end")
        elif word == "repeat":
            stack.append("until")
        elif word == stack[-1]:
            stack.pop()
            if not stack:
                args.append(text[start:left].strip())
                return args, i
        elif word == "," and len(stack) == 1:
            args.append(text[start:left].strip())
            start = right
    raise ValueError("Unclosed Lua call")


def identity(combo, submap=""):
    parts = re.split(r"\s*\+\s*", combo)
    mask = 0
    for modifier in parts[:-1]:
        mask |= MODIFIERS.get(modifier.upper(), 0)
    return mask, parts[-1].lower(), submap


def keycaps(combo):
    mask, key, _ = identity(combo)
    modifiers = [label for label, bit in MODIFIER_KEYS if mask & bit]
    # XKB keycodes 10–19 are the physical number row, independent of de/us layout.
    numbers = {f"code:{n}": str((n - 9) % 10) for n in range(10, 20)}
    return modifiers + [
        numbers.get(key, KEY_NAMES.get(key, key.upper() if len(key) == 1 else key))
    ]


def describe(action, command, combo, submap):
    key = identity(combo)[1]
    if "hl.plugin.hyprtasking" in action:
        if ".move(" in action:
            return (
                "Workspaces",
                f"Navigate overview {key}",
                "While the workspace overview is open",
            )
        return (
            "Workspaces",
            "Close workspace overview"
            if key == "escape"
            else "Toggle workspace overview",
            "",
        )
    match = re.search(r"hl\.dsp\.([\w.]+)\((.*)\)\s*$", action, re.DOTALL)
    if match:
        dispatcher, arg = match.groups()
        arg = arg.strip()
        workspace = re.search(r"workspace\s*=\s*([\"']?)([\w+\-]+)\1", arg)
        direction = re.search(r"direction\s*=\s*[\"\'](\w+)", arg)
        if workspace:
            target = {"e+1": "next workspace", "e-1": "previous workspace"}.get(
                workspace[2], f"workspace {workspace[2]}"
            )
            return (
                "Workspaces",
                ("Move window to " if dispatcher == "window.move" else "Switch to ")
                + target,
                "",
            )
        if direction:
            return (
                "Windows",
                ("Swap window " if dispatcher == "window.swap" else "Focus window ")
                + direction[1],
                "",
            )
        if dispatcher == "window.resize":
            x = re.search(r"x\s*=\s*(-?\d+)", arg)
            y = re.search(r"y\s*=\s*(-?\d+)", arg)
            amount = int(x[1]) if x and int(x[1]) else int(y[1]) if y else 0
            if amount:
                axis = "width" if x and int(x[1]) else "height"
                return (
                    "Windows",
                    f"{'Increase' if amount > 0 else 'Decrease'} window {axis} by {abs(amount)} px",
                    "",
                )
            return "Windows", "Resize window by dragging", "Hold the shortcut and drag"
        simple = {
            "window.close": "Close focused window",
            "window.fullscreen": "Toggle fullscreen",
            "window.pseudo": "Toggle pseudo tiling",
            "window.drag": "Move window by dragging",
            "exit": "Log out of Hyprland",
        }
        if dispatcher in simple:
            return (
                "Session" if dispatcher == "exit" else "Windows",
                simple[dispatcher],
                "",
            )
        if dispatcher == "layout":
            label = {
                "movetoroot": "Move window to layout root",
                "togglesplit": "Toggle split direction",
                "preselect b": "Place next window below",
                "preselect r": "Place next window to the right",
            }.get(literal(arg), f"Change layout: {arg}")
            return "Windows", label, ""
        if dispatcher == "submap":
            target = literal(arg) or arg
            label = (
                "Leave shortcut mode"
                if target == "reset"
                else "Enter resize mode"
                if target == "resize"
                else "Open power menu"
                if "shutdown" in target
                else f"Enter {target} mode"
            )
            return (
                "Session"
                if "shutdown" in target or "shutdown" in submap
                else "Windows",
                label,
                "",
            )
    rules = [
        ("translate_manager.py offline", "Tools", "Translate text offline"),
        ("translate_manager.py deepl", "Tools", "Translate text with DeepL"),
        ("transcribe.sh", "Tools", "Transcribe speech"),
        ("omarchy-show-keybindings", "Tools", "Browse keyboard shortcuts"),
        ("omarchy-show-commands", "Tools", "Browse commands"),
        ("omarchy-show-prompts", "Tools", "Browse saved prompts"),
        ("omarchy-show-repos", "Tools", "Browse repositories"),
        ("omarchy-claude-usage", "Tools", "Show Claude usage"),
        ("omarchy-claude-code", "Tools", "Open Claude Code"),
        ("omarchy-remind", "Tools", "Create a reminder"),
        ("makoctl dismiss", "Tools", "Dismiss current notification"),
        ("makoctl invoke", "Tools", "Open notification actions"),
        ("kaihuman-palette-toggle", "Tools", "Toggle Kaihuman palette"),
        ("copyq", "Tools", "Toggle CopyQ clipboard history"),
        ("clipse", "Tools", "Open Clipse clipboard history"),
        ("spotlight.sh", "Tools", "Open Spotlight search"),
        ("wofi", "Applications", "Open application launcher"),
        ("lazydocker", "Applications", "Open Docker dashboard"),
        ("nvim", "Applications", "Open Neovim"),
        ("btop", "Applications", "Open system monitor"),
        ("nautilus", "Applications", "Open file manager"),
        ("1password", "Applications", "Open password manager"),
        ("signal-desktop", "Applications", "Open Signal"),
        ("code -", "Applications", "Open Visual Studio Code"),
        ("waybar", "Appearance", "Toggle status bar"),
        ("swaybg-next", "Appearance", "Next wallpaper"),
        ("omarchy-theme-next", "Appearance", "Next desktop theme"),
        ("omarchy-powerprofile", "Session", "Switch power profile"),
        ("lock-session", "Session", "Lock screen"),
        ("systemctl suspend", "Session", "Suspend computer"),
        ("reboot", "Session", "Restart computer"),
        ("systemctl poweroff", "Session", "Shut down computer"),
        (
            "omarchy-airpods-toggle",
            "Media & brightness",
            "Connect / disconnect AirPods",
        ),
        ("playerctl next", "Media & brightness", "Next track"),
        ("playerctl previous", "Media & brightness", "Previous track"),
        ("playerctl play-pause", "Media & brightness", "Play / pause media"),
        ("@DEFAULT_AUDIO_SOURCE@", "Media & brightness", "Mute / unmute microphone"),
        ("wpctl set-mute", "Media & brightness", "Mute / unmute speakers"),
        (
            "wpctl set-volume",
            "Media & brightness",
            "Increase volume" if "5%+" in command else "Decrease volume",
        ),
        (
            "brightnessctl",
            "Media & brightness",
            "Increase display brightness"
            if "5%+" in command
            else "Decrease display brightness",
        ),
        (
            "apple-display-brightness",
            "Media & brightness",
            "Increase Apple display brightness"
            if " +" in command
            else "Decrease Apple display brightness",
        ),
        ("satty", "Screenshots", "Capture and annotate a region"),
        ("hyprshot -m region", "Screenshots", "Screenshot a region"),
        ("hyprshot -m window", "Screenshots", "Screenshot a window"),
        ("hyprshot -m output", "Screenshots", "Screenshot a display"),
        ("hyprpicker", "Screenshots", "Pick and copy a screen color"),
    ]
    for needle, category, label in rules:
        if needle in command:
            return category, label, ""
    url = re.search(r"https?://([^/\s\"']+)([^\s\"']*)", command)
    if url:
        name = {
            "chatgpt.com": "ChatGPT",
            "grok.com": "Grok",
            "youtube.com": "YouTube",
            "web.whatsapp.com": "WhatsApp",
            "messages.google.com": "Google Messages",
            "x.com": "X",
        }.get(url[1], url[1])
        return (
            "Applications",
            f"Open {name}" + (" post composer" if "/compose/post" in url[2] else ""),
            "",
        )
    if command:
        if any(browser in command for browser in ("chrome", "chromium", "firefox")):
            return "Applications", "Open web browser", ""
        if command in ("ghostty", "alacritty", "kitty", "foot"):
            return "Applications", "Open terminal", ""
        try:
            executable = Path(shlex.split(command)[0]).name
        except (ValueError, IndexError):
            executable = command
        return "Applications", f"Run {executable}", ""
    return "Other", "Custom action", "Expand for implementation details"


class Reader:
    def __init__(self):
        self.variables = {}
        self.bindings = []
        self.sources = []
        self.warnings = []
        self.stack = []
        self.required = set()
        self.runtime_unresolved = []

    def read(self, path, submap=""):
        path = Path(path).expanduser().resolve()
        if path in self.stack:
            self.warnings.append(f"Recursive include skipped: {path}")
            return
        try:
            text = path.read_text()
        except OSError as error:
            self.warnings.append(f"Cannot read {path}: {error.strerror}")
            return
        if str(path) not in self.sources:
            self.sources.append(str(path))
        self.stack.append(path)
        if path.suffix == ".conf":
            self.hyprlang(text, path, submap)
        else:
            self.lua(text, path, submap)
        self.stack.pop()

    def include(self, expression, path, submap, module=False):
        value = resolve(expression, self.variables)
        if value is None:
            self.warnings.append(f"Unresolved include in {path}: {expression}")
            return
        if module:
            relative = value.replace(".", "/")
            candidates = [
                path.parent / f"{relative}.lua",
                path.parent / relative / "init.lua",
            ]
            target = next((p for p in candidates if p.exists()), None)
            if target is None:
                self.warnings.append(f"Unresolved Lua module in {path}: {value}")
                return
            if target.resolve() in self.required:
                return
            self.required.add(target.resolve())
        else:
            target = Path(os.path.expandvars(value)).expanduser()
            if not target.is_absolute():
                target = path.parent / target
        self.read(target, submap)

    def add(
        self, combo, action, options, path, line, submap, command="", annotation=""
    ):
        category, description, context = describe(action, command, combo, submap)
        explicit = re.search(
            r"description\s*=\s*(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')", options
        )
        if explicit:
            description = literal(explicit[1])
        if annotation:
            parts = annotation.split("|", 1)
            if len(parts) == 2:
                category, description = (part.strip() for part in parts)
            else:
                description = annotation.strip()
        flags = re.findall(r"(\w+)\s*=\s*true", options)
        self.bindings.append(
            {
                "keys": combo,
                "keycaps": keycaps(combo),
                "description": description,
                "category": category,
                "submap": submap,
                "context": context,
                "action": action,
                "command": command,
                "flags": flags,
                "source": str(path),
                "line": line,
                "status": "not_checked",
            }
        )

    def lua(self, text, path, submap="", offset=0):
        items = tokens(text)
        i = 0
        while i < len(items):
            word, start, _ = items[i]
            line = offset + text.count("\n", 0, start) + 1
            if (
                word
                in ("hl.bind", "hl.unbind", "hl.define_submap", "dofile", "require")
                and i + 1 < len(items)
                and items[i + 1][0] == "("
            ):
                try:
                    args, end = call_args(items, i + 1, text)
                except ValueError as error:
                    self.warnings.append(f"{path}:{line}: {error}")
                    return
                if word in ("dofile", "require"):
                    self.include(args[0], path, submap, module=word == "require")
                elif word == "hl.define_submap" and len(args) >= 2:
                    name = resolve(args[0], self.variables)
                    if name is None:
                        self.warnings.append(
                            f"{path}:{line}: Unresolved submap {args[0]}"
                        )
                    else:
                        body_start = text.find(args[1], items[i + 1][2])
                        self.lua(
                            args[1],
                            path,
                            name,
                            offset + text.count("\n", 0, body_start),
                        )
                else:
                    combo = resolve(args[0], self.variables)
                    if combo is None:
                        self.warnings.append(
                            f"{path}:{line}: Unresolved shortcut {args[0]}"
                        )
                    elif word == "hl.unbind":
                        self.bindings = [
                            b
                            for b in self.bindings
                            if identity(b["keys"], b["submap"])
                            != identity(combo, submap)
                        ]
                    elif len(args) >= 2:
                        action = args[1]
                        command = ""
                        if action.startswith("hl.dsp.exec_cmd("):
                            command = (
                                resolve(
                                    action[len("hl.dsp.exec_cmd(") : -1], self.variables
                                )
                                or ""
                            )
                        preceding = text[:start].rstrip().splitlines()
                        annotation = ""
                        if preceding and "-- @shortcut " in preceding[-1]:
                            annotation = preceding[-1].split("-- @shortcut ", 1)[1]
                        self.add(
                            combo,
                            action,
                            args[2] if len(args) > 2 else "",
                            path,
                            line,
                            submap,
                            command,
                            annotation,
                        )
                i = end + 1
                continue
            if (
                re.fullmatch(r"[A-Za-z_]\w*", word)
                and i + 1 < len(items)
                and items[i + 1][0] == "="
            ):
                end = text.find("\n", items[i + 1][2])
                expression = text[items[i + 1][2] : end if end >= 0 else len(text)]
                value = resolve(expression, self.variables)
                if value is not None:
                    self.variables[word] = value
            i += 1

    def hyprlang(self, text, path, submap):
        for line, raw in enumerate(text.splitlines(), 1):
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            name, value = (part.strip() for part in raw.split("=", 1))
            value = re.sub(r"\$(\w+)", lambda m: self.variables.get(m[1], m[0]), value)
            if name.startswith("$"):
                self.variables[name[1:]] = value
            elif name == "source":
                target = Path(os.path.expandvars(value)).expanduser()
                if not target.is_absolute():
                    target = path.parent / target
                matches = sorted(glob.glob(str(target)))
                if not matches:
                    self.warnings.append(f"{path}:{line}: Include not found: {value}")
                for included in matches:
                    self.read(included, submap)
            elif name == "submap":
                submap = "" if value == "reset" else value
            elif re.fullmatch(r"bind[a-z]*", name):
                fields = [
                    part.strip()
                    for part in value.split(",", 4 if "d" in name[4:] else 3)
                ]
                description = (
                    fields.pop(2) if "d" in name[4:] and len(fields) == 5 else ""
                )
                if len(fields) != 4:
                    self.warnings.append(f"{path}:{line}: Invalid binding")
                    continue
                mods, key, dispatcher, argument = fields
                combo = " + ".join(mods.split() + [key])
                self.add(
                    combo,
                    f"{dispatcher} {argument}".strip(),
                    "",
                    path,
                    line,
                    submap,
                    argument if dispatcher == "exec" else "",
                    description,
                )
                self.bindings[-1]["flags"] = list(name[4:])
            elif name == "unbind":
                parts = value.split(",", 1)
                if len(parts) == 2:
                    combo = " + ".join(parts[0].split() + [parts[1].strip()])
                    self.bindings = [
                        b
                        for b in self.bindings
                        if identity(b["keys"], b["submap"]) != identity(combo, submap)
                    ]


def reconcile(reader, active):
    """Retain unmatched runtime entries, including shortcuts generated in Lua loops."""
    # Some Lua-enabled Hyprland versions omit both key and keycode for code:N.
    # Never infer their identity from registration order or duplicate blank rows.
    reader.runtime_unresolved = [
        b for b in active if not b.get("key") and not b.get("keycode")
    ]
    active = [b for b in active if b.get("key") or b.get("keycode")]
    if reader.runtime_unresolved:
        reader.warnings.append(
            f"Hyprland did not report keys for {len(reader.runtime_unresolved)} runtime bindings. "
            "Their configured shortcuts are shown; live key verification is unavailable."
        )

    def live_combo(binding):
        mods = [
            name.upper()
            for name, bit in MODIFIER_KEYS
            if binding.get("modmask", 0) & bit
        ]
        key = (
            f"code:{binding['keycode']}"
            if binding.get("keycode")
            else binding.get("key", "unknown")
        )
        return " + ".join(mods + [key])

    counts = Counter(identity(live_combo(b), b.get("submap", "")) for b in active)
    for binding in reader.bindings:
        key = identity(binding["keys"], binding["submap"])
        binding["status"] = "active" if counts[key] else "configured_only"
        if not counts[key] and any(
            b.get("modmask", 0) == key[0] and b.get("submap", "") == key[2]
            for b in reader.runtime_unresolved
        ):
            binding["status"] = "unverified"
        if counts[key]:
            counts[key] -= 1
    for binding in active:
        combo = live_combo(binding)
        submap = binding.get("submap", "")
        key = identity(combo, submap)
        if not counts[key]:
            continue
        counts[key] -= 1
        dispatcher = binding.get("dispatcher", "")
        argument = binding.get("arg", "")
        reader.add(
            combo,
            f"{dispatcher} {argument}".strip(),
            "",
            "",
            0,
            submap,
            argument if dispatcher == "exec" else "",
            binding.get("description", ""),
        )
        entry = reader.bindings[-1]
        entry["status"] = "runtime_only"
        entry["context"] = "Registered at runtime; source could not be resolved"
        if not binding.get("description") and dispatcher == "__lua":
            entry["description"] = "Dynamic Lua shortcut (no description)"
        entry["flags"] = [
            flag
            for flag in ("locked", "mouse", "release", "repeat", "non_consuming")
            if binding.get(flag)
        ]


def generate(configs, live=True):
    reader = Reader()
    for path in configs:
        if not path.expanduser().is_file():
            raise ValueError(f"Config not found: {path}")
        reader.read(path)
    live_checked = False
    if live:
        try:
            result = subprocess.run(
                ["hyprctl", "-j", "binds"],
                capture_output=True,
                text=True,
                check=True,
                timeout=3,
            )
            active = json.loads(result.stdout)
            if not isinstance(active, list) or any(
                not isinstance(b, dict) for b in active
            ):
                raise ValueError("Unexpected hyprctl binding response")
            reconcile(reader, active)
            live_checked = True
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            reader.warnings.append(
                f"Live bindings unavailable; showing configuration only ({error})"
            )
    if not reader.bindings:
        reader.warnings.append("No shortcuts found in the selected configuration")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "roots": [str(path.expanduser().resolve()) for path in configs],
        "sources": reader.sources,
        "live_checked": live_checked,
        "runtime_unresolved": reader.runtime_unresolved,
        "warnings": reader.warnings,
        "bindings": reader.bindings,
    }


def export_json(data, destination):
    destination = Path(destination).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def matches(binding, query):
    haystack = " ".join(
        str(binding.get(field, ""))
        for field in (
            "keys",
            "keycaps",
            "description",
            "category",
            "submap",
            "context",
            "action",
            "command",
            "source",
            "flags",
            "status",
        )
    ).casefold()
    return all(word in haystack for word in query.casefold().replace("+", " ").split())
