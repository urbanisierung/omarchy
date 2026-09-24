# Guided Fedora Kickstart USB

Status: implementation and isolated validation only; **no ISO/VM/physical install
sign-off yet**. This is disposable test media, not a supported unattended installer.
The existing [installation repair plan](action-plan.md) still applies.

## Current handoff (2026-09-24)

- Generated and syntax-validated preparation: `~/.cache/omarchy-usb/6ebb8ba-guided`.
- Pinned installer: `6ebb8baf578bb328583a209fe795209e26b323e7`; remote `dev`
  matched this hash when checked. This directory is not a bootable ISO.
- All 57 unittests, Bash syntax, ShellCheck, shfmt, Ruff formatting/lint and
  Fedora 44 Kickstart syntax checks pass. Build/privilege operations are mocked.
- Next: install the host tools below, obtain a signature-verified source ISO,
  and build into a **different, new** output directory. VM and USB gates remain open.

## Design and limits

- Fedora 44 Everything network installer, x86_64, mutable Workstation/GNOME base.
  This is a test baseline, not a change to the project's eventual support contract.
- Fedora's installer handles disk selection/reclamation, encryption, timezone,
  keyboard and account setup interactively. No hardcoded disk, automatic
  `clearpart`, partition layout, username, password, or encryption passphrase.
  Create an administrator account; root password login is locked.
- `%post` only installs the first-login payload and selects the graphical target.
  It does not execute the project installer. It halts at completion so you can
  remove the USB before booting the installed system.
- The GNOME login offers setup in a terminal. Type `INSTALL` to proceed; anything
  else defers until a later login. Use the normal administrator account, not root.
- The bootstrap comes from the selected committed revision; `OMARCHY_REF` pins
  the checkout to that same full hash. The bootstrap's existing GitHub repository
  remains unchanged. Push the commit before trying it on another machine.
- The USB assets come from this working tree, including uncommitted edits. The
  generated manifest hashes them separately from the pinned installer revision.
- Internet is needed throughout; Ethernet is recommended. No Wi-Fi credentials
  or GitHub tokens are embedded. This is not an offline package cache.
- Existing installer behavior is **not repaired by Kickstart**: it overwrites
  configs, enables TTY autologin, adds third-party repositories, and may fail on
  package/plugin/session setup. GNOME is available as a fallback, but final login
  behavior is not yet verified. Review NVIDIA/Secure Boot requirements separately;
  do not disable Secure Boot just to bypass an unexplained failure.
- Pinned checkouts are detached. Do not use the current normal Git-pull updater
  until a deliberate, reviewed switch to a tracking branch has been made.

## Space

Planning allowances, not measured minimums: 8 GB USB (16 GB recommended), 10–15 GB
host build space, 80 GB sparse VM disk, and 100 GB or more target storage. Leave
additional space for development data, Docker images, models and source builds.

## 1. Prepare the Fedora host

Run these steps yourself in a terminal. Adding the repository files changes no
system packages or disks.

Install build tools with `sudo dnf install lorax pykickstart mediawriter`.
Use `python3` to invoke the builder; it is deliberately not an executable entry
under the desktop's `bin/` directory or the sourced `install/` stages.

From the repository root, preparation without an ISO or privileges is:

`python3 -B tools/build-kickstart-iso.py --ref HEAD --prepare-only --output-dir "$HOME/.cache/omarchy-usb/prepared"`

The output directory must not exist (including dangling symlinks). Preparation
uses committed `boot.sh`, not its working-tree edits. It writes `kickstart.ks`,
`omarchy-usb/` and `manifest.json`. Missing `ksvalidator` is explicitly reported;
preparation alone never creates a bootable image.

## 2. Download and verify the source ISO

