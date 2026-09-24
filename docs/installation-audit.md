# Fedora installation audit

Date: 2026-09-24. Reviewed checkout: `8d5b9cd` on `dev`.

This is the historical pre-implementation audit; findings and source line numbers
describe that revision. For fixes already implemented and current validation,
see [implementation progress](action-plan.md#implementation-progress). In
particular, bootstrap preservation, the VS Code update-check abort, independent
RPM Fusion checks, and explicit `updatedb` provisioning now have regression tests.
The remaining audit is not a claim that the whole installer has been repaired.

## Verdict

**Do not consider the current installer fresh-install-ready.** It may complete
under favorable conditions, but does not reproduce all the behavior configured
in this repository. The running workstation includes manual setup that the
installer does not encode.

The largest gaps are mismatched application dependencies, incomplete helper
installation, session initialization, stale pre-Lua integration, and unsafe
retry/update behavior. Repair these before adopting additional upstream features.

The corresponding implementation checklist is in [action-plan.md](action-plan.md).

## Scope and verification limits

The review covered bootstrap, the 24 active installation stages, two ignored
stages, runtime configurations, helpers, applications, themes, migrations, and
existing tests.

Observed during read-only verification:

| Check | Result |
| --- | --- |
| Bash syntax | All 34 checked entry-point, active installer, and migration shell files passed |
| Existing tests | All 10 tests passed; coverage concerns lock-screen status and related configuration |
| ShellCheck | Warnings remain, including unchecked directory changes, quoting, masked assignment statuses, and unresolved sourced files |
| Editor diagnostics | No errors reported; not equivalent to full lint or runtime verification |
| Host | Fedora 44, DNF5 5.4.5, Hyprland 0.56.2 |
| Git status | Clean before and after the audit |

No installer, migration, package installation, compositor reload, or system
configuration change was executed. No fresh VM installation was performed.
The installed host is evidence of available mechanisms, not a fresh-image baseline.
Package resolution, source builds, first login, GPU support, suspend, and portal
behavior still need isolated integration tests. The COPR project webpage was
blocked by an anti-bot challenge, so its complete current package matrix was not verified.

### Severity and confidence

- **P0:** blocks the advertised entry point or risks destructive bootstrap behavior.
- **P1:** can abort installation, break core desktop behavior, or lose managed/user state.
- **P2:** optional-feature gaps, portability, reproducibility, and maintenance issues.
- **Confirmed:** directly supported by code or observed behavior.
- **Conditional:** triggered by a particular starting state, image, hardware, or external service.
- **Unverified:** needs package-resolution, VM, or hardware testing; not a proven failure.

## Current execution model

The advertised download invokes bootstrap. Bootstrap clones the repository and
sources `install.sh`. That script enables RPM Fusion, updates the system, sources
every `install/*.sh` in shell glob order, runs `updatedb`, and offers a reboot.

Actual active order:

1. `1-yay.sh`
2. `2-identification.sh`
3. `3-terminal.sh`
4. `4-config.sh`
5. `atuin.sh`
6. `backgrounds.sh`
7. `bluetooth.sh`
8. `desktop.sh`
9. `development.sh`
10. `docker.sh`
11. `fonts.sh`
12. `hyprlandia.sh`
13. `nvidia.sh`
14. `nvim.sh`
15. `printer.sh`
16. `theme.sh`
17. `vscode.sh`
18. `webapps.sh`
19. `xtras.sh`
20. `zed.sh`
21. `zzz_hyprtasking.sh`
22. `zzz_hyprwhspr.sh`
23. `zzz_node.sh`
24. `zzz_window_picker.sh`

`mimetypes.sh.ignore` and `power.sh.ignore` do not execute. The active Bluetooth
stage contains only commented-out setup.

## A01 — Published bootstrap is not returning a usable installer

**P0 · Observed external failure.** [README.md:11](../README.md#L11) advertises
`https://u11g.com/install`. The webpage check returned a 404 page; a local Python
request returned HTTP 403. Responses differed by client, but neither produced an
installer. Do not infer a single universal HTTP response from these observations.

Repair the endpoint and verify both transport success and expected script content.
Provide a direct, documented fallback entry point.

## A02 — Bootstrap deletes the checkout before validating its replacement

**P0 · Confirmed.** [boot.sh:16–17](../boot.sh#L16) deletes the existing checkout
before cloning. Local changes are lost, and clone failure can leave existing
configuration links pointing nowhere. Bootstrap has no independent fail-fast
handling; custom-reference failure is not reliably prevented from falling through.

Preserve existing checkouts, validate a new checkout before use, and distinguish
fresh install from update. Report failures without destroying the last usable copy.

## A03 — Normal update availability can abort installation

**P1 · Confirmed conditional failure.** [install/vscode.sh:4](../install/vscode.sh#L4)
runs `dnf check-update` under the `set -e` established in
[install.sh:5](../install.sh#L5). DNF returns 100 when updates exist, so this normal
result stops installation before VS Code and all later stages. Repositories added
after the initial upgrade can expose further updates.

Remove this unnecessary check or explicitly handle its exit statuses.

## A04 — Prerequisites and support boundaries are implicit

**P1 · Confirmed provisioning gaps; image-dependent failures.**

- [install.sh:11–15](../install.sh#L11) checks only RPM Fusion Free before assuming
  both Free and Nonfree are configured.
- [install.sh:28](../install.sh#L28) requires `updatedb`, but no active stage
  explicitly installs its provider. This host has `plocate`.
- [install/hyprlandia.sh:4](../install/hyprlandia.sh#L4) assumes the DNF COPR command.
- [install/nvidia.sh:12](../install/nvidia.sh#L12) assumes `lspci`.
- [install/4-config.sh:2](../install/4-config.sh#L2) assumes `~/.config` exists.
- There are no declared Fedora release, base-image, architecture, login-session,
  root/non-root, or shell support checks.
- Eza downloads and picker RPM names are explicitly x86_64-specific:
  [install/3-terminal.sh:12](../install/3-terminal.sh#L12),
  [install/zzz_window_picker.sh:60–74](../install/zzz_window_picker.sh#L60).

Resolve package names and third-party repository support against the selected
fresh image before changing user/session configuration. A single unavailable
package can fail an entire transaction; installed packages on this host do not
prove availability for every supported release.

### Docker compatibility qualification

[install/docker.sh:2](../install/docker.sh#L2) uses `dnf-3`, but this is **not a
proven blocker**. On the audited Fedora 44 host, `python3-dnf` provides that
executable, and `dnf-plugins-core` depends transitively on `python3-dnf`.
Use the current DNF5 setup to reduce compatibility dependencies, rather than
claiming the existing executable is universally absent.

## A05 — Configured commands do not match provisioned dependencies

**P1 for core desktop commands; P2 for optional features · Confirmed omissions.**

| Feature | Gap | Evidence |
| --- | --- | --- |
| Terminal | Ghostty configured; Alacritty installed | [hyprland.lua:9](../config/hypr/hyprland.lua#L9), [3-terminal.sh:6](../install/3-terminal.sh#L6) |
| Browser | Google Chrome configured; Chromium installed | [hyprland.lua:13](../config/hypr/hyprland.lua#L13), [desktop.sh:5](../install/desktop.sh#L5) |
| Clipboard | Clipse and wl-clip-persist started but explicitly omitted | [autostart.lua:7](../default/hypr/autostart.lua#L7), [desktop.sh:8–10](../install/desktop.sh#L8) |
| Polkit | hyprpolkitagent started but not provisioned | [autostart.lua:6](../default/hypr/autostart.lua#L6), [hyprlandia.sh:10–11](../install/hyprlandia.sh#L10) |
| Waybar CPU/network | Ghostty and iwctl required | [waybar/config:80](../config/waybar/config#L80), [waybar/config:104](../config/waybar/config#L104) |
| Bluetooth UI | Blueberry expected; setup commented out | [waybar/config:151](../config/waybar/config#L151), [bluetooth.sh](../install/bluetooth.sh) |
| Dropbox | Status command runs every five seconds; installation manual | [waybar/config:175–182](../config/waybar/config#L175), [xtras.sh:9](../install/xtras.sh#L9) |
| Docker UI | Launcher requires Ghostty and uninstalled lazydocker | [Docker.desktop:5](../applications/Docker.desktop#L5), [development.sh:10](../install/development.sh#L10) |
| Modeler | Launcher requires an unmanaged /usr/local/bin/modeler | [Modeler.desktop:5](../applications/Modeler.desktop#L5) |
| Zoom | Launcher supplied; application left manual | [Zoom.desktop:4](../applications/Zoom.desktop#L4), [xtras.sh:10](../install/xtras.sh#L10) |
| Other desktop apps | Spotify, Signal, and 1Password configured but not installed | [hyprland.lua:15–19](../config/hypr/hyprland.lua#L15), [desktop.sh](../install/desktop.sh), [xtras.sh](../install/xtras.sh) |
| Spotlight | Uses jq without explicit provisioning | [spotlight.sh:20–37](../bin/spotlight.sh#L20) |
| Browser terminal helper | ttyd/tmux and lsof are not explicitly provisioned | [bt:10–15](../bin/bt#L10), [bt:30](../bin/bt#L30) |

Choose one installation policy per enabled feature: provision it, explicitly
defer it behind a setup action, or hide/disable its UI until available. Do not
silently substitute unwanted applications merely to make the audit pass.
For networking, prefer Fedora's existing NetworkManager unless an iwd backend
change is a deliberate, fully tested choice.

## A06 — Voice and translation installation is incomplete

**P1/P2 · Confirmed.** Dictation invokes `~/hyprwhspr/transcribe.sh`, but the
installer merely asks the user to place that script manually:
[hyprland.lua:89](../config/hypr/hyprland.lua#L89),
[zzz_hyprwhspr.sh:38](../install/zzz_hyprwhspr.sh#L38).
The managed source is [bin/transcribe.sh](../bin/transcribe.sh).

[bindings.lua:19–25](../default/hypr/bindings.lua#L19) references translation and
Spotlight helpers under `~/.local/bin`, while the installer leaves them in the
repository's `bin/` directory. Translation requires Python packages and offline
models described in [hyprtranslate-docs.md](../hyprtranslate-docs.md), not installed
by the active stages. DeepL additionally needs a user-supplied credential; that
is an optional configuration requirement, not something to commit to the repo.

Provision an isolated Python environment and chosen models, unify launcher paths,
and validate Whisper's executable/model before enabling dictation. Store recording
state privately rather than assuming shared fixed `/tmp` paths are per-user.

## A07 — Login bypasses expected shell initialization

**P1 · Confirmed startup-path gap.**
[install/hyprlandia.sh:14](../install/hyprlandia.sh#L14) replaces `.bash_profile`
with a TTY1 Hyprland `exec` condition and does not source `.bashrc`.
[install/4-config.sh:8](../install/4-config.sh#L8) places Omarchy initialization in
`.bashrc`; the PATH setup is in [default/bash/shell:11](../default/bash/shell#L11).
That setup is therefore not guaranteed through the configured login path.

An existing graphical login manager is not explicitly integrated or replaced.
Choose whether the supported image uses GDM session selection or TTY login.
Preserve existing shell startup behavior and establish the session environment
before launching Hyprland. Remove the relative `./bin` PATH prefix unless its
command-shadowing behavior is intentionally wanted.

## A08 — Autologin policy is not equivalent to authenticated login

**P1 · Confirmed policy gap.**
[install/4-config.sh:10–16](../install/4-config.sh#L10) enables passwordless TTY1
autologin and cites disk encryption plus Hyprlock, but does not check encryption
or immediately start the lock screen. The idle lock is five minutes:
[hypridle.conf:15–16](../config/hypr/hypridle.conf#L15).

Define the intended policy explicitly. Test access after boot, compositor exit,
failed installation, and failed lock startup. Do not claim disk encryption
protects an already unlocked session.

## A09 — Session-service environment needs explicit handling

**P1 · Confirmed keyring scope issue; other behavior needs runtime validation.**
[autostart.lua:10](../default/hypr/autostart.lua#L10) exports keyring variables only
inside a child shell; that cannot set the compositor's or sibling processes'
environment. Input-method setup is split between configuration files and needs
verification with the chosen login mechanism.

Import the necessary graphical environment into user services and D-Bus
activation. Verify GTK/Qt/XWayland input, keyring consumers, portals, and Wofi
actions launched by reminder timers—not just commands from an existing terminal.

## A10 — Remaining installer integration targets pre-Lua configuration

**P1 · Confirmed.** `hyprland.lua` is the correct current Hyprland configuration
entry point; its filename is not a bug. However:

- [nvidia.sh:40–49](../install/nvidia.sh#L40) appends old environment syntax only
  if `hyprland.conf` exists, silently skipping the fresh Lua configuration.
- [zzz_window_picker.sh:254–300](../install/zzz_window_picker.sh#L254) patches the
  same obsolete filename or prints manual Hyprlang instructions. Built picker
  helpers are not automatically integrated into the actual Lua entry point.

Convert these integrations to the selected, tested Lua API. The migration
generator's plugin-dispatcher output also needs a regression test before future
reuse: [hyprlang-to-lua.py:311–312](../bin/hyprlang-to-lua.py#L311).
Do not run it indiscriminately over already-correct configuration.

## A11 — Plugin compatibility and startup ordering are fragile

**P1 · Confirmed missing sequencing; runtime failure is conditional.**
[autostart.lua:15–16](../default/hypr/autostart.lua#L15) launches plugin reload and
plugin configuration separately. Submission order does not establish successful
load completion. The global arrow/Escape bindings assume the plugin is available:
[hyprland.lua:95–99](../config/hypr/hyprland.lua#L95).

[zzz_hyprtasking.sh:10–18](../install/zzz_hyprtasking.sh#L10) uses moving package
and plugin sources and masks `hyprpm add` failure. Validate matching headers/ABI,
installation before first graphical login, plugin permissions, and failed-load
behavior. Apply settings after confirmed load and guard optional bindings.

## A12 — Screen-sharing setup applies broad historical workarounds

**P1 · Confirmed invasive behavior; present necessity unverified.**
[zzz_window_picker.sh](../install/zzz_window_picker.sh) continues after dependency
failures, uses `rpm --replacefiles` or `--allowerasing`, installs a nightly Rust
toolchain, builds moving sources, overwrites portal configuration, and generates
scripts that kill portal processes. It restarts user-session services even when
installation may occur outside a usable Hyprland session.

Relevant sections: [packages:54–74](../install/zzz_window_picker.sh#L54),
[build:85–117](../install/zzz_window_picker.sh#L85),
[configuration/helpers:133–243](../install/zzz_window_picker.sh#L133),
[restart:345–353](../install/zzz_window_picker.sh#L345).

Zoom is not installed, and [Zoom.desktop:4](../applications/Zoom.desktop#L4)
bypasses the generated `zoomw` wrapper. First test the standard portal path,
including GTK file selection. Keep the preview picker if desired, but isolate
workarounds and use them only for reproduced problems.

## A13 — NVIDIA setup does not verify reboot readiness

**P1 · Hardware-dependent.** [nvidia.sh:21–38](../install/nvidia.sh#L21) installs
drivers then immediately regenerates initramfs. It lacks a complete Secure Boot
enrollment/signing path, explicit akmod completion checks, target-kernel
verification after system upgrade, and supported GPU/driver selection.

Validate the actual driver package providers on the target release. Confirm
kernel-module readiness before rebuilding the relevant initramfs and rebooting.
Do not classify every NVIDIA system as broken, but do not claim support without
these hardware tests.

## A14 — Power support must recognize Fedora's existing provider

**P2 · Image-dependent provisioning gap, not a confirmed host failure.** The
power install stage is ignored, but
[omarchy-powerprofile:3–4](../bin/omarchy-powerprofile#L3) intentionally uses the
PowerProfiles D-Bus API. This host supplies it through `tuned-ppd`, without the
`power-profiles-daemon` package.

Validate the API, permissions, and supported profiles. Preserve a working
provider rather than blindly installing a conflicting daemon. Test machines
without batteries and those lacking a performance profile.

## A15 — Personal machine assumptions leak into defaults

**P2 · Confirmed references; impact varies by user/hardware.**

- Private dotfiles startup: [autostart.lua:9](../default/hypr/autostart.lua#L9).
- DP-3/eDP-1 monitor layout: [monitors.lua:8–18](../config/hypr/monitors.lua#L8).
- Global display scale: [hyprland.lua:45](../config/hypr/hyprland.lua#L45).
- Private prompt collection: [omarchy-show-prompts:17](../bin/omarchy-show-prompts#L17).
- `/home/adam` wallpaper: [themes/nord/hyprlock.conf:13](../themes/nord/hyprlock.conf#L13).
  Tokyo Night is the initial theme, so this is not a universal first-login failure.
- Apple brightness bindings require unprovisioned `asdcontrol`:
  [apple-display-brightness:3–6](../bin/apple-display-brightness#L3).
- AirPods helper expects user-specific device configuration:
  [omarchy-airpods-toggle:9–23](../bin/omarchy-airpods-toggle#L9).
- Fingerprint setup still uses `yay`:
  [omarchy-fingerprint-setup:3](../bin/omarchy-fingerprint-setup#L3).

Keep personal choices in a small explicit override/profile layer. Defaults must
not require a particular username, private checkout, or peripheral. Enabling
fingerprint configuration is not evidence that Fedora enrollment is provisioned.

## A16 — Shared-shell orchestration has real hidden dependencies

**P1 · Confirmed.** [install.sh:25](../install.sh#L25) sources every stage, sharing
working directory, options, traps, functions, and variables. The picker stage
enables stricter shell options globally. The Whisper stage changes directory.

This is not fixed by mechanically replacing `source` with `bash`:
[theme.sh:16](../install/theme.sh#L16) depends on the background helper and variable
established by [backgrounds.sh:1–9](../install/backgrounds.sh#L1).

Make stage order and inputs explicit, remove accidental sharing, then isolate
stages. Move graphical activation after provisioning. Include useful failure
context and a safe retry procedure; the current error trap is installed only
after repository setup and the initial system upgrade.

## A17 — Reruns and configuration ownership can lose user state

**P1 · Confirmed.**

- Configs are overlaid without backup: [4-config.sh:2](../install/4-config.sh#L2).
- Shell startup files are replaced: [4-config.sh:8](../install/4-config.sh#L8),
  [hyprlandia.sh:14](../install/hyprlandia.sh#L14).
- Docker configuration is replaced: [docker.sh:8](../install/docker.sh#L8),
  [migration 1751669258](../migrations/1751669258.sh).
- Neovim bootstrap is skipped if its executable exists; otherwise its existing
  configuration is deleted: [nvim.sh:1–9](../install/nvim.sh#L1).
- Selected configs can be manually linked with no backup policy:
  [omarchy-config-link:8–11](../bin/omarchy-config-link#L8).

The repository already contains `config/nvim/lua/plugins/theme.lua`; a missing
theme parent directory is not a demonstrated true-fresh-install blocker. The
real Neovim issue is inconsistent bootstrap depending on preexisting software.

Choose which files are user-owned, managed links, or generated state. Back up or
merge user-owned files. Test reruns through existing symlinks as well as files.
Docker group membership grants root-equivalent access and must be an explicit
policy decision. CUPS and other enabled services should likewise be intentional.

## A18 — Updates can forget failed migrations and leave mixed config versions

**P1 · Confirmed.** [omarchy-update:9–23](../bin/omarchy-update#L9) selects
migrations using the old commit timestamp, pulls, and sources migration files
without a durable completion journal. A failed migration can be skipped next
time because Git has already advanced. Pull failure is not explicitly handled.

Fresh installs copy entry-point configs, load some defaults directly from the
repo, and link themes. Updates do not reconcile all copied configs or install
new stages automatically. This permits stale entry points with newer defaults.
Application synchronization is not part of update. The Waybar migration uses
`sed -i`, which can replace a managed symlink rather than preserving it:
[migration 1751225707](../migrations/1751225707.sh).

Track successful migrations by ID, stop on failure, and define the initial
baseline for new installations without blindly replaying destructive history.
Install replacement functionality before removing the old version; review
[migration 1751667620](../migrations/1751667620.sh) with that ordering in mind.

## A19 — Downloads, themes, and application synchronization need validation

**P2 · Confirmed robustness gaps; external failures are conditional.**

- Several installers execute remote scripts or consume moving latest releases:
  [atuin.sh](../install/atuin.sh), [zed.sh](../install/zed.sh),
  [3-terminal.sh](../install/3-terminal.sh), [fonts.sh](../install/fonts.sh),
  [zzz_node.sh](../install/zzz_node.sh), and source-build stages.
  The NVM script tag is pinned, but Node/global npm packages still move.
- Shared `/tmp` filenames and archive assumptions make retries less reliable.
- Wallpaper/icon downloads do not reject HTTP error responses:
  [backgrounds.sh:6](../install/backgrounds.sh#L6),
  [default/bash/functions](../default/bash/functions).
- Theme and wallpaper cycling assume nonempty candidate lists and use fragile
  whitespace splitting: [omarchy-theme-next:6–28](../bin/omarchy-theme-next#L6),
  [swaybg-next:8–30](../bin/swaybg-next#L8).
- Application synchronization overwrites files, does not track retired assets,
  and its installer invocation masks failure:
  [omarchy-sync-applications](../bin/omarchy-sync-applications),
  [xtras.sh:15](../install/xtras.sh#L15).
- GSettings theme setup needs validation in the supported installation session:
  [theme.sh:6–7](../install/theme.sh#L6).

Validate downloads before replacing working assets, pin compatibility-sensitive
builds, preserve user-owned launchers, and surface mandatory failures. Select a
valid next wallpaper before stopping the existing wallpaper process.

## A20 — Documentation and tests do not establish installer readiness

**P2 · Confirmed.** Existing tests cover lock status, not bootstrap, stage ordering,
package provisioning, migrations, or first login. The conversion summary is
historical: claims about package conversion and available scripts are not a
current support matrix. `PLAN.md` primarily proposes feature additions.

Add installation contract tests and fresh-VM evidence. Update documentation only
to claim support for combinations actually tested. Preserve the existing tests.

## External references checked

- [Hyprland configuration entry point](https://wiki.hypr.land/Configuring/Start/)
- [Hyprland plugin requirements and loading](https://wiki.hypr.land/Plugins/Using-Plugins/)
- [Hyprland portal behavior](https://wiki.hypr.land/Hypr-Ecosystem/xdg-desktop-portal-hyprland/)
- [DNF5 update-check exit statuses](https://dnf5.readthedocs.io/en/latest/commands/check-upgrade.8.html)
- [Current Docker Fedora installation](https://docs.docker.com/engine/install/fedora/)
- [Docker group privileges](https://docs.docker.com/engine/install/linux-postinstall/)

External pages and repository/package availability can change. Revalidate them
against the selected Fedora and Hyprland versions during implementation.
