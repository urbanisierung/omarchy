# Omarchy

Turn a fresh Fedora installation into a fully-configured, beautiful, and modern web development system based on Hyprland by running a single command. That's the one-line pitch for Omarchy (adapted from the original Arch version for Omakub). No need to write bespoke configs for every essential tool just to get started or to be up on all the latest command-line tools. Omarchy is an opinionated take on what Linux can be at its best.

**Note**: This version has been adapted for Fedora Linux. The original was designed for Arch Linux.

Read more at [omarchy.org](https://omarchy.org).

## Installation status

Fresh-install repairs are in progress; do not run the installer on your daily-use
workstation to test them. See the [audit and action plan](docs/README.md).
The previously advertised `https://u11g.com/install` endpoint did not return a
usable installer during the audit and has not been repaired or revalidated.

Bootstrap now refuses to replace any existing `~/.local/share/omarchy` path,
including symlinks. A fresh clone is validated in temporary storage before being
published. If installation fails after publication, the checkout is retained for
inspection; rerunning bootstrap will refuse it rather than delete it. Do not
remove your working checkout to bypass this protection. Installation stages are
not yet fully safe to rerun: review the failure and back up affected configuration
before invoking the retained `install.sh` with Bash in a disposable test system.

`OMARCHY_REF` can select a branch, tag, or other fetchable Git ref. Named branches
retain tracking; tags and fetch-only refs produce detached checkouts that the
existing update helper cannot update normally. No ref selection skips validation.

Installer regression tests use temporary homes and fake package/privilege/session
commands; Git integration uses only local repositories. Run all tests with
`python3 -B -m unittest discover -s tests`. These tests do not perform a real
Fedora installation or establish first-login readiness.

For disposable laptop testing, see the [guided Kickstart USB guide](docs/kickstart-usb.md).
It includes ISO preparation/build tooling and a pinned first-login setup offer.
Real ISO boot and fresh-install validation remain outstanding; it is not an
unattended disk-wiping installer.

TODOs: Install eza, yazi

Graphics Intel: https://fostips.com/hardware-acceleration-video-fedora/?amp=1
Start Zoom:

```
[Desktop Entry]
Name=Zoom Workplace
Comment=Zoom Video Conference
Exec=env QT_QPA_PLATFORM=xcb /usr/bin/zoom %U
Icon=Zoom
Terminal=false
Type=Application
Encoding=UTF-8
Categories=Network;Application;
StartupWMClass=zoom
MimeType=x-scheme-handler/zoommtg;x-scheme-handler/zoomus;x-scheme-handler/tel;x-scheme-handler/callto;x-scheme-handler/zoomphonecall;x-scheme-handler/zoomphonesms;x-sche>
X-KDE-Protocols=zoommtg;zoomus;tel;callto;zoomphonecall;zoomphonesms;zoomcontactcentercall;
Name[en_US]=Zoom Workplace
```

## Lock screen status

All themes include the weekday, full date, and year progress above the clock,
a clock above the password field, elapsed lock time below it,
and battery plus system status at the bottom. The calendar uses local time and
refreshes every minute; year progress accounts for leap years. Dark translucent backplates keep
the text readable on light backgrounds. The labels are configured in
`config/hypr/hyprlock-status.conf`; changes appear the next time you lock.

`bin/omarchy-lock-status` uses Python 3's standard library and local Linux system
data only. Lock duration is measured from hyprlock startup, includes suspend time,
and refreshes every 10 seconds. Battery status excludes peripherals and is hidden
when no system battery is available. System status shows one-minute CPU load
(not CPU percentage) and RAM usage based on available memory, also every 10 seconds.
Authentication, display-off behavior, and power profiles are unchanged.

Tests: `python3 -m unittest discover -s tests`.

## License

Omarchy is released under the [MIT License](https://opensource.org/licenses/MIT).
