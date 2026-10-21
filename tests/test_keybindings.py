import ast
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "keybindings", ROOT / "tools/keybindings.py"
)
kb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kb)


class KeybindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def write(self, name, text):
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def catalog(self, text):
        return kb.generate([self.write("hyprland.lua", text)], live=False)

    def test_recursive_includes_variables_and_source_lines(self):
        self.write(
            "nested/apps.lua",
            '\n-- comment\nhl.bind("SUPER + Return", hl.dsp.exec_cmd(terminal))\n',
        )
        self.write("extra.lua", 'dofile("nested/apps.lua")\n')
        data = self.catalog('terminal = "ghostty"\ndofile("extra.lua")\n')
        self.assertEqual(len(data["sources"]), 3)
        self.assertEqual(data["warnings"], [])
        binding = data["bindings"][0]
        self.assertEqual(binding["command"], "ghostty")
        self.assertEqual(binding["description"], "Open terminal")
        self.assertEqual(binding["line"], 3)
        self.assertTrue(binding["source"].endswith("nested/apps.lua"))

    def test_comments_and_backup_files_are_not_bindings(self):
        self.write("old.lua.bak", 'hl.bind("X", hl.dsp.exit())')
        self.write("unused.lua", 'hl.bind("Y", hl.dsp.exit())')
        data = self.catalog("""-- hl.bind("A", hl.dsp.exit())
--[=[
hl.bind("B", hl.dsp.exit())
]=]
text = 'hl.bind("C", hl.dsp.exit())'
hl.bind('SUPER + K', hl.dsp.exec_cmd("omarchy-show-keybindings"))
""")
        self.assertEqual([b["keys"] for b in data["bindings"]], ["SUPER + K"])
        self.assertEqual(len(data["sources"]), 1)

    def test_multiline_nested_callbacks_submaps_and_annotations(self):
        data = self.catalog("""hl.define_submap("resize", function()
    -- @shortcut Windows | Make the window wider
    hl.bind(
        "right",
        hl.dsp.window.resize({ x = 50, y = 0, relative = true }),
        { repeating = true }
    )
    hl.bind("Escape", hl.dsp.submap("reset"))
end)
hl.bind("left", function()
    if hl.plugin.hyprtasking.is_active() then
        hl.plugin.hyprtasking.move("left")
    end
end, { non_consuming = true })
""")
        self.assertEqual(len(data["bindings"]), 3)
        resize, escape, overview = data["bindings"]
        self.assertEqual(resize["description"], "Make the window wider")
        self.assertEqual(resize["line"], 3)
        self.assertEqual(resize["flags"], ["repeating"])
        self.assertEqual(escape["submap"], "resize")
        self.assertEqual(overview["submap"], "")
        self.assertIn("overview", overview["description"])
        self.assertIn("open", overview["context"])

    def test_quotes_commas_parentheses_and_long_strings(self):
        data = self.catalog(r"""browser = "google-chrome"
hl.bind("SUPER + A", hl.dsp.exec_cmd(browser .. " --app=\"https://chatgpt.com\""))
hl.bind("B", hl.dsp.exec_cmd([=[printf 'a,b) -- not a comment']=]), { description = "Print text" })
""")
        self.assertEqual(data["bindings"][0]["description"], "Open ChatGPT")
        self.assertEqual(
            data["bindings"][1]["command"], "printf 'a,b) -- not a comment'"
        )
        self.assertEqual(data["bindings"][1]["description"], "Print text")

    def test_safe_resolution_does_not_execute_code(self):
        marker = self.home / "must-not-exist"
        data = self.catalog(f"""os.execute("touch {marker}")
dofile(discover_config())
hl.bind(compute_key(), hl.dsp.exit())
hl.bind("Q", function() os.execute("touch {marker}") end)
""")
        self.assertFalse(marker.exists())
        self.assertEqual(len(data["warnings"]), 2)
        self.assertEqual(len(data["bindings"]), 1)

    def test_getenv_concatenation_and_unresolved_expression(self):
        with patch.dict(os.environ, {"SHORTCUT_HOME": str(self.home)}):
            self.assertEqual(
                kb.resolve('os.getenv("SHORTCUT_HOME") .. "/extra.lua"', {}),
                str(self.home / "extra.lua"),
            )
        self.assertIsNone(kb.resolve('dangerous("x")', {}))
        self.assertIsNone(kb.resolve('"unfinished" ..', {}))

    def test_cycles_missing_includes_and_require_deduplication(self):
        self.write("module.lua", 'hl.bind("M", hl.dsp.exit())\n')
        data = self.catalog(
            'require("module")\nrequire("module")\ndofile("hyprland.lua")\ndofile("missing.lua")'
        )
        self.assertEqual(len(data["bindings"]), 1)
        self.assertEqual(len(data["warnings"]), 2)

    def test_unbind_keeps_other_submaps(self):
        data = self.catalog("""hl.bind("SUPER + Q", hl.dsp.exit())
hl.define_submap("test", function()
    hl.bind("SUPER + Q", hl.dsp.exit())
end)
hl.unbind("super + q")
""")
        self.assertEqual(len(data["bindings"]), 1)
        self.assertEqual(data["bindings"][0]["submap"], "test")

    def test_hyprlang_sources_flags_descriptions_and_commas(self):
        self.write(
            "bindings/apps.conf", "bindd = $mod, T, Open a terminal, exec, printf a,b\n"
        )
        path = self.write(
            "hyprland.conf",
            """$mod = SUPER CTRL
source = bindings/*.conf
submap = resize
binde = , right, resizeactive, 20 0
submap = reset
bind = SUPER, Q, exit,
unbind = SUPER, Q
""",
        )
        data = kb.generate([path], live=False)
        self.assertEqual(len(data["bindings"]), 2)
        first, second = data["bindings"]
        self.assertEqual(first["description"], "Open a terminal")
        self.assertEqual(first["command"], "printf a,b")
        self.assertEqual(first["keycaps"], ["Super", "Ctrl", "T"])
        self.assertEqual(second["submap"], "resize")
        self.assertEqual(second["flags"], ["e"])

    def test_keycaps_and_search(self):
        self.assertEqual(
            kb.keycaps("SHIFT + CTRL + SUPER + code:19"),
            ["Super", "Ctrl", "Shift", "0"],
        )
        self.assertEqual(kb.keycaps("SUPER + mouse:272"), ["Super", "Left mouse"])
        self.assertEqual(kb.keycaps("XF86AudioRaiseVolume"), ["Volume up"])
        data = self.catalog(
            'hl.bind("SUPER + code:10", hl.dsp.focus({ workspace = 1 }))'
        )
        binding = data["bindings"][0]
        for query in ("super+1", "WORKSPACE 1", "hyprland.lua", "code:10", ""):
            self.assertTrue(kb.matches(binding, query), query)
        self.assertFalse(kb.matches(binding, "screenshot"))

    def test_reconciliation_preserves_duplicates_and_modes(self):
        reader = kb.Reader()
        reader.lua(
            """hl.bind("SUPER + K", hl.dsp.exit())
hl.bind("SUPER + K", hl.dsp.window.close())
hl.bind("SUPER + code:10", hl.dsp.focus({ workspace = 1 }))
""",
            self.home / "test.lua",
        )
        active = [
            {"modmask": 64, "key": "k", "dispatcher": "__lua", "arg": "1"},
            {"modmask": 64, "keycode": 10, "key": "", "dispatcher": "__lua"},
            {
                "modmask": 0,
                "key": "Escape",
                "submap": "test",
                "dispatcher": "exec",
                "arg": "ghostty",
                "description": "Custom terminal",
            },
        ]
        kb.reconcile(reader, active)
        self.assertEqual(
            [b["status"] for b in reader.bindings],
            ["active", "configured_only", "active", "runtime_only"],
        )
        self.assertEqual(reader.bindings[-1]["description"], "Custom terminal")
        self.assertEqual(reader.bindings[-1]["submap"], "test")

    def test_missing_runtime_keycodes_do_not_create_blank_shortcuts(self):
        reader = kb.Reader()
        reader.lua(
            'hl.bind("SUPER + code:10", hl.dsp.focus({ workspace = 1 }))',
            self.home / "test.lua",
        )
        kb.reconcile(
            reader, [{"modmask": 64, "key": "", "keycode": 0, "dispatcher": "__lua"}]
        )
        self.assertEqual(len(reader.bindings), 1)
        self.assertEqual(reader.bindings[0]["status"], "unverified")
        self.assertEqual(len(reader.runtime_unresolved), 1)
        self.assertEqual(len(reader.warnings), 1)

    def test_additional_modifiers_do_not_collide_with_unmodified_keys(self):
        reader = kb.Reader()
        reader.lua(
            'hl.bind("CAPS + K", hl.dsp.exit())\nhl.unbind("K")',
            self.home / "test.lua",
        )
        kb.reconcile(reader, [{"modmask": 2, "key": "K", "dispatcher": "__lua"}])
        self.assertEqual(len(reader.bindings), 1)
        self.assertEqual(reader.bindings[0]["status"], "active")
        self.assertEqual(reader.bindings[0]["keycaps"], ["Caps", "K"])
        self.assertEqual(kb.keycaps("MOD5 + K"), ["Mod5", "K"])

    def test_live_unavailable_falls_back_without_losing_config(self):
        path = self.write("hyprland.lua", 'hl.bind("K", hl.dsp.exit())')
        with patch.object(kb.subprocess, "run", side_effect=FileNotFoundError):
            data = kb.generate([path])
        self.assertFalse(data["live_checked"])
        self.assertEqual(len(data["bindings"]), 1)
        self.assertIn("Live bindings unavailable", data["warnings"][0])

    def test_json_cli_is_headless_and_export_round_trips(self):
        config = self.write("hyprland.lua", 'hl.bind("K", hl.dsp.exit())')
        destination = self.home / "export/catalog.json"
        result = subprocess.run(
            [
                "python3",
                "-B",
                str(ROOT / "bin/omarchy-show-keybindings"),
                "--config",
                str(config),
                "--offline",
                "--json",
                "--export",
                str(destination),
            ],
            env={**os.environ, "DISPLAY": "", "WAYLAND_DISPLAY": ""},
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(json.loads(destination.read_text()), data)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(result.stderr, "")

    def test_invalid_root_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Config not found"):
            kb.generate([self.home / "missing.lua"], live=False)

    def test_ui_pins_gtk_and_gdk_before_import(self):
        # Importing Gdk first otherwise chooses GTK 4 on mixed-version systems.
        tree = ast.parse((ROOT / "tools/keybindings_ui.py").read_text())
        versions = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "gi.repository":
                break
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "require_version"
            ):
                name, version = (ast.literal_eval(arg) for arg in node.value.args)
                versions[name] = version
        self.assertEqual(versions, {"Gtk": "3.0", "Gdk": "3.0"})

    def test_current_repository_bindings_have_descriptions(self):
        # Use a disposable HOME and source layout, not the running user's config.
        repo_link = self.home / ".local/share/omarchy"
        repo_link.parent.mkdir(parents=True)
        repo_link.symlink_to(ROOT, target_is_directory=True)
        self.write(".config/hypr/monitors.lua", "")
        self.write(".config/omarchy/current/theme/hyprland.lua", "")
        with patch.dict(os.environ, {"HOME": str(self.home)}):
            data = kb.generate([ROOT / "config/hypr/hyprland.lua"], live=False)
        self.assertEqual(data["warnings"], [])
        self.assertEqual(len(data["bindings"]), 143)
        self.assertEqual(len(data["sources"]), 9)
        self.assertEqual(sum(b["submap"] == "resize" for b in data["bindings"]), 5)
        for binding in data["bindings"]:
            self.assertNotEqual(binding["description"], "Custom action", binding)
            source_line = (
                Path(binding["source"]).read_text().splitlines()[binding["line"] - 1]
            )
            self.assertIn("hl.bind", source_line)


if __name__ == "__main__":
    unittest.main()
