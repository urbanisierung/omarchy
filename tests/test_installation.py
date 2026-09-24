import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")

# Only allowlisted commands are available to the child shells. Privileged,
# network, and session commands are fakes; installer stages live in a temp HOME.
FAKE_COMMAND = r'''
import json
import os
import shutil
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["TEST_LOG"], "a") as log:
    log.write(json.dumps([name, *args]) + "\n")

if name == "rpm":
    if args == ["-q", "git"]:
        sys.exit(0)
    if args == ["-E", "%fedora"]:
        print("44")
        sys.exit(0)
    if len(args) == 2 and args[0] == "-q":
        sys.exit(0 if args[1] in os.environ.get("INSTALLED_REPOS", "").split(",") else 1)
elif name == "sudo":
    if args == ["tee", "/etc/yum.repos.d/vscode.repo"]:
        sys.stdin.read()
        sys.exit(0)
    allowed_dnf = args == ["dnf", "update", "-y"] or (
        args[:3] == ["dnf", "install", "-y"] and len(args) == 4 and (
            args[3] in ("git", "plocate", "code") or args[3] in (
                "https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm",
                "https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-44.noarch.rpm",
            )
        )
    )
    if allowed_dnf:
        if os.environ.get("FAIL_DNF") and os.environ["FAIL_DNF"] in args:
            sys.exit(42)
        sys.exit(0)
    if args in (
        ["rpm", "--import", "https://packages.microsoft.com/keys/microsoft.asc"],
        ["updatedb"],
    ):
        sys.exit(0)
elif name == "git":
    if "clone" in args:
        destination = Path(args[-1])
        shutil.copytree(os.environ["CLONE_FIXTURE"], destination)
        race = os.environ.get("PUBLISH_RACE")
        if race:
            existing = Path(os.environ["HOME"]) / ".local/share/omarchy"
            if race == "file":
                existing.write_text("keep me")
            elif race == "directory":
                existing.mkdir()
                (existing / "local-changes").write_text("keep me")
            elif race == "symlink":
                existing.symlink_to("missing-target")
        sys.exit(42 if os.environ.get("FAIL_GIT") == "clone" else 0)
    if args[:1] == ["-C"]:
        args = args[2:]
    if args[:1] == ["show-ref"]:
        sys.exit(0)
    if args and args[0] in ("fetch", "checkout"):
        sys.exit(42 if os.environ.get("FAIL_GIT") == args[0] else 0)
elif name == "gum" and args[:1] == ["confirm"]:
    sys.exit(int(os.environ.get("CONFIRM_STATUS", "1")))
elif name == "reboot":
    sys.exit(0)
elif name == "dnf" and args == ["check-update"]:
    sys.exit(100)

raise SystemExit("Unexpected test command: " + name + " " + repr(args))
'''


class InstallationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.commands = self.root / "commands"
        self.commands.mkdir()
        self.log = self.root / "commands.jsonl"
        self.checkout = self.home / ".local/share/omarchy"
        self.fixture = self.root / "clone fixture"
        self.fixture.mkdir()
        (self.fixture / "install.sh").write_text(
            'printf "installed\\n" > "$HOME/installer-ran"\n'
        )
        self.env = {
            "HOME": str(self.home),
            "PATH": str(self.commands),
            "LC_ALL": "C",
            "TEST_LOG": str(self.log),
            "CLONE_FIXTURE": str(self.fixture),
        }
        for command in ("bash", "mkdir", "mktemp", "mv", "rm"):
            executable = shutil.which(command)
            self.assertIsNotNone(executable, command)
            (self.commands / command).symlink_to(executable)
        for command in ("rpm", "sudo", "git", "gum", "reboot", "dnf"):
            script = self.commands / command
            script.write_text(f"#!{sys.executable}\n" + FAKE_COMMAND)
            script.chmod(0o755)

    def run_script(self, script, **env):
        return subprocess.run(
            [BASH, "--noprofile", "--norc", str(script)],
            cwd=self.root,
            env={**self.env, **env},
            text=True,
            capture_output=True,
            timeout=10,
        )

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def assert_failed_bootstrap(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.checkout.exists())
        self.assertFalse((self.home / "installer-ran").exists())
        self.assertEqual(list((self.home / ".local/share").glob(".omarchy-install.*")), [])

    def test_bootstrap_preserves_existing_checkout(self):
        self.checkout.mkdir(parents=True)
        marker = self.checkout / "local-changes"
        marker.write_text("keep me")
        result = self.run_script(ROOT / "boot.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "keep me")
        self.assertEqual(self.calls(), [])

    def test_bootstrap_preserves_existing_file(self):
        self.checkout.parent.mkdir(parents=True)
        self.checkout.write_text("keep me")
        result = self.run_script(ROOT / "boot.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.checkout.read_text(), "keep me")
        self.assertEqual(self.calls(), [])

    def test_bootstrap_preserves_dangling_symlink(self):
        self.checkout.parent.mkdir(parents=True)
        target = self.root / "missing"
        self.checkout.symlink_to(target)
        result = self.run_script(ROOT / "boot.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.checkout.is_symlink())
        self.assertEqual(self.checkout.readlink(), target)
        self.assertEqual(self.calls(), [])

    def test_bootstrap_cleans_failed_clone(self):
        result = self.run_script(ROOT / "boot.sh", FAIL_GIT="clone")
        self.assert_failed_bootstrap(result)

    def test_bootstrap_rejects_option_like_ref_before_commands(self):
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="--help")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_bootstrap_preserves_path_created_during_clone(self):
        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind):
                result = self.run_script(ROOT / "boot.sh", PUBLISH_RACE=kind)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse((self.home / "installer-ran").exists())
                if kind == "directory":
                    self.assertEqual(
                        (self.checkout / "local-changes").read_text(), "keep me"
                    )
                    shutil.rmtree(self.checkout)
                elif kind == "symlink":
                    self.assertEqual(self.checkout.readlink(), Path("missing-target"))
                    self.checkout.unlink()
                else:
                    self.assertEqual(self.checkout.read_text(), "keep me")
                    self.checkout.unlink()
                self.assertEqual(
                    list(self.checkout.parent.glob(".omarchy-install.*")), []
                )

    def test_bootstrap_stops_on_failed_fetch(self):
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="missing", FAIL_GIT="fetch")
        self.assert_failed_bootstrap(result)
        self.assertFalse(any("checkout" in call for call in self.calls()))

    def test_bootstrap_stops_on_failed_checkout(self):
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="missing", FAIL_GIT="checkout")
        self.assert_failed_bootstrap(result)

    def test_bootstrap_rejects_missing_installer(self):
        (self.fixture / "install.sh").unlink()
        self.assert_failed_bootstrap(self.run_script(ROOT / "boot.sh"))

    def test_bootstrap_rejects_invalid_installer_syntax(self):
        (self.fixture / "install.sh").write_text("if then\n")
        self.assert_failed_bootstrap(self.run_script(ROOT / "boot.sh"))

    def test_bootstrap_publishes_valid_checkout_and_runs_installer(self):
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.checkout / "install.sh").is_file())
        self.assertEqual((self.home / "installer-ran").read_text(), "installed\n")
        self.assertTrue(any("fetch" in call for call in self.calls()))
        self.assertTrue(any("checkout" in call for call in self.calls()))
        self.assertEqual(list(self.checkout.parent.glob(".omarchy-install.*")), [])

    def test_bootstrap_retains_checkout_after_installer_failure(self):
        (self.fixture / "install.sh").write_text("exit 42\n")
        result = self.run_script(ROOT / "boot.sh")
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertTrue((self.checkout / "install.sh").is_file())
        self.assertEqual(list(self.checkout.parent.glob(".omarchy-install.*")), [])

    def prepare_local_git(self):
        self.git = shutil.which("git")
        self.assertIsNotNone(self.git)
        (self.commands / "git").unlink()
        (self.commands / "git").symlink_to(self.git)
        self.env.update(
            {
                "GIT_ALLOW_PROTOCOL": "file",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_0": f"url.{self.fixture.as_uri()}.insteadOf",
                "GIT_CONFIG_VALUE_0": "https://github.com/urbanisierung/omarchy.git",
                "GIT_CONFIG_KEY_1": "core.hooksPath",
                "GIT_CONFIG_VALUE_1": "/dev/null",
                "GIT_CONFIG_KEY_2": "commit.gpgsign",
                "GIT_CONFIG_VALUE_2": "false",
                "GIT_AUTHOR_NAME": "Installation test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "Installation test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }
        )
        self.run_git(self.fixture, "init", "--initial-branch=main")
        self.run_git(self.fixture, "add", "install.sh")
        self.run_git(self.fixture, "commit", "-m", "Test fixture")

    def run_git(self, directory, *args):
        result = subprocess.run(
            [self.git, "-C", str(directory), *args],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_bootstrap_local_git_branch_retains_tracking(self):
        self.prepare_local_git()
        self.run_git(self.fixture, "branch", "dev")
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.run_git(self.checkout, "symbolic-ref", "--short", "HEAD"), "dev"
        )
        self.assertEqual(
            self.run_git(self.checkout, "rev-parse", "--abbrev-ref", "@{upstream}"),
            "origin/dev",
        )

    def test_bootstrap_local_git_tag_uses_fetched_commit(self):
        self.prepare_local_git()
        self.run_git(self.fixture, "tag", "v1")
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="v1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.run_git(self.checkout, "rev-parse", "--abbrev-ref", "HEAD"), "HEAD"
        )
        self.assertEqual(
            self.run_git(self.checkout, "rev-parse", "HEAD"),
            self.run_git(self.fixture, "rev-parse", "v1"),
        )

    def test_bootstrap_local_git_fetch_only_ref(self):
        self.prepare_local_git()
        self.run_git(self.fixture, "update-ref", "refs/pull/1/head", "HEAD")
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="refs/pull/1/head")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.run_git(self.checkout, "rev-parse", "HEAD"),
            self.run_git(self.fixture, "rev-parse", "refs/pull/1/head"),
        )

    def test_bootstrap_local_git_missing_ref_is_not_published(self):
        self.prepare_local_git()
        result = self.run_script(ROOT / "boot.sh", OMARCHY_REF="missing")
        self.assert_failed_bootstrap(result)

    def prepare_install(self, stage='printf "stage\\n" > "$HOME/stage-ran"\n'):
        stages = self.checkout / "install"
        stages.mkdir(parents=True)
        (stages / "fixture.sh").write_text(stage)

    def test_install_checks_rpmfusion_repositories_independently(self):
        self.prepare_install()
        repos = ("rpmfusion-free-release", "rpmfusion-nonfree-release")
        for installed in ((), repos[:1], repos[1:], repos):
            with self.subTest(installed=installed):
                self.log.write_text("")
                result = self.run_script(
                    ROOT / "install.sh", INSTALLED_REPOS=",".join(installed)
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                downloads = [
                    call[-1]
                    for call in self.calls()
                    if call[:3] == ["sudo", "dnf", "install"]
                ]
                for repo in repos:
                    found = any(f"/{repo}-44.noarch.rpm" in item for item in downloads)
                    self.assertEqual(found, repo not in installed)

    def test_install_provisions_updatedb_before_using_it(self):
        self.prepare_install()
        result = self.run_script(ROOT / "install.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertLess(
            calls.index(["sudo", "dnf", "install", "-y", "plocate"]),
            calls.index(["sudo", "updatedb"]),
        )

    def test_install_declining_reboot_succeeds(self):
        self.prepare_install()
        result = self.run_script(ROOT / "install.sh", CONFIRM_STATUS="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / "stage-ran").exists())
        self.assertNotIn(["reboot"], self.calls())

    def test_install_stops_when_plocate_installation_fails(self):
        self.prepare_install()
        result = self.run_script(ROOT / "install.sh", FAIL_DNF="plocate")
        self.assertEqual(result.returncode, 42)
        self.assertFalse((self.home / "stage-ran").exists())
        self.assertNotIn(["sudo", "updatedb"], self.calls())

    def test_install_confirming_reboot_uses_mock(self):
        self.prepare_install()
        result = self.run_script(ROOT / "install.sh", CONFIRM_STATUS="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["reboot"], self.calls())

    def test_install_reports_prompt_failure(self):
        self.prepare_install()
        result = self.run_script(ROOT / "install.sh", CONFIRM_STATUS="130")
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertNotIn(["reboot"], self.calls())

    def test_install_reports_early_upgrade_failure(self):
        self.prepare_install()
        result = self.run_script(ROOT / "install.sh", FAIL_DNF="update")
        self.assertEqual(result.returncode, 42)
        self.assertIn("Omarchy installation failed", result.stdout + result.stderr)
        self.assertFalse((self.home / "stage-ran").exists())
        self.assertNotIn(["sudo", "updatedb"], self.calls())

    def test_install_stops_after_stage_failure(self):
        self.prepare_install("false\n")
        result = self.run_script(ROOT / "install.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(["sudo", "updatedb"], self.calls())
        self.assertNotIn(["reboot"], self.calls())

    def test_vscode_does_not_abort_when_updates_are_available(self):
        wrapper = self.root / "vscode-test.sh"
        wrapper.write_text('set -e\nsource "$VSCODE_STAGE"\n')
        result = self.run_script(wrapper, VSCODE_STAGE=str(ROOT / "install/vscode.sh"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(["dnf", "check-update"], self.calls())
        self.assertIn(["sudo", "dnf", "install", "-y", "code"], self.calls())

    def test_vscode_still_reports_package_install_failure(self):
        wrapper = self.root / "vscode-test.sh"
        wrapper.write_text('set -e\nsource "$VSCODE_STAGE"\n')
        result = self.run_script(
            wrapper, VSCODE_STAGE=str(ROOT / "install/vscode.sh"), FAIL_DNF="code"
        )
        self.assertEqual(result.returncode, 42)


if __name__ == "__main__":
    unittest.main()
