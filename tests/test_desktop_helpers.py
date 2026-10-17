"""Tests for omarchy-wifi, omarchy-restart-portal, omarchy-update-hypr-plugins
and omarchy-edit-config.

System tools (nmcli, wofi, systemctl, hyprpm, ...) are fakes that log their
arguments to TEST_LOG, and answer from environment variables.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"

LOGGER = 'printf "%s\\n" "$(basename "$0") $*" >> "$TEST_LOG"\n'

FAKES = {
    # nmcli answers from NM_* env vars.
    "nmcli": LOGGER + r'''
case "$*" in
  "radio wifi") echo "${NM_RADIO:-enabled}" ;;
  "radio wifi "*) ;;
  *"connection show"*) printf '%b' "${NM_SAVED:-}" ;;
  *"device wifi list"*) printf '%b' "${NM_LIST:-}" ;;
  "connection up "*) exit "${NM_UP_RC:-0}" ;;
  "device wifi connect "*) exit "${NM_CONNECT_RC:-0}" ;;
esac
''',
    # wofi prints the first menu line containing WOFI_PICK, or WOFI_PASSWORD.
    "wofi": LOGGER + r'''
if [[ " $* " == *" --password "* ]]; then echo "$WOFI_PASSWORD"; exit 0; fi
[[ -n "${WOFI_PICK:-}" ]] || exit 1
grep -m1 -F -- "$WOFI_PICK" || exit 1
''',
    "flock": 'shift 2; exec "$@"\n',
    "notify-send": LOGGER,
    "nm-connection-editor": LOGGER,
    "systemctl": LOGGER + 'exit "${SYSTEMCTL_RC:-0}"\n',
    "pkill": LOGGER + "exit 1\n",
    "sleep": "",
    "hyprpm": LOGGER,
    "rpm": 'echo "${HYPR_VERSION:-hyprland-0.55.0-1.fc44.x86_64}"\n',
    "fake-editor": LOGGER,
    "ghostty": LOGGER + 'shift; exec "$@"\n',
}


class DesktopHelpersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.log = self.tmp / "log"
        self.log.touch()
        fakes = self.tmp / "fakes"
        fakes.mkdir()
        for name, body in FAKES.items():
            p = fakes / name
            p.write_text("#!/bin/bash\n" + body)
            p.chmod(0o755)
        self.home = self.tmp / "home"
        self.home.mkdir()
        # Only fakes + coreutils: no real nmcli/wofi/systemctl can be reached.
        coreutils = sorted({str(Path(shutil.which(t)).parent)
                            for t in ("bash", "awk", "grep", "cat", "head", "mkdir")})
        self.env = {
            "PATH": ":".join([str(fakes), *coreutils]),
            "HOME": str(self.home),
            "TEST_LOG": str(self.log),
        }

    def run_bin(self, name, *args, env=None, check=True):
        r = subprocess.run([str(BIN / name), *args], env={**self.env, **(env or {})},
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if check and r.returncode != 0:
            self.fail(f"{name} {args} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r

    def calls(self, prog=None):
        lines = self.log.read_text().splitlines()
        return [l for l in lines if prog is None or l.split(" ", 1)[0] == prog]

    # omarchy-wifi ----------------------------------------------------------

    WIFI_LIST = (
        "*:80:WPA2:HomeNet\\n"
        ":70:WPA2:Cafe: Free\\n"        # colon inside the SSID
        ":60:WPA2:HomeNet\\n"           # same SSID on another band -> listed once
        ":50:--:OpenSpot\\n"
        ":40:WPA2 802.1X:CorpWifi\\n"
        ":30:WPA2:\\n"                  # hidden network -> skipped
    )

    def wifi(self, pick, check=True, **env):
        return self.run_bin("omarchy-wifi", check=check, env={
            "NM_LIST": self.WIFI_LIST,
            "NM_SAVED": "HomeNet:802-11-wireless\\nWired:802-3-ethernet\\nKnownCafe:802-11-wireless\\n",
            "WOFI_PICK": pick, **env})

    def test_wifi_new_network_with_colon_asks_password(self):
        self.wifi("Cafe: Free", WOFI_PASSWORD="pw")
        self.assertIn("nmcli device wifi connect Cafe: Free password pw", self.calls("nmcli"))

    def test_wifi_menu_lists_each_network_once(self):
        # Fake wofi that dumps the menu it was given.
        dump = self.tmp / "menu"
        wofi = Path(self.env["PATH"].split(":")[0]) / "wofi"
        wofi.write_text(f"#!/bin/bash\ncat > {dump}\nexit 1\n")
        self.wifi("")
        menu = dump.read_text().splitlines()
        names = [l for l in menu if "%)" in l]
        self.assertEqual(len(names), 4, menu)  # hidden + duplicate band dropped
        self.assertEqual(sum("HomeNet" in l for l in names), 1)
        self.assertTrue(any("Disconnect HomeNet" in l for l in menu))

    def test_wifi_connects_saved_network_without_password(self):
        self.run_bin("omarchy-wifi", env={
            "NM_LIST": ":70:WPA2:KnownCafe\\n",
            "NM_SAVED": "KnownCafe:802-11-wireless\\n",
            "WOFI_PICK": "KnownCafe"})
        self.assertIn("nmcli connection up id KnownCafe", self.calls("nmcli"))
        self.assertFalse(any("wofi" in c and "--password" in c for c in self.calls()))

    def test_wifi_open_network_connects_directly(self):
        self.wifi("OpenSpot")
        self.assertIn("nmcli device wifi connect OpenSpot", self.calls("nmcli"))

    def test_wifi_enterprise_opens_settings(self):
        self.wifi("CorpWifi")
        self.assertTrue(self.calls("nm-connection-editor"))
        self.assertFalse(any("wifi connect" in c or "connection up" in c for c in self.calls("nmcli")))

    def test_wifi_disconnect_active(self):
        self.wifi("Disconnect HomeNet")
        self.assertIn("nmcli connection down id HomeNet", self.calls("nmcli"))

    def test_wifi_cancel_does_nothing(self):
        self.wifi("no-such-entry")  # fake wofi exits 1 = Esc
        self.assertFalse(any(c.startswith("nmcli connection") or "connect " in c
                             for c in self.calls("nmcli")))

    def test_wifi_off_menu_turns_on(self):
        self.run_bin("omarchy-wifi", env={"NM_RADIO": "disabled", "WOFI_PICK": "Turn Wi-Fi on"})
        self.assertIn("nmcli radio wifi on", self.calls("nmcli"))

    def test_wifi_toggle(self):
        self.run_bin("omarchy-wifi", "toggle", env={"NM_RADIO": "enabled"})
        self.assertIn("nmcli radio wifi off", self.calls("nmcli"))
        self.run_bin("omarchy-wifi", "toggle", env={"NM_RADIO": "disabled"})
        self.assertIn("nmcli radio wifi on", self.calls("nmcli"))

    def test_wifi_failed_password_reports_error(self):
        r = self.wifi("Cafe: Free", WOFI_PASSWORD="wrong", NM_CONNECT_RC="4", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(any("critical" in c for c in self.calls("notify-send")))

    # omarchy-restart-portal ------------------------------------------------

    def test_restart_portal(self):
        self.run_bin("omarchy-restart-portal")
        self.assertEqual(self.calls("systemctl"), [
            "systemctl --user restart xdg-desktop-portal-hyprland.service",
            "systemctl --user restart xdg-desktop-portal.service",
        ])
        self.assertIn("pkill -x xdg-desktop-portal-gnome", self.calls("pkill"))

    def test_restart_portal_failure_exits_nonzero(self):
        r = self.run_bin("omarchy-restart-portal", env={"SYSTEMCTL_RC": "1"}, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("failed", r.stdout)

    # omarchy-update-hypr-plugins -------------------------------------------

    def test_plugins_rebuild_only_when_hyprland_changes(self):
        self.run_bin("omarchy-update-hypr-plugins")
        self.assertEqual(self.calls("hyprpm"), ["hyprpm update -f"])
        self.run_bin("omarchy-update-hypr-plugins")
        self.assertEqual(len(self.calls("hyprpm")), 1, "same version: no rebuild")
        self.run_bin("omarchy-update-hypr-plugins", env={"HYPR_VERSION": "hyprland-0.56.0"})
        self.assertEqual(len(self.calls("hyprpm")), 2)

    def test_plugins_force_and_reload_in_session(self):
        self.run_bin("omarchy-update-hypr-plugins")
        self.run_bin("omarchy-update-hypr-plugins", "--force",
                     env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})
        self.assertEqual(self.calls("hyprpm")[-2:], ["hyprpm update -f", "hyprpm reload -n"])

    # omarchy-edit-config ---------------------------------------------------

    def test_edit_config_lists_existing_files_and_opens_editor(self):
        envdir = self.home / ".config/envvars"
        envdir.mkdir(parents=True)
        (envdir / "weeklyfoo.env").write_text("")
        (self.home / ".zshrc").write_text("")
        self.run_bin("omarchy-edit-config",
                     env={"WOFI_PICK": "weeklyfoo", "EDITOR": "fake-editor"})
        self.assertIn(f"fake-editor {envdir}/weeklyfoo.env", self.calls("fake-editor"))

    def test_edit_config_reloads_waybar(self):
        wb = self.home / ".config/waybar"
        wb.mkdir(parents=True)
        (wb / "config").write_text("{}")
        self.run_bin("omarchy-edit-config", env={"WOFI_PICK": "waybar/config", "EDITOR": "fake-editor"})
        self.assertIn("pkill -SIGUSR2 -x waybar", self.calls("pkill"))


class WiringTest(unittest.TestCase):
    def test_waybar_config_is_valid_json_and_uses_wifi_menu(self):
        cfg = json.loads((ROOT / "config/waybar/config").read_text())
        self.assertIn("omarchy-wifi", cfg["network"]["on-click"])

    def test_new_bindings_present_and_unique(self):
        import re
        keys = []
        for f in [ROOT / "default/hypr/bindings.lua", *(ROOT / "config/hypr").glob("*.lua")]:
            keys += re.findall(r'^hl\.bind\("([^"]+)"', f.read_text(), re.M)
        for k in ("SUPER + ALT + W", "SUPER + ALT + S", "SUPER + ALT + E"):
            self.assertEqual(keys.count(k), 1, k)


if __name__ == "__main__":
    unittest.main()
