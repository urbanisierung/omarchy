import importlib.machinery
import importlib.util
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "lock_status", str(ROOT / "bin/omarchy-lock-status")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
status = importlib.util.module_from_spec(spec)
loader.exec_module(status)


def process_stat(pid, name, parent, started):
    return f"{pid} ({name}) S {parent} " + "0 " * 17 + str(started)


class LockStatusTests(unittest.TestCase):
    def test_calendar_date_and_year_progress(self):
        for instant, expected in (
            ((2026, 1, 1), "Thursday · 01 January 2026\nYear progress · 0.0%"),
            ((2026, 7, 2, 12), "Thursday · 02 July 2026\nYear progress · 50.0%"),
            ((2024, 7, 2), "Tuesday · 02 July 2024\nYear progress · 50.0%"),
            ((2024, 2, 29), "Thursday · 29 February 2024\nYear progress · 16.1%"),
            ((2026, 12, 31), "Thursday · 31 December 2026\nYear progress · 99.7%"),
            ((2027, 1, 1), "Friday · 01 January 2027\nYear progress · 0.0%"),
        ):
            with (
                self.subTest(instant=instant),
                patch.object(status, "datetime") as clock,
            ):
                clock.now.return_value.astimezone.return_value = datetime(
                    *instant, tzinfo=timezone.utc
                )
                self.assertEqual(status.calendar_status(), expected)
                clock.now.return_value.astimezone.assert_called_once_with()

    def test_duration_units(self):
        for seconds, expected in (
            (-1, "<1m"),
            (0, "<1m"),
            (59, "<1m"),
            (60, "1m"),
            (3599, "59m"),
            (3600, "1h 0m"),
            (86400 + 3660, "1d 1h 1m"),
        ):
            with self.subTest(seconds=seconds):
                self.assertEqual(status.format_duration(seconds), expected)

    def test_duration_walks_ancestors_and_includes_suspend(self):
        stats = {
            "/proc/30/stat": process_stat(30, "sh (label)", 20, 99999),
            "/proc/20/stat": process_stat(20, "hyprlock", 1, 10000),
        }
        with (
            patch.object(status.os, "getppid", return_value=30),
            patch.object(status.Path, "read_text", lambda p: stats[str(p)]),
            patch.object(status.os, "sysconf", return_value=100),
            patch.object(status.time, "clock_gettime", return_value=3760) as clock,
        ):
            self.assertEqual(status.lock_duration(), "Locked for 1h 1m")
            clock.assert_called_once_with(status.time.CLOCK_BOOTTIME)

    def test_duration_without_locker_is_empty(self):
        with (
            patch.object(status.os, "getppid", return_value=20),
            patch.object(
                status.Path, "read_text", return_value=process_stat(20, "sh", 1, 0)
            ),
        ):
            self.assertEqual(status.lock_duration(), "")

    def test_duration_when_parent_exits_is_empty(self):
        with (
            patch.object(status.os, "getppid", return_value=20),
            patch.object(status.Path, "read_text", side_effect=FileNotFoundError),
        ):
            self.assertEqual(status.lock_duration(), "")

    def test_battery_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(status, "Path", return_value=root):
                self.assertEqual(status.battery_status(), "")
                for name, values in {
                    "AC": {"type": "Mains"},
                    "BAT0": {
                        "type": "Battery",
                        "scope": "System",
                        "capacity": "99",
                        "status": "Not charging",
                    },
                    "mouse": {"type": "Battery", "scope": "Device"},
                    "missing": {"type": "Battery"},
                }.items():
                    supply = root / name
                    supply.mkdir()
                    for key, value in values.items():
                        (supply / key).write_text(value)
                self.assertEqual(status.battery_status(), "Battery 99% · not charging")
                for source, expected in (
                    ("Charging", "charging"),
                    ("Discharging", "discharging"),
                    ("Full", "full"),
                    ("Unknown", "unknown"),
                ):
                    (root / "BAT0/status").write_text(source)
                    self.assertEqual(
                        status.battery_status(), f"Battery 99% · {expected}"
                    )

    def test_memory_uses_available_not_free(self):
        with (
            patch.object(
                status.Path,
                "read_text",
                return_value="MemTotal: 8388608 kB\nMemAvailable: 6291456 kB\nMemFree: 0 kB\n",
            ),
            patch.object(status.os, "getloadavg", return_value=(0.25, 1, 2)),
        ):
            self.assertEqual(
                status.system_status(), "CPU load (1m) 0.25 · RAM 2.0/8.0 GiB"
            )

    def test_labels_render_above_dark_backplates(self):
        text = (ROOT / "config/hypr/hyprlock-status.conf").read_text()
        shapes = re.findall(r"^shape \{(.*?)^\}", text, re.MULTILINE | re.DOTALL)
        labels = re.findall(r"^label \{(.*?)^\}", text, re.MULTILINE | re.DOTALL)
        self.assertEqual(len(shapes), 4)
        self.assertEqual(len(labels), 5)
        for shape in shapes:
            self.assertIn("color = rgba(15,18,24,0.75)", shape)
            self.assertIn("zindex = 0", shape)
        for label in labels:
            self.assertIn("zindex = 1", label)

    def test_calendar_panel_is_above_clock(self):
        text = (ROOT / "config/hypr/hyprlock-status.conf").read_text()
        labels = re.findall(r"^label \{(.*?)^\}", text, re.MULTILINE | re.DOTALL)
        calendar = next(
            label for label in labels if "omarchy-lock-status calendar" in label
        )
        self.assertIn("cmd[update:60000]", calendar)
        self.assertIn("position = 0, 275", calendar)
        clock = next(label for label in labels if "text = $TIME" in label)
        self.assertIn("position = 0, 150", clock)

    def test_all_themes_include_shared_labels(self):
        configs = [ROOT / "config/hypr/hyprlock.conf"]
        configs.extend((ROOT / "themes").glob("*/hyprlock.conf"))
        for config in configs:
            with self.subTest(config=config):
                text = config.read_text()
                self.assertIn("$lock_text = rgba(", text)
                self.assertEqual(
                    text.count(
                        "source = ~/.local/share/omarchy/config/hypr/hyprlock-status.conf"
                    ),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
