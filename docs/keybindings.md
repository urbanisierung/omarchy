# Shortcut library

Press **Super+K** to open the read-only library. It replaces the fixed-width wofi
list with a native GTK window: category filters, action descriptions, keycaps,
mode labels, and expandable source/command details. Long text wraps rather than
running off screen. Opening a row never executes its shortcut.

- Type to search descriptions, keys, categories, modes, commands, flags, and paths.
  Multiple words are combined; matching ignores case. Try `super+k`, `resize`,
  `screenshot`, or `bindings.lua`.
- **Ctrl+F** focuses search; **Esc** closes the window. Tab navigates controls.
- **Refresh** rereads configuration and live bindings. Reopening **Super+K** also
  refreshes and presents the existing window instead of opening duplicates.
- **Source & action** shows the full command, original shortcut, mode, flags,
  and `file:line`. This text can be selected and copied.
- Resize/power-menu bindings are explicitly labeled; they are not global keys.
  Number-row `code:10`–`code:19` keys display as `1`–`0`, with the raw codes in details.

## Where shortcuts come from

The default root is `$XDG_CONFIG_HOME/hypr/hyprland.lua` (normally
`~/.config/hypr/hyprland.lua`), falling back to `hyprland.conf` if Lua is absent.
All reachable includes are read, including personal, default, and theme files.
Only referenced files are included: old `.bak` files and unused configurations
are not scanned indiscriminately. Source symlinks resolve to their actual files.

Supported discovery:

- Lua `dofile(...)`, local `require("module")` / `require("module.name")`,
  `hl.bind(...)`, `hl.unbind(...)`, and `hl.define_submap(...)`.
- String literals, single-line string assignments, concatenation, and
  `os.getenv(...)` for include paths and application commands.
- Multiline binding calls, nested tables/callbacks, quoted/long strings,
  and commented-out bindings.
- Legacy `.conf` roots: `source =` (including glob patterns), variables,
  `bind*`, `bindd` descriptions, `unbind`, and `submap`.

Relative includes resolve from the containing file. Local modules are searched
beside that file as `module.lua` or `module/init.lua`; custom Lua module search
paths are not evaluated. Missing, recursive, or unresolved includes are reported
in the window and JSON, not silently dropped. Repeat `--config` to add explicit
roots that cannot be discovered statically.

This is a **static catalog, not a Lua interpreter**. It never executes configuration
code, shell commands, or binding callbacks. It does not evaluate branches, loops,
functions, computed keys, or arbitrary Lua expressions. `hyprctl -j binds`
supplements the catalog with dynamically registered shortcuts when available.
App-internal shortcuts (for example, Neovim mappings) and independent hotkey
daemons are outside this Hyprland catalog's scope.

### Live verification

File descriptions are matched to live registrations by modifiers, key, and mode.
An `active` match confirms the **chord is registered**, not that opaque Lua callback
code matches a recently edited file. Reload Hyprland separately to apply binding
changes; the library does not change compositor configuration.

Some Lua-enabled Hyprland versions report an empty key and keycode `0` for
physical-number-row shortcuts. The library keeps their configured keycaps, marks
them `unverified`, and shows a warning instead of guessing or adding blank duplicates.
The raw unmatched records are retained in JSON's `runtime_unresolved` array.

If Hyprland is unavailable, file-based browsing/export still works and a warning
explains that live verification was unavailable. Use `--offline` to intentionally
skip the live query.

## Descriptions in binding files

Known desktop commands and dispatchers receive automatic readable labels.
For a custom action, put `-- @shortcut Tools | My descriptive action` immediately
above its `hl.bind(...)` call. The part before `|` is the category; omit it to
override only the description. This comment is ignored by Hyprland and requires
no changes to executable bindings.

A literal `description = "..."` in the binding options is also recognized, as
are legacy `bindd` descriptions. An `@shortcut` comment takes precedence. Unknown
actions remain visible with their original implementation in details.

## JSON and other tools

- `omarchy-show-keybindings --json`: write JSON to stdout, no GUI.
- `omarchy-show-keybindings --export ~/keybindings.json`: write a JSON file, no GUI.
- `omarchy-show-keybindings --offline --json`: file-only export, no compositor needed.
- `omarchy-show-keybindings --config /path/to/hyprland.lua --offline --json`:
  inspect a different configuration. `--config` can be repeated.
- **Export JSON…** in the window saves the entire catalog, not only filtered rows.

Each successful GUI load/refresh also writes
`$XDG_CACHE_HOME/omarchy/keybindings.json` (normally
`~/.cache/omarchy/keybindings.json`). It is a snapshot, not a background watcher.

Schema version **1**:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer schema version |
| `generated_at` | UTC ISO timestamp |
| `roots`, `sources` | Absolute root paths and discovered source paths |
| `live_checked` | Whether a live binding query succeeded |
| `warnings` | Discovery/verification issues |
| `runtime_unresolved` | Raw runtime records with no reported key |
| `bindings` | Shortcut records described below |

Each binding contains `keys` (raw combo), `keycaps` (display tokens),
`description`, `category`, `submap` (empty for global), `context`, `action`
(original implementation), `command` (resolved exec string when available),
`flags`, `source`, `line` (1-based), and `status`.

Statuses: `not_checked`, `active`, `configured_only`, `unverified`, or
`runtime_only`. Runtime-only entries have an empty `source` and `line: 0`;
Lua callback descriptions may be unavailable. Duplicate chords are retained:
multiple actions on one chord can be intentional. Treat commands as data, not
instructions to execute. Exports contain local paths and commands; review them
before sharing publicly.

## Dependencies and checks

Python 3.11+ is required. JSON mode uses only the standard library; the window
also needs PyGObject and GTK 3 (`python3-gobject` and `gtk3` on Fedora, included
in `install/desktop.sh`). No browser, web server, or additional Python package is
required for normal use.

Run regression tests with `python3 -B -m unittest discover -s tests`.
The parser's repository fixture verifies all 143 current bindings and source
locations, alongside include, mode, comment, keycode, search, and export tests.