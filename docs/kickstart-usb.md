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

**Use virt-manager (Virtual Machine Manager) with KVM/QEMU and libvirt.** It is
Fedora-native and exposes firmware, boot order, graphics and storage explicitly.
GNOME Boxes is simpler, but virt-manager is a better fit for this installer test;
VirtualBox would add an unnecessary virtualization stack.

Host check on 2026-09-24: KVM is accessible, libvirt's QEMU/network/storage sockets
are active, OVMF is installed, and about 38 GiB RAM is available. Only
`virt-manager` was identified as missing in that initial check; a subsequent
launch exposed a missing desktop polkit agent (see recovery below).
The custom ISO was found at
`~/.cache/omarchy-usb/build-2/omarchy-fedora44-x86_64.iso`.
These are preparation checks, **not a successful VM boot**.

### 4.1. Install the UI and make the ISO accessible

Run these commands yourself on the **host**, not inside the guest:

1. Install the UI: `sudo dnf install virt-manager`.
  No libvirt restart or group-membership change is needed on the checked host.
2. Verify the built image:
  `cd "$HOME/.cache/omarchy-usb/build-2" && sha256sum -c SHA256SUMS`.
  Stop if verification fails. Substitute your actual build directory if different.
3. System libvirt runs QEMU under a separate account. Copy only the ISO into its
  standard storage directory rather than loosening permissions on your home:
  `sudo install -m 0644 "$HOME/.cache/omarchy-usb/build-2/omarchy-fedora44-x86_64.iso" /var/lib/libvirt/images/omarchy-fedora44-build-2.iso`.
  This destination is a dedicated test ISO; the command replaces it if repeated.
  Choose a different filename if that name already holds something you need.
4. Apply Fedora's expected SELinux label:
  `sudo restorecon -v /var/lib/libvirt/images/omarchy-fedora44-build-2.iso`.
  Verify the copy with
  `sudo cmp -- "$HOME/.cache/omarchy-usb/build-2/omarchy-fedora44-x86_64.iso" /var/lib/libvirt/images/omarchy-fedora44-build-2.iso`;
  success produces no output. Do not disable SELinux to fix an access error.
5. Launch `virt-manager --connect qemu:///system` as your normal desktop user.
  Approve local administrator authentication if requested; do not run the GUI
  with sudo. Use **QEMU/KVM**, not **QEMU/KVM user session**.

  #### If launch reports "no polkit agent available"

  On this Hyprland host, polkit was running but no desktop authentication agent
  was installed. The old startup command referenced a nonexistent
  `hyprpolkitagent` user service. This prevents libvirt's normal administrator
  prompt; it is not a QEMU or socket-permission failure.

  1. On the **host**, install Fedora's agent: `sudo dnf install polkit-kde`.
  2. Start it once in the current Hyprland session, as your normal user:
    `hyprctl eval 'hl.exec_cmd("/usr/libexec/kf6/polkit-kde-authentication-agent-1")'`.
    This Lua-based Hyprland build requires the Lua API; legacy
    `hyprctl dispatch exec ...` syntax is parsed as Lua and fails.
    Do not start another copy if an agent is already running.
  3. Reconnect the QEMU/KVM connection in virt-manager (or relaunch
    `virt-manager --connect qemu:///system`). Enter your administrator password
    only in the local authentication dialog.

  The repository's active `default/hypr/autostart.lua` now starts this agent on
  future Hyprland logins, and `install/hyprlandia.sh` provisions its package.
  The current host links to that config, so no config copy is needed. A config
  reload does not replay the startup event; use step 2 for this session.
  Do not run virt-manager as root, disable polkit, loosen socket permissions, or
  add passwordless libvirt rules to work around a missing agent. Runtime recovery
  is not verified until the package is installed and the connection succeeds.
  Existing ISOs pinned to older commits do not receive this installer fix;
  commit/push and rebuild with the new revision for subsequent guest tests.

#### If authentication reports "access denied by policy"

