#!/usr/bin/env python3
"""Best-effort transpiler: Hyprland hyprlang (.conf) -> Hyprland Lua (hl.* API).

Clean-room implementation (no code taken from any third-party transpiler)
tailored to the hyprlang subset actually used in this repo's config/hypr and
default/hypr files: $variables, source, env, exec-once, monitor, bind*,
submap, 0.53+ windowrule syntax, and nested config blocks (general,
decoration, animations, dwindle, master, misc, gestures, input, xwayland,
ecosystem, plugin, ...).

Directives this script cannot confidently map to the Lua API are emitted as
"-- TODO(manual-migration): ..." comments instead of guessing.

Usage:
    hyprlang-to-lua.py input.conf [-o output.lua] [-r]

    -o output.lua   write Lua to a file; defaults to stdout
    -r, --recursive also transpile every file referenced by a `source = ...`
                    directive (resolved relative to the input file, `~`
                    expanded) into a sibling .lua file next to the output
"""

import argparse
import os
import re
import sys

VAR_RE = re.compile(r"\$([A-Za-z0-9_-]+)")
COLOR_RE = re.compile(r"rgba?\([^)]*\)")
NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
# Bare "0"/"1" are intentionally excluded: hyprlang uses plain integers for
# many numeric/enum fields (e.g. sensitivity, follow_mouse), not just
# booleans, so guessing bool there would silently corrupt numeric values.
BOOL_TRUE = {"true", "yes", "on"}
BOOL_FALSE = {"false", "no", "off"}