Use [Fedora Everything 44](https://fedoraproject.org/misc/#everything), Intel/AMD
x86_64 Network Install, **not Workstation Live, Server, Atomic or ARM media**.
Download the accompanying CHECKSUM file. Follow Fedora's Verify instructions to
verify its signature with Fedora's OpenPGP certificate, then the image SHA256.

Keep the original image, signed checksum and verification result. The builder's
`--sha256` check detects mismatches; it does not authenticate Fedora's signature
or establish that an arbitrary input file is a Fedora installer.

## 3. Build

Authenticate with `sudo -v` directly in your terminal, then run the following
from the repository root after replacing the ISO path and checksum placeholder:

`python3 -B tools/build-kickstart-iso.py --ref HEAD --iso "$HOME/Downloads/Fedora-Everything-netinst-x86_64-44-1.7.iso" --sha256 VERIFIED_SHA256 --output-dir "$HOME/.cache/omarchy-usb/build-1"`

The build validates Kickstart with `ksvalidator -v F44`, then invokes
`sudo -n mkksiso` to embed the payload and update EFI boot configuration. Do not
use `--skip-mkefiboot`: a virtual CD boot is not proof of UEFI USB boot support.
If sudo authorization is unavailable, the build stops rather than prompting or
retrying. Keep any partial output for diagnosis and use a new directory on retry.

A successful build writes `omarchy-fedora44-x86_64.iso` and `SHA256SUMS` alongside
the preparation manifest. The builder does not download images, install packages,
choose a disk, flash media, or run the workstation installer on the build host.

## 4. VM gate before USB

Use virt-manager or another local hypervisor. If needed, install Fedora's
`virt-manager`, `qemu-kvm` and `edk2-ovmf` packages and configure local libvirt.
Create a disposable VM with UEFI firmware, 4 virtual CPUs, 8 GB RAM, an 80 GB
sparse virtual disk, and NAT networking. Attach the custom ISO. **Never pass
through host disks, USB storage or your home directory.**

Verify all of these before calling the image ready:

- [ ] Installer waits for storage selection; no disk is silently erased.
- [ ] Select only the VM disk, reclaim it, and test encrypted installation with
  a passphrase entered locally. Also test unencrypted storage if needed.
- [ ] Create an administrator account during installation or first-boot setup.
  Verify it can sign in and use sudo before starting the project installer.
- [ ] At completion remove the virtual ISO, then boot the installed disk.
- [ ] GNOME opens the setup offer. Deferring performs no project installation.
- [ ] Accepting runs the recorded commit interactively, with a private log.
- [ ] Failures preserve logs and checkout and do not rerun on the next login.
- [ ] Decline the project installer's reboot prompt; inspect results, then reboot.
- [ ] Check graphical login, terminal/browser bindings, network, sound and lock.

VM results do not establish laptop GPU, Secure Boot driver, suspend or UEFI USB
compatibility. Record ISO hash, manifest, firmware, logs and remaining failures.

## 5. Flash and use the USB

1. Back up the USB. Disconnect unrelated removable storage on the build machine.
2. Open Fedora Media Writer, choose **Select .iso file** (custom/local image),
   and select the generated ISO, not the original Fedora download.
3. Identify the USB by model and capacity, then confirm writing. **All existing
   USB contents are lost.** Let write verification finish before ejecting it.
4. On the spare laptop, disconnect other storage, connect power and network,
   and choose the USB's UEFI entry from the firmware boot menu.
5. In Fedora's installer, identify the intended internal disk by model/capacity.
   Select/reclaim only that disk, not the USB. Choose encryption and enter all
   passwords locally. Disk reclamation destroys the selected disk's data.
6. Complete Fedora setup, remove the USB when installation finishes, and reboot.
7. Sign into GNOME as the administrator user and respond to the setup offer.

## Logs and recovery

- Fedora staging: `/var/log/omarchy-usb-stage.log`; Anaconda: `/var/log/anaconda/`.
- User setup: `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-usb/` contains
  `attempted`, `install.log`, `exit-status`, and `completed` on exit status zero.
- `script` records terminal output only, not raw input; do not enable input
  logging for password prompts. Output can still contain personal data/secrets
  printed by downloaded software: review and redact before sharing logs.
- An attempted marker is written before sudo/network work. An interrupted reboot
  may leave no exit status or completion marker. That is **not success**, and it
  will not automatically rerun. A lock also blocks concurrent launcher instances.
- If you deferred, run `bash /usr/local/lib/omarchy-usb/setup.sh` in a terminal.
  After an attempt it only reports the recovery location. There is deliberately
  no `--force` or automatic-resume option. Review the failed stage and back up
  config before manually repairing the retained checkout or reinstalling the VM.
- The GNOME autostart entry remains installed; after an attempt its launcher
  exits without reinstalling (a terminal may briefly appear).

## Implementation validation

Run `python3 -B -m unittest discover -s tests`,
`shellcheck installer/kickstart/setup.sh`, and
`ksvalidator -v F44 installer/kickstart/fedora44.ks`.
Python formatting/lint checks cover the builder and its test file with Ruff.
Tests use temporary homes, pseudo-terminals, fake privilege/session commands and
mocked ISO builds. They never run a real project installer or flash media.

References: [mkksiso](https://weldr.io/lorax/mkksiso.html),
[Kickstart syntax](https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html),
[Fedora Media Writer](https://github.com/FedoraQt/MediaWriter).