Do not assume this requires broader permissions. On 2026-10-06, the polkit
journal recorded failed authentication at the same time the KDE authentication
agent crashed with SIGSEGV. The user was already in `wheel`, the local Wayland
session was active, and `org.libvirt.unix.manage` required administrator
authentication (`auth_admin_keep`). No coredump was retained to identify the
crashing component.

The session forced `QT_STYLE_OVERRIDE=kvantum`. As a diagnostic workaround,
after confirming the crashed agent was no longer running, it was restarted with
Qt's built-in style for this process only:

`hyprctl eval 'hl.exec_cmd("env QT_STYLE_OVERRIDE=Fusion /usr/libexec/kf6/polkit-kde-authentication-agent-1")'`

The replacement process started with `QT_STYLE_OVERRIDE=Fusion`. Reconnect in
virt-manager and authenticate in the local dialog to test it. **Successful
authorization and a Kvantum root cause are not yet confirmed.** Do not launch
a duplicate agent, change global Qt settings, or add permissive polkit rules.
This override is session-only; the normal autostart configuration is unchanged.
If it crashes again, inspect `journalctl -b -u polkit --since '-5 minutes'` and
`journalctl -b _EXE=/usr/libexec/kf6/polkit-kde-authentication-agent-1 --since '-5 minutes'`
before choosing another fix.

