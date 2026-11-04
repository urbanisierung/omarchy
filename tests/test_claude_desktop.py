import json
import os
import runpy
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
launcher = runpy.run_path(str(ROOT / "bin/omarchy-claude-desktop"))


class ClaudeDesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"
        self.root = self.home / ".claude-instances"
        self.proc = Path(self.temp.name) / "proc"
        self.proc.mkdir()
        self.running: dict[str, set[int]] = {
            slug: set() for slug, _, _ in launcher["PROFILES"]
        }

    def process(self, pid, *args):
        directory = self.proc / str(pid)
        directory.mkdir()
        (directory / "cmdline").write_bytes("\0".join((*args, "")).encode())

    def client(self, pid=42, workspace="13"):
        return {"pid": pid, "address": "0xabc", "workspace": {"name": workspace}}

    def test_exactly_eleven_unique_profiles_and_workspace_mappings(self):
        profiles = launcher["PROFILES"]
        self.assertEqual(len(profiles), 11)
        self.assertEqual(profiles[0], ("business", "Business", 6))
        self.assertEqual([profile[2] for profile in profiles[1:]], list(range(11, 21)))
        self.assertEqual(len({profile[0] for profile in profiles}), 11)

    def test_suggestion_first_then_free_then_running_in_numeric_order(self):
        self.running["business"] = {41}
        self.running["personal-3"] = {42}
        entries = launcher["menu_entries"](13, self.running, [self.client()])
        self.assertEqual(
            list(entries.values()),
            ["personal-3"]
            + [f"personal-{i}" for i in (1, 2, 4, 5, 6, 7, 8, 9, 10)]
            + ["business"],
        )
        first = next(iter(entries))
        self.assertIn("suggested", first)
        self.assertIn("in use on workspace 13", first)
        self.assertIn("in use (no visible window)", list(entries)[-1])

    def test_business_and_personal_ten_suggestions(self):
        for workspace, slug in ((6, "business"), (20, "personal-10")):
            entries = launcher["menu_entries"](workspace, self.running, [])
            self.assertEqual(next(iter(entries.values())), slug)
            self.assertIn("free", next(iter(entries)))

    def test_no_workspace_match_has_only_free_first(self):
        self.running["business"] = {42}
        entries = launcher["menu_entries"](5, self.running, [])
        self.assertEqual(next(iter(entries.values())), "personal-1")
        self.assertEqual(list(entries.values())[-1], "business")
        self.assertFalse(any("suggested" in label for label in entries))

    def test_process_arguments_match_exact_directories_and_ignore_helpers(self):
        directory = self.root / "personal-1"
        self.process(
            42,
            "/usr/lib/claude-desktop-unofficial/claude-desktop",
            f"--user-data-dir={directory}",
        )
        self.process(
            43, "claude-desktop", "--user-data-dir", str(self.root / "personal-10")
        )
        self.process(44, "claude-desktop", f"--user-data-dir={directory}-other")
        self.process(
            45, "claude-desktop", f"--user-data-dir={directory}", "--type=renderer"
        )
        self.process(46, "chromium", f"--user-data-dir={self.root / 'business'}")
        self.process(
            47,
            "/usr/bin/bash",
            "/usr/bin/claude-desktop-unofficial",
            f"--user-data-dir={self.root / 'business'}",
        )
        (self.proc / "48").mkdir()  # A process that exits during the scan.
        running = launcher["running_profiles"](self.root, self.proc)
        self.assertEqual(running["personal-1"], {42})
        self.assertEqual(running["personal-10"], {43})
        self.assertEqual(running["business"], {47})
        self.assertEqual(sum(map(len, running.values())), 3)

    def test_status_shows_actual_workspace_after_moving_window(self):
        self.running["business"] = {42}
        entries = launcher["menu_entries"](
            6, self.running, [self.client(workspace="2")]
        )
        self.assertIn("in use on workspace 2", next(iter(entries)))

    def test_activate_rechecks_and_focuses_running_window(self):
        self.running["business"] = {42}
        with (
            patch.dict(
                launcher["activate"].__globals__,
                running_profiles=lambda root: self.running,
            ),
            patch.dict(
                launcher["activate"].__globals__,
                hypr=unittest.mock.Mock(return_value=json.dumps([self.client()])),
            ),
        ):
            launcher["activate"]("business", self.root, 6)
            launcher["activate"].__globals__["hypr"].assert_called_with(
                "dispatch", 'hl.dsp.focus({ window = "address:0xabc" })'
            )
        self.assertFalse(self.root.exists())

    def test_new_and_tray_only_profiles_launch_with_isolated_directory(self):
        for running in (set(), {42}):
            self.running["business"] = running
            with (
                patch.dict(
                    launcher["activate"].__globals__,
                    running_profiles=lambda root: self.running,
                ),
                patch.dict(
                    launcher["activate"].__globals__,
                    hypr=unittest.mock.Mock(side_effect=["[]", "ok\n"]),
                ),
            ):
                launcher["activate"]("business", self.root, 19)
                call = launcher["activate"].__globals__["hypr"].call_args.args
                self.assertEqual(call[0], "dispatch")
                self.assertEqual(len(call), 2)
                self.assertTrue(call[1].startswith("hl.dsp.exec_cmd("))
                command = json.loads(call[1][len("hl.dsp.exec_cmd(") : -1])
                self.assertTrue(command.startswith("[workspace 19] "))
                args = shlex.split(command.split("] ", 1)[1])
                self.assertEqual(
                    args,
                    [
                        "claude-desktop-unofficial",
                        "--enable-features=UseOzonePlatform",
                        "--ozone-platform=wayland",
                        f"--user-data-dir={self.root / 'business'}",
                    ],
                )
        self.assertEqual((self.root / "business").stat().st_mode & 0o777, 0o700)

    def test_launch_error_is_not_silently_ignored(self):
        with (
            patch.dict(
                launcher["activate"].__globals__,
                running_profiles=lambda root: self.running,
                hypr=unittest.mock.Mock(side_effect=["[]", "error"]),
            ),
            self.assertRaisesRegex(RuntimeError, "could not launch"),
        ):
            launcher["activate"]("business", self.root, 6)

    def run_menu(self, result, args=()):
        globals_ = launcher["main"].__globals__
        with (
            patch.object(Path, "home", return_value=self.home),
            patch.object(globals_["shutil"], "which", return_value="/bin/fake"),
            patch.dict(
                globals_,
                running_profiles=lambda root: self.running,
                hypr=unittest.mock.Mock(side_effect=['{"id": 12}', "[]"]),
                activate=unittest.mock.Mock(),
                forward_url=unittest.mock.Mock(),
            ),
            patch.object(globals_["subprocess"], "run", return_value=result) as menu,
        ):
            launcher["main"](args)
            self.forwarded = globals_["forward_url"].call_args
            return menu.call_args, globals_["activate"].call_args

    def test_cancel_does_not_launch(self):
        _, activation = self.run_menu(subprocess.CompletedProcess([], 1, "", ""))
        self.assertIsNone(activation)
        self.assertFalse(self.root.exists())

    def test_selection_and_wofi_order(self):
        label = "Personal 2 — free — preferred WS 12 — suggested"
        menu, activation = self.run_menu(
            subprocess.CompletedProcess([], 0, label + "\n", "")
        )
        self.assertIn("--sort-order", menu.args[0])
        self.assertEqual(menu.kwargs["input"].splitlines()[0], label)
        self.assertEqual(activation.args, ("personal-2", self.root, 12))

    def test_arbitrary_input_cannot_launch(self):
        with self.assertRaisesRegex(RuntimeError, "listed Claude profiles"):
            self.run_menu(subprocess.CompletedProcess([], 0, "$(touch /tmp/nope)", ""))

    def test_wofi_error_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, "display unavailable"):
            self.run_menu(subprocess.CompletedProcess([], 1, "", "display unavailable"))

    def test_callback_chooser_only_offers_running_profiles(self):
        self.running["personal-2"] = {42}
        label = "Personal 2 — in use (no visible window) — preferred WS 12 — suggested"
        url = "claude://login/oauth?code=FAKE&state=FAKE"
        menu, activation = self.run_menu(
            subprocess.CompletedProcess([], 0, label + "\n", ""),
            ["--open-url", url],
        )
        self.assertEqual(menu.kwargs["input"], label + "\n")
        self.assertIn("select the original profile", menu.args[0][-1])
        self.assertNotIn(url, str(menu))
        self.assertEqual(self.forwarded.args, ("personal-2", self.root, url))
        self.assertEqual(activation.args, ("personal-2", self.root, 12))

    def test_callback_without_running_profile_requires_new_sign_in(self):
        with self.assertRaisesRegex(RuntimeError, "No Claude profile is running"):
            self.run_menu(
                subprocess.CompletedProcess([], 0, "", ""),
                ["--open-url", "claude://login?code=FAKE"],
            )

    def test_callback_cancellation_discards_link(self):
        self.running["business"] = {42}
        _, activation = self.run_menu(
            subprocess.CompletedProcess([], 1, "", ""),
            ["--open-url", "claude://login?code=FAKE"],
        )
        self.assertIsNone(self.forwarded)
        self.assertIsNone(activation)

    def test_invalid_urls_and_arguments_are_rejected_without_echoing_url(self):
        for args in (
            ["--open-url"],
            ["--other", "claude://login?code=FAKE"],
            ["--open-url", "https://example.com/?code=FAKE"],
            ["--open-url", "CLAUDE://login?code=FAKE"],
            ["--open-url", "claude:///login?code=FAKE"],
            ["--open-url", "claude://[invalid?code=FAKE"],
            ["--open-url", "claude://login?code=FAKE\n"],
        ):
            with self.subTest(args=args), self.assertRaises(RuntimeError) as error:
                launcher["main"](args)
            self.assertNotIn("code=FAKE", str(error.exception))

    def test_forwarding_preserves_url_as_one_argument_without_a_shell(self):
        self.running["business"] = {42}
        url = "claude://login/oauth?code=FAKE&state=a'$(touch /tmp/nope)"
        globals_ = launcher["forward_url"].__globals__
        with (
            patch.dict(globals_, running_profiles=lambda root: self.running),
            patch.object(globals_["subprocess"], "run") as run,
        ):
            run.return_value.returncode = 0
            launcher["forward_url"]("business", self.root, url)
            self.assertEqual(
                run.call_args.args[0],
                [*launcher["claude_command"](self.root / "business"), url],
            )
            self.assertFalse(run.call_args.kwargs.get("shell", False))
            self.assertEqual(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)
            self.assertFalse(self.root.exists())

    def test_callback_to_closed_profile_is_not_forwarded(self):
        globals_ = launcher["forward_url"].__globals__
        with (
            patch.dict(globals_, running_profiles=lambda root: self.running),
            patch.object(globals_["subprocess"], "run") as run,
            self.assertRaisesRegex(RuntimeError, "profile has closed"),
        ):
            launcher["forward_url"]("business", self.root, "claude://login?code=FAKE")
        run.assert_not_called()

    def test_forwarding_errors_never_expose_callback_codes(self):
        self.running["business"] = {42}
        url = "claude://login?code=FAKE_SECRET"
        globals_ = launcher["forward_url"].__globals__
        for failure in (
            OSError(url),
            subprocess.TimeoutExpired(["claude-desktop-unofficial", url], 15),
            subprocess.CalledProcessError(1, ["claude-desktop-unofficial", url]),
        ):
            with (
                self.subTest(failure=type(failure).__name__),
                patch.dict(globals_, running_profiles=lambda root: self.running),
                patch.object(globals_["subprocess"], "run", side_effect=failure),
                self.assertRaises(RuntimeError) as error,
            ):
                launcher["forward_url"]("business", self.root, url)
            self.assertNotIn("FAKE_SECRET", str(error.exception))

    def test_nonzero_callback_delivery_is_reported(self):
        globals_ = launcher["forward_url"].__globals__
        self.running["business"] = {42}
        with (
            patch.dict(globals_, running_profiles=lambda root: self.running),
            patch.object(globals_["subprocess"], "run") as run,
            self.assertRaisesRegex(RuntimeError, "Claude rejected the link"),
        ):
            run.return_value.returncode = 1
            launcher["forward_url"]("business", self.root, "claude://login?code=FAKE")

    @unittest.skipUnless(shutil.which("gio"), "GIO desktop launcher not installed")
    def test_desktop_handler_preserves_url_argument_with_real_gio(self):
        # A disposable HOME replaces the destination script, never the real app.
        script = self.home / ".local/share/omarchy/bin/omarchy-claude-desktop"
        script.parent.mkdir(parents=True)
        script.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
        url = "claude://login/oauth?code=FAKE%2B%2F%3D&state=a'$(echo nope)"
        result = subprocess.run(
            [
                "gio",
                "launch",
                str(ROOT / "applications/com.anthropic.Claude.desktop"),
                url,
            ],
            env={**os.environ, "HOME": str(self.home)},
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout), ["--open-url", url])


if __name__ == "__main__":
    unittest.main()
