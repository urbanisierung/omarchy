import fcntl
import hashlib
import importlib.util
import json
import os
import pty
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "installer/kickstart"
BASH = shutil.which("bash")
SPEC = importlib.util.spec_from_file_location(
    "usb_builder", ROOT / "tools/build-kickstart-iso.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

FAKE_COMMAND = r"""
import os
import subprocess
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
if name == "id" and args == ["-u"]:
    print(os.environ.get("TEST_UID", "1000"))
elif name == "uname" and args == ["-m"]:
    print(os.environ.get("TEST_ARCH", "x86_64"))
elif name == "rpm" and args == ["-E", "%fedora"]:
    print(os.environ.get("TEST_FEDORA", "44"))
elif name == "sudo" and args == ["-v"]:
    Path(os.environ["HOME"], "sudo-called").touch()
    sys.exit(int(os.environ.get("TEST_SUDO_EXIT", "0")))
elif name == "script" and args[:4] == ["--quiet", "--return", "--flush", "--command"]:
    Path(args[-1]).write_text("fake terminal log\n")
    sys.exit(subprocess.run([os.environ["TEST_BASH"], "-c", args[4]]).returncode)
else:
    raise SystemExit("Unexpected command: " + name + repr(args))
"""


class UsbSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.payload = self.root / "payload with 'quotes' and spaces"
        self.payload.mkdir()
        shutil.copyfile(ASSETS / "setup.sh", self.payload / "setup.sh")
        self.revision = "a" * 40
        (self.payload / "revision").write_text(self.revision + "\n")
        (self.payload / "boot.sh").write_text(
            'printf "%s" "$OMARCHY_REF" > "$HOME/boot-ran"\n'
            'exit "${TEST_BOOT_EXIT:-0}"\n'
        )
        self.commands = self.root / "commands"
        self.commands.mkdir()
        for name in ("bash", "dirname", "cat", "mkdir", "flock"):
            (self.commands / name).symlink_to(shutil.which(name))
        for name in ("id", "uname", "rpm", "sudo", "script", "git"):
            command = self.commands / name
            command.write_text(f"#!{sys.executable}\n" + FAKE_COMMAND)
            command.chmod(0o755)
        self.env = {
            "HOME": str(self.home),
            "PATH": str(self.commands),
            "LC_ALL": "C",
            "TEST_BASH": BASH,
        }
        self.state = self.home / ".local/state/omarchy-usb"

    def run_setup(self, answer="INSTALL\n", terminal=True, args=(), **env):
        command = [BASH, "--noprofile", "--norc", str(self.payload / "setup.sh"), *args]
        environment = {**self.env, **env}
        if not terminal:
            result = subprocess.run(
                command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.returncode, result.stdout + result.stderr
        master, slave = pty.openpty()
        try:
            with subprocess.Popen(
                command, env=environment, stdin=slave, stdout=slave, stderr=slave
            ) as process:
                os.write(master, answer.encode())
                try:
                    result = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    raise
            os.close(slave)
            slave = None
            output = bytearray()
            while True:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
            return result, output.decode()
        finally:
            os.close(master)
            if slave is not None:
                os.close(slave)

    def assert_not_started(self):
        self.assertFalse((self.home / "sudo-called").exists())
        self.assertFalse((self.home / "boot-ran").exists())
        self.assertFalse((self.state / "attempted").exists())

    def test_declining_does_not_start_or_mark_attempt(self):
        result, output = self.run_setup(answer="no\n")
        self.assertEqual(result, 0, output)
        self.assert_not_started()

    def test_success_pins_commit_and_records_result(self):
        result, output = self.run_setup()
        self.assertEqual(result, 0, output)
        self.assertEqual((self.home / "boot-ran").read_text(), self.revision)
        self.assertEqual((self.state / "completed").read_text().strip(), self.revision)
        self.assertEqual((self.state / "exit-status").read_text(), "0\n")
        self.assertTrue((self.state / "install.log").exists())
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_installer_failure_is_recorded_and_not_retried(self):
        result, output = self.run_setup(TEST_BOOT_EXIT="42")
        self.assertEqual(result, 42, output)
        self.assertFalse((self.state / "completed").exists())
        self.assertEqual((self.state / "exit-status").read_text(), "42\n")
        (self.home / "boot-ran").unlink()
        (self.home / "sudo-called").unlink()
        result, output = self.run_setup(terminal=False, args=("--autostart",))
        self.assertEqual(result, 0, output)
        self.assertFalse((self.home / "boot-ran").exists())
        self.assertFalse((self.home / "sudo-called").exists())

    def test_sudo_failure_is_not_success(self):
        result, output = self.run_setup(TEST_SUDO_EXIT="1")
        self.assertEqual(result, 1, output)
        self.assertTrue((self.state / "attempted").exists())
        self.assertFalse((self.state / "completed").exists())
        self.assertFalse((self.home / "boot-ran").exists())

    def test_root_wrong_os_and_wrong_arch_are_rejected(self):
        for environment in (
            {"TEST_UID": "0"},
            {"TEST_FEDORA": "43"},
            {"TEST_ARCH": "aarch64"},
        ):
            with self.subTest(environment=environment):
                result, _ = self.run_setup(**environment)
                self.assertNotEqual(result, 0)
                self.assert_not_started()

    def test_noninteractive_invocation_is_rejected(self):
        result, output = self.run_setup(terminal=False)
        self.assertNotEqual(result, 0)
        self.assertIn("interactive terminal", output)
        self.assert_not_started()

    def test_existing_checkout_types_are_preserved(self):
        checkout = self.home / ".local/share/omarchy"
        checkout.parent.mkdir(parents=True)
        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind):
                if kind == "file":
                    checkout.write_text("keep me")
                elif kind == "directory":
                    checkout.mkdir()
                else:
                    checkout.symlink_to("missing-target")
                result, output = self.run_setup()
                self.assertNotEqual(result, 0, output)
                self.assert_not_started()
                if kind == "directory":
                    checkout.rmdir()
                else:
                    if kind == "file":
                        self.assertEqual(checkout.read_text(), "keep me")
                    else:
                        self.assertEqual(checkout.readlink(), Path("missing-target"))
                    checkout.unlink()

    def test_invalid_revision_is_rejected(self):
        (self.payload / "revision").write_text("dev; false")
        result, output = self.run_setup()
        self.assertNotEqual(result, 0, output)
        self.assert_not_started()

    def test_invalid_bootstrap_is_rejected(self):
        (self.payload / "boot.sh").write_text("if then\n")
        result, output = self.run_setup()
        self.assertNotEqual(result, 0, output)
        self.assert_not_started()

    def test_concurrent_setup_is_rejected(self):
        self.state.mkdir(parents=True)
        with (self.state / "lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result, _ = self.run_setup()
        self.assertNotEqual(result, 0)
        self.assert_not_started()

    def test_autostart_success_waits_for_acknowledgement(self):
        result, output = self.run_setup(answer="INSTALL\n\n", args=("--autostart",))
        self.assertEqual(result, 0, output)
        self.assertIn("Press Enter", output)


class UsbBuilderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "output with spaces"
        self.revision = "b" * 40
        patcher = mock.patch.object(
            builder, "git", side_effect=[self.revision, 'echo "fixture bootstrap"']
        )
        self.git = patcher.start()
        self.addCleanup(patcher.stop)

    def prepare(self, **kwargs):
        return builder.prepare(self.output, "HEAD", **kwargs)

    def test_prepare_pins_bootstrap_and_hashes_payload(self):
        kickstart, payload = self.prepare()
        self.assertEqual((payload / "revision").read_text(), self.revision + "\n")
        self.git.assert_any_call("show", f"{self.revision}:boot.sh")
        self.assertEqual(kickstart.read_bytes(), (ASSETS / "fedora44.ks").read_bytes())
        manifest = json.loads((self.output / "manifest.json").read_text())
        for name, checksum in manifest["files"].items():
            self.assertEqual(builder.digest(self.output / name), checksum)
        self.assertFalse(list(self.output.glob("*.iso")))

    def test_existing_output_and_dangling_symlink_are_refused(self):
        self.output.mkdir()
        with self.assertRaises(ValueError):
            self.prepare()
        self.output.rmdir()
        self.output.symlink_to(self.root / "missing")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertTrue(self.output.is_symlink())
        self.git.assert_not_called()

    def test_option_like_ref_is_rejected_before_git(self):
        with self.assertRaises(ValueError):
            builder.prepare(self.output, "--help")
        self.git.assert_not_called()

    def test_mismatched_iso_checksum_leaves_no_output(self):
        iso = self.root / "source.iso"
        iso.write_bytes(b"not a Fedora image")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            self.prepare(iso=iso, sha256="0" * 64)
        self.assertFalse(self.output.exists())

    def test_valid_iso_checksum_is_recorded(self):
        iso = self.root / "source.iso"
        iso.write_bytes(b"fixture")
        checksum = hashlib.sha256(b"fixture").hexdigest()
        self.prepare(iso=iso, sha256=checksum)
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["source_sha256"], checksum)

    def test_device_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "regular .iso"):
            self.prepare(iso=Path("/dev/null"), sha256="0" * 64)
        self.assertFalse(self.output.exists())

    def test_missing_checksum_is_rejected(self):
        iso = self.root / "source.iso"
        iso.touch()
        with self.assertRaisesRegex(ValueError, "--sha256"):
            self.prepare(iso=iso)
        self.assertFalse(self.output.exists())

    def test_build_uses_validation_and_full_efi_path(self):
        image = self.output / "omarchy-fedora44-x86_64.iso"
        self.output.mkdir()
        image.write_bytes(b"fake built image")
        kickstart = self.output / "kickstart.ks"
        payload = self.output / "omarchy-usb"
        args = [
            "builder",
            "--output-dir",
            str(self.output),
            "--iso",
            str(self.root / "source.iso"),
            "--sha256",
            "0" * 64,
        ]
        with (
            mock.patch.object(sys, "argv", args),
            mock.patch.object(builder.platform, "machine", return_value="x86_64"),
            mock.patch.object(builder.shutil, "which", return_value="fake"),
            mock.patch.object(builder, "prepare", return_value=(kickstart, payload)),
            mock.patch.object(builder.subprocess, "run") as run,
        ):
            self.assertEqual(builder.main(), 0)
        self.assertEqual(
            run.call_args_list[0].args[0][:3], ["ksvalidator", "-v", "F44"]
        )
        build_command = run.call_args_list[1].args[0]
        self.assertEqual(build_command[:3], ["sudo", "-n", "mkksiso"])
        self.assertNotIn("--skip-mkefiboot", build_command)
        self.assertEqual(build_command[-1], str(image))
        self.assertTrue((self.output / "SHA256SUMS").exists())

    def test_validation_failure_never_invokes_build(self):
        with (
            mock.patch.object(
                sys,
                "argv",
                ["builder", "--output-dir", str(self.output), "--iso", "source.iso"],
            ),
            mock.patch.object(builder.platform, "machine", return_value="x86_64"),
            mock.patch.object(builder.shutil, "which", return_value="fake"),
            mock.patch.object(
                builder, "prepare", return_value=(self.root / "ks", self.root)
            ),
            mock.patch.object(
                builder.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(1, "ksvalidator"),
            ) as run,
        ):
            self.assertEqual(builder.main(), 1)
        self.assertEqual(run.call_count, 1)
        self.assertFalse((self.output / "SHA256SUMS").exists())

    def test_kickstart_keeps_destructive_storage_and_secrets_interactive(self):
        kickstart = (ASSETS / "fedora44.ks").read_text()
        for line in kickstart.splitlines():
            if line and not line.startswith("#"):
                self.assertNotIn(
                    line.split()[0],
                    {"clearpart", "zerombr", "autopart", "part", "partition", "user"},
                )
        self.assertIn("rootpw --lock", kickstart)
        self.assertNotIn("--password", kickstart)
        self.assertNotIn("--passphrase", kickstart)
        self.assertIn("%post --nochroot --erroronfail", kickstart)
        self.assertNotIn("bash ", kickstart)
        self.assertIn("halt", kickstart)


if __name__ == "__main__":
    unittest.main()