On another Fedora host, the corresponding prerequisites are `virt-manager`,
`qemu-kvm`, `libvirt-daemon-kvm`, `libvirt-daemon-config-network` and `edk2-ovmf`.
Check `/dev/kvm` exists; if it does not, check firmware virtualization settings
(Intel VT-x / AMD-V). For a host already using modular libvirt, inactive sockets
can be started with
`sudo systemctl enable --now virtqemud.socket virtnetworkd.socket virtstoraged.socket`.
Do not switch daemon architectures on a host with existing VMs; see
[libvirt's daemon checks](https://libvirt.org/daemons.html#checking-whether-modular-monolithic-mode-is-in-use).

### 4.2. Create the disposable VM

1. In virt-manager select **QEMU/KVM → File → New Virtual Machine**.
2. Choose **Local install media (ISO image or CDROM)**, then **Browse** and select
  `/var/lib/libvirt/images/omarchy-fedora44-build-2.iso` from the default pool.
  Refresh the pool if the copied file is not listed. Do not select the original
  Fedora download. If OS detection fails, disable automatic detection and choose
  **Fedora 44**, or the newest Fedora entry available.
3. Allocate **8192 MiB RAM** and **4 CPUs**.
4. Choose **Create a disk image for the virtual machine**, sized **80 GiB**.
  Use a new sparse **qcow2** file in the default storage pool, not an existing
  disk or a `/dev/...` device. Its host disk usage grows as the guest writes data.
5. Name it **omarchy-fedora44-test**. Select **Virtual network 'default': NAT**,
  and check **Customize configuration before install**, then **Finish**.
  If the default network is inactive, allow virt-manager to start it. If it is
  missing, open the connection's **Details → Virtual Networks**, use **+** to
  create a NAT network with DHCP and an unused subnet, and select that network.
  Do not bridge the guest directly onto the physical LAN.
6. In **Overview**, select **UEFI x86_64 / OVMF** firmware, not BIOS, before the
  first boot. For the plain UEFI test on this host, choose the entry pointing to
  `/usr/share/edk2/ovmf/OVMF_CODE.fd`. Its installed firmware descriptor pairs it
  with `/usr/share/edk2/ovmf/OVMF_VARS.fd`; libvirt creates the guest's own variable
  store from that template. Do not select `OVMF.qemuvars.fd` for this workflow
  (see recovery below). Record whether the selected firmware enables Secure Boot;
  don't toggle host Secure Boot or claim Secure Boot coverage from plain UEFI testing.
7. For Hyprland testing, select **Video → Virtio → 3D acceleration** and
  **Display Spice → Listen type: None → OpenGL**. Apply the changes. This uses a
  virtual GPU, not PCI GPU passthrough. If the host cannot provide accelerated
  graphics, record that blocker; a GNOME-only software-rendered boot does not
  pass the Hyprland graphics check.
8. Under **Boot Options**, enable the virtual CD-ROM before the virtual disk.
  Review the device list: exactly one new virtual hard disk, the ISO, and a NAT
  network adapter. **Never add host-disk/USB passthrough or a shared home folder.**
9. Click **Begin Installation**. Let the ISO's default installer entry boot;
  do not replace its kernel arguments, which include the embedded Kickstart.

NAT provides guest internet access for the network installer. It is not complete
network isolation: the guest can still initiate connections to the host or LAN.
Leave unrelated USB devices disconnected from the VM and do not use this setup
to run untrusted images.

#### If creation reports "unable to find any master var store"

On 2026-10-06, the virt-manager log showed `OVMF.qemuvars.fd` configured as a
`pflash` loader. The installed `90/91-edk2-ovmf-qemuvars-*.json` descriptors instead
map this firmware to `memory` with the newer QEMU `uefi-vars` backend and a JSON
variable template. It is valid firmware, but not a traditional CODE/VARS pair;
libvirt cannot find a matching pflash variable-store template for that selection.

1. Dismiss the creation error and return to the pre-install customization window,
  **Overview → Firmware**. The guest has not booted from this failed attempt.
2. Choose the UEFI entry ending in **`OVMF_CODE.fd`**, not `OVMF.qemuvars.fd`,
  `OVMF_VARS.fd`, or a stateless/TDX/SEV variant. Keep the **Q35** chipset.
3. Click **Apply**, then **Begin Installation** again. This changes only the VM's
  firmware choice; keep the existing ISO and dedicated virtual disk.
4. If the firmware selector is unavailable, return to the creation wizard and
  select **Customize configuration before install** again. Do not delete disks
  or variable stores belonging to existing installed VMs to resolve this error.

Both files in the plain pair were confirmed installed; their mapping is in
`/usr/share/qemu/firmware/51-edk2-ovmf-2m-raw-x64-nosb.json`.
For a separate Secure Boot test, use the traditional secure-boot firmware profile
with enrolled keys: `OVMF_CODE.secboot.fd` + `OVMF_VARS.secboot.fd`, Q35 and SMM,
as described by `31-edk2-ovmf-2m-raw-x64-sb-enrolled.json`. Do not mix templates or
overwrite the shared files under `/usr/share/edk2/ovmf`.
No ISO rebuild, package reinstall, or host Secure Boot change is required for
this loader/backend mismatch. Successful guest boot remains to be verified.

### 4.3. Install, eject the ISO, and test the first login

1. In Fedora's installer select **only the 80 GiB virtual disk** (usually `vda`).
  Reclaim its space if prompted. Enter encryption/account passwords locally and
  create an administrator account when offered. No physical host disk should
  appear; stop if the storage list is unexpected.
2. Complete installation. Kickstart requests a halt rather than a reboot. If the
  guest remains on a halted screen, it can now be powered off in virt-manager;
  do not force it off while installation is writing data.
3. With the VM off, open **Show virtual hardware details → CD-ROM → Disconnect**
  (or clear the ISO source), then **Apply**. This ejects the media; it does not
  delete the ISO. Set the virtual disk first under **Boot Options** and click
  **Run**. If you see the installer again, power off and check the CD-ROM source
  and boot order.
4. Complete first-boot account setup if necessary and sign into **GNOME**. In a
  guest terminal verify `sudo -v` works. The setup offer must allow you to defer:
  first enter something other than `INSTALL` and verify no project checkout was
  created. Reopen it inside the guest with
  `bash /usr/local/lib/omarchy-usb/setup.sh` when ready.
5. Type `INSTALL` in the **guest's** setup terminal. Follow its prompts and decline
  the final automatic reboot so it can record the result. Inspect the logs below,
  then reboot the guest manually and complete the checklist.
6. If an attempt fails, keep its logs before repairing or starting a fresh VM.
  Reopening the launcher deliberately does not retry an attempted installation.
  When deleting a test VM, select only its dedicated qcow2 disk for removal;
  preserve the ISO, manifest and collected evidence.

### 4.4. Acceptance checklist

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