def sanitize_ident(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def lua_string(text):
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def strip_comment(line):
    """Split a line into (code, comment) at the first '#' outside quotes."""
    in_squote = in_dquote = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_dquote:
            in_squote = not in_squote
        elif ch == '"' and not in_squote:
            in_dquote = not in_dquote
        elif ch == "#" and not in_squote and not in_dquote:
            return line[:i].rstrip(), line[i:].rstrip()
    return line.rstrip(), ""


def render_value_with_vars(text, known_vars):
    """Render a raw hyprlang value/arg string as a Lua expression, resolving
    $variables to the local Lua variables that hold their values."""
    parts = []
    pos = 0
    for m in VAR_RE.finditer(text):
        name = m.group(1)
        if name not in known_vars:
            continue
        if m.start() > pos:
            parts.append(("lit", text[pos:m.start()]))
        parts.append(("var", known_vars[name]))
        pos = m.end()
    if pos < len(text):
        parts.append(("lit", text[pos:]))
    if not parts:
        return lua_string("")
    if len(parts) == 1 and parts[0][0] == "var":
        return parts[0][1]
    exprs = [lua_string(p[1]) if p[0] == "lit" else p[1] for p in parts]
    return " .. ".join(exprs)


def convert_scalar(key, raw, known_vars):
    """Convert a plain hyprlang value into a Lua literal (number/bool/string)."""
    raw = raw.strip()
    low = raw.lower()
    if low in BOOL_TRUE:
        return "true"
    if low in BOOL_FALSE:
        return "false"
    if NUMBER_RE.match(raw):
        return raw
    if VAR_RE.search(raw):
        return render_value_with_vars(raw, known_vars)
    return lua_string(raw)


def loose_bool(raw):
    """Coerce a value whose leading token is bool-ish to true/false.

    Handles Hyprland's strictly-boolean keys (e.g. `enabled`) even when the
    source has trailing junk, like omarchy's `enabled = yes, please :)`.
    """
    tok = re.split(r"[,\s]+", raw.strip(), maxsplit=1)[0].lower()
    if tok in BOOL_TRUE:
        return "true"
    if tok in BOOL_FALSE:
        return "false"
    return None


def convert_color_key(key, raw):
    """Handle `col.xxx = rgba(...) [rgba(...)] [Ndeg]` gradient border colors."""
    colors = COLOR_RE.findall(raw)
    rest = COLOR_RE.sub("", raw).strip()
    angle_match = re.search(r"(-?\d+(\.\d+)?)deg", rest)
    if len(colors) > 1 or angle_match:
        colors_lua = ", ".join(lua_string(c) for c in colors)
        angle = angle_match.group(1) if angle_match else "0"
        return f"{{ colors = {{ {colors_lua} }}, angle = {angle} }}"
    if colors:
        return lua_string(colors[0])
    return lua_string(raw)


BIND_FLAG_MAP = {
    "l": "locked",
    "e": "repeating",
    "m": "mouse",
    "r": "release",
    "i": "ignoremods",
    "t": "transparent",
    "n": "nonconsuming",
}


def parse_bind_flags(prefix):
    """`bindel` -> suffix 'el' -> {'repeating': True, 'locked': True}."""
    suffix = prefix[len("bind"):]
    flags = {}
    for ch in suffix:
        name = BIND_FLAG_MAP.get(ch)
        if name:
            flags[name] = True
        else:
            flags[f"unknown_flag_{ch}"] = True
    return flags


class Ctx:
    def __init__(self, name):
        self.name = name
        self.entries = []  # list of ("kv", key, luaval) | ("sub", key, entries) | ("comment", text)


def render_entries(entries, indent):
    pad = "    " * indent
    lines = []
    for kind, *rest in entries:
        if kind == "kv":
            key, val = rest
            lines.append(f"{pad}{key} = {val},")
        elif kind == "sub":
            key, sub = rest
            lines.append(f"{pad}{key} = {{")
            lines.extend(render_entries(sub, indent + 1))
            lines.append(f"{pad}}},")
        elif kind == "comment":
            (text,) = rest
            lines.append(f"{pad}{text}")
    return lines


def render_block(name, entries):
    lines = ["hl.config({", f"    {name} = {{"]
    lines.extend(render_entries(entries, 2))
    lines.append("    },")
    lines.append("})")
    return "\n".join(lines)


def convert_windowrule(raw):
    # Unlike generic config keys, windowrule match: fields (xwayland, float,
    # fullscreen, pin, ...) are always strictly boolean in Hyprland, so bare
    # "1"/"0" are safe to treat as booleans here.
    rule_bool_true = BOOL_TRUE | {"1"}
    rule_bool_false = BOOL_FALSE | {"0"}

    parts = [p.strip() for p in raw.split(",")]
    action_str = parts[0]
    match_parts = parts[1:]

    action_tokens = action_str.split(None, 1)
    action_name = action_tokens[0]
    action_arg = action_tokens[1] if len(action_tokens) > 1 else ""

    if not action_arg:
        action_val = "true"
    else:
        # Window-rule action values are strings in the Lua API (e.g.
        # opacity = "0.97 0.9"), except on/off/true/false which are bools.
        if action_arg.lower() in rule_bool_true:
            action_val = "true"
        elif action_arg.lower() in rule_bool_false:
            action_val = "false"
        else:
            action_val = lua_string(action_arg)

    match_entries = []
    for mp in match_parts:
        if not mp.startswith("match:"):
            continue
        field_val = mp[len("match:"):].strip()
        if " " in field_val:
            field, val = field_val.split(None, 1)
        else:
            field, val = field_val, "true"
        vlow = val.lower()
        if vlow in rule_bool_true:
            val_lua = "true"
        elif vlow in rule_bool_false:
            val_lua = "false"
        elif NUMBER_RE.match(val):
            val_lua = val
        else:
            val_lua = lua_string(val)
        match_entries.append(f"{field} = {val_lua}")

    lines = ["hl.window_rule({"]
    lines.append(f"    {action_name} = {action_val},")
    if match_entries:
        lines.append("    match = { " + ", ".join(match_entries) + " },")
    lines.append("})")
    return "\n".join(lines)


# hyprland direction shorthands -> the full words the Lua focus/move API wants.
DIRECTION = {
    "l": "left", "r": "right", "u": "up", "d": "down",
    "left": "left", "right": "right", "up": "up", "down": "down",
}


def _ws_value(arg):
    arg = arg.strip()
    return arg if NUMBER_RE.match(arg) else lua_string(arg)


def convert_dispatcher(dispatcher, args, flags, known_vars, var_literal):
    """Map a hyprlang dispatcher + args to the structured hl.dsp.* Lua call.

    The Lua API is a curated semantic namespace (verified against Hyprland
    --verify-config), NOT a 1:1 passthrough of hyprlang dispatcher names.
    Returns a Lua expression string, or None if it can't be mapped.
    """
    a = args.strip()
    mouse = flags.get("mouse")

    if dispatcher == "exec":
        return f"hl.dsp.exec_cmd({render_value_with_vars(a, known_vars)})"
    if dispatcher == "exit":
        return "hl.dsp.exit()"
    if dispatcher == "killactive":
        return "hl.dsp.window.close()"
    if dispatcher == "pseudo":
        return "hl.dsp.window.pseudo()"
    if dispatcher == "fullscreen":
        return "hl.dsp.window.fullscreen()"
    if dispatcher == "togglefloating":
        return 'hl.dsp.window.float({ action = "toggle" })'
    if dispatcher == "movefocus":
        d = DIRECTION.get(a.lower())
        return f"hl.dsp.focus({{ direction = {lua_string(d)} }})" if d else None
    if dispatcher == "movewindow":
        if mouse:
            return "hl.dsp.window.drag()"
        d = DIRECTION.get(a.lower())
        return f"hl.dsp.window.move({{ direction = {lua_string(d)} }})" if d else None
    if dispatcher == "swapwindow":
        d = DIRECTION.get(a.lower())
        return f"hl.dsp.window.swap({{ direction = {lua_string(d)} }})" if d else None
    if dispatcher == "resizeactive":
        nums = a.split()
        if len(nums) == 2 and all(re.match(r"^-?\d+$", n) for n in nums):
            return f"hl.dsp.window.resize({{ x = {nums[0]}, y = {nums[1]}, relative = true }})"
        return None
    if dispatcher == "resizewindow":
        return "hl.dsp.window.resize()"
    if dispatcher == "workspace":
        return f"hl.dsp.focus({{ workspace = {_ws_value(a)} }})"
    if dispatcher == "movetoworkspace":
        return f"hl.dsp.window.move({{ workspace = {_ws_value(a)} }})"
    if dispatcher == "layoutmsg":
        return f"hl.dsp.layout({lua_string(a)})"
    if dispatcher == "submap":
        name = var_literal[a[1:]] if a.startswith("$") and a[1:] in var_literal else a
        return f"hl.dsp.submap({lua_string(name)})"
    # plugin dispatcher (e.g. hyprexpo:expo): not exposed on hl.dsp, so route
    # it through hl.dispatch by name, wrapped in a Lua function (hl.bind
    # accepts a plain function). Safe even if the plugin isn't loaded at parse.
    if ":" in dispatcher:
        if a:
            return f"function() hl.dispatch({lua_string(dispatcher)}, {lua_string(a)}) end"
        return f"function() hl.dispatch({lua_string(dispatcher)}) end"
    return None


def transpile(text, known_vars=None, var_literal=None):
    out = []
    stack = []
    # Seed with vars from a parent file that `source =`s this one, since
    # hyprlang $variables are visible to sourced files in document order.
    known_vars = dict(known_vars) if known_vars else {}
    var_literal = dict(var_literal) if var_literal else {}
    exec_once = []
    current_submap = None
    sources = []

    block_open_re = re.compile(r"^([A-Za-z0-9_.]+)\s*\{\s*$")

    for raw_line in text.splitlines():
        code, comment = strip_comment(raw_line)
        stripped = code.strip()

        if not stripped:
            if not comment and stack:
                continue
            if comment and not stack:
                out.append(f"-- {comment.lstrip('#').strip()}")
            continue

        if stripped == "}":
            ctx = stack.pop()
            if stack:
                stack[-1].entries.append(("sub", ctx.name, ctx.entries))
            elif ctx.name in ("monitor", "monitorv2"):
                # A monitor block maps to hl.monitor({...}), not a config block.
                lines = ["hl.monitor({"]
                lines.extend(render_entries(ctx.entries, 1))
                lines.append("})")
                out.append("\n".join(lines))
            elif ctx.name == "plugin":
                # Unlike classic hyprlang (which defers unknown plugin keys),
                # the Lua hl.config validates immediately and logs "unknown
                # config key" for any plugin that isn't already loaded - which
                # spams the startup error overlay. Emit commented so it stays
                # inert; load the plugin via hl.plugin.load(...) then uncomment.
                block = render_block(ctx.name, ctx.entries)
                commented = "\n".join("-- " + ln for ln in block.split("\n"))
                out.append(
                    "-- TODO(manual-migration): plugin config requires the plugin"
                    " to be loaded first (hl.plugin.load); uncomment once loaded:\n"
                    + commented
                )
            else:
                out.append(render_block(ctx.name, ctx.entries))
            continue

        m = block_open_re.match(stripped)
        if m:
            stack.append(Ctx(m.group(1)))
            continue

        if "=" not in stripped:
            out.append(f"-- TODO(manual-migration): {raw_line.strip()}")
            continue

        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()

        # animations block: bezier/animation are repeated directives, not kv
        if stack and stack[-1].name == "animations" and key in ("bezier", "animation"):
            fields = [f.strip() for f in value.split(",")]
            if key == "bezier":
                bname = fields[0]
                pts = [float(x) for x in fields[1:5]]
                out.append(
                    f'hl.curve({lua_string(bname)}, {{ type = "bezier", '
                    f"points = {{ {{{pts[0]}, {pts[1]}}}, {{{pts[2]}, {pts[3]}}} }} }})"
                )
            else:
                aname = fields[0]
                # The animation on/off field is always strictly 0/1 in
                # Hyprland, unlike generic config values.
                enabled = fields[1].strip().lower() in (BOOL_TRUE | {"1"}) if len(fields) > 1 else True
                speed = fields[2].strip() if len(fields) > 2 else "0"
                bezier = fields[3].strip() if len(fields) > 3 else "default"
                style = fields[4].strip() if len(fields) > 4 else None
                extra = f', style = {lua_string(style)}' if style else ""
                out.append(
                    f'hl.animation({{ leaf = {lua_string(aname)}, enabled = '
                    f'{"true" if enabled else "false"}, speed = {speed}, '
                    f"bezier = {lua_string(bezier)}{extra} }})"
                )
            continue

        if key.startswith("$"):
            name = key[1:]
            ident = sanitize_ident(name)
            known_vars[name] = ident
            var_literal[name] = value
            lua_val = render_value_with_vars(value, known_vars)
            # Global (not local): hyprlang $vars are visible to `source`d
            # files, which we emit as dofile() chunks that can't see the
            # parent's Lua locals. Globals restore that cross-file visibility.
            out.append(f"{ident} = {lua_val}")
            continue

        if key == "source":
            sources.append(value)
            # dofile() (not require()) so this works with the same arbitrary,
            # cross-directory absolute paths hyprlang's `source` supports,
            # without relying on unconfirmed package.path search behavior.
            lua_path = os.path.splitext(value)[0] + ".lua"
            if lua_path.startswith("~/"):
                path_expr = f'os.getenv("HOME") .. {lua_string("/" + lua_path[2:])}'
            else:
                path_expr = lua_string(lua_path)
            out.append(f'dofile({path_expr})  -- was: source = {value}')
            continue

        if key == "env":
            name, _, val = value.partition(",")
            out.append(
                f"hl.env({lua_string(name.strip())}, {render_value_with_vars(val.strip(), known_vars)})"
            )
            continue

        if key in ("exec-once", "exec"):
            exec_once.append(render_value_with_vars(value, known_vars))
            continue

        if key == "monitor":
            fields = [f.strip() for f in value.split(",")]
            output, mode, position, scale = (fields + ["", "", "", "1"])[:4]
            scale_lua = scale if NUMBER_RE.match(scale) else lua_string(scale)
            out.append(
                "hl.monitor({\n"
                f"    output = {lua_string(output)},\n"
                f"    mode = {lua_string(mode)},\n"
                f"    position = {lua_string(position)},\n"
                f"    scale = {scale_lua},\n"
                "})"
            )
            continue

        if key == "submap":
            name = value.strip()
            if name == "reset":
                current_submap = None
            elif name.startswith("$") and name[1:] in var_literal:
                current_submap = var_literal[name[1:]]
            else:
                current_submap = name
            continue

        if key in ("windowrule", "windowrulev2"):
            out.append(convert_windowrule(value))
            continue

        if key.startswith("bind"):
            flags = parse_bind_flags(key)
            fields = value.split(",", 3)
            fields += [""] * (4 - len(fields))
            mods, keyname, dispatcher, args = (f.strip() for f in fields)
            # Every token must be '+'-joined: "SUPER + SHIFT + M", not
            # "SUPER SHIFT + M" (Hyprland's Lua key parser rejects the latter).
            mods_key = " + ".join([*mods.split(), keyname]) if keyname else " + ".join(mods.split())
            if dispatcher:
                call = convert_dispatcher(dispatcher, args, flags, known_vars, var_literal)
                if call is None:
                    out.append(f"-- TODO(manual-migration): {stripped}")
                    continue
            else:
                call = "nil"
            if current_submap is not None:
                flags["submap"] = current_submap
            if flags:
                opt_entries = ", ".join(
                    f"{k} = {v if v is True else lua_string(v)}" if v is not True else f"{k} = true"
                    for k, v in flags.items()
                )
                out.append(f'hl.bind({lua_string(mods_key)}, {call}, {{ {opt_entries} }})')
            else:
                out.append(f'hl.bind({lua_string(mods_key)}, {call})')
            continue

        # generic key = value inside/outside a block
        if key.startswith("col."):
            _, _, subkey = key.partition(".")
            lua_val = convert_color_key(key, value)
            if stack:
                # Merge into an existing "col" sub-block instead of adding a
                # second one, which would produce a Lua table with a
                # duplicate `col` key (silently dropping the first value).
                for kind, ekey, esub in stack[-1].entries:
                    if kind == "sub" and ekey == "col":
                        esub.append(("kv", subkey, lua_val))
                        break
                else:
                    stack[-1].entries.append(("sub", "col", [("kv", subkey, lua_val)]))
            else:
                out.append(render_block("col", [("kv", subkey, lua_val)]))
            continue

        lua_val = convert_scalar(key, value, known_vars)
        # `enabled` is strictly boolean everywhere in Hyprland; coerce even
        # when the source value has trailing junk.
        if key == "enabled":
            lua_val = loose_bool(value) or lua_val
        entry = ("kv", key, lua_val)
        if stack:
            stack[-1].entries.append(entry)
        else:
            out.append(f"hl.config({{ {key} = {lua_val} }})")

    if exec_once:
        lines = ['hl.on("hyprland.start", function()']
        lines += [f"    hl.exec_cmd({cmd})" for cmd in exec_once]
        lines.append("end)")
        out.append("\n".join(lines))

    return "\n\n".join(out) + "\n", sources, known_vars, var_literal


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="hyprlang .conf file to convert")
    parser.add_argument("-o", "--output", help="write Lua to this file (default: stdout)")
    parser.add_argument("-r", "--recursive", action="store_true", help="also transpile sourced files")
    parser.add_argument(
        "--vars-from",
        help="harvest $variable definitions from this file first (its own output is discarded) "
             "so a file that is normally `source`d by it - but is being converted standalone - "
             "still resolves those $vars instead of leaving them as literal text",
    )
    args = parser.parse_args()

    with open(args.input) as f:
        text = f.read()

    seed_known_vars = seed_var_literal = None
    if args.vars_from:
        with open(args.vars_from) as f:
            parent_text = f.read()
        _, _, seed_known_vars, seed_var_literal = transpile(parent_text)

    lua, sources, known_vars, var_literal = transpile(text, seed_known_vars, seed_var_literal)

    if args.output:
        with open(args.output, "w") as f:
            f.write(lua)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(lua)

    if args.recursive:
        in_dir = os.path.dirname(os.path.abspath(args.input))
        seen = {os.path.abspath(args.input)}
        for src in sources:
            resolved = os.path.expanduser(src)
            if not os.path.isabs(resolved):
                resolved = os.path.join(in_dir, resolved)
            resolved = os.path.abspath(resolved)
            if resolved in seen or not os.path.isfile(resolved):
                print(f"skip (not found): {src}", file=sys.stderr)
                continue
            seen.add(resolved)
            with open(resolved) as f:
                sub_text = f.read()
            sub_lua, _, _, _ = transpile(sub_text, known_vars, var_literal)
            # Write next to the original file, not into a shared output
            # directory: several sourced files across this repo share the
            # same basename (e.g. every theme's hyprland.conf), so
            # flattening by basename alone would silently clobber outputs.
            sub_out = os.path.splitext(resolved)[0] + ".lua"
            with open(sub_out, "w") as f:
                f.write(sub_lua)
            print(f"wrote {sub_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
