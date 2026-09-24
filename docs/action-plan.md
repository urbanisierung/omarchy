# Installation repair and project identity action plan

Date: 2026-09-24. Status: first safety batch and guided USB tooling implemented;
overall plan in progress.

This checklist implements the findings in [installation-audit.md](installation-audit.md).
Checked items have focused implementation/test coverage, not fresh-VM sign-off.
Source locations in the audit describe the original reviewed checkout.

## Implementation progress

### Batch 1: Bootstrap and early-failure safety

Implemented without changing desktop configuration, applications, services,
login policy, executable names, or stage order:

- Bootstrap refuses existing files, directories, and symlinks before any package
  or Git operations. It never removes an existing checkout to retry installation.
- New clones are staged privately, validated for a nonempty, syntax-valid
  installer, and published without replacing a competing destination. Failed
  clone/ref/validation operations remove only their temporary staging directory.
- Invalid refs stop bootstrap. Named branches retain upstream tracking; tags and
  other fetched refs use detached HEAD. Existing update tooling still requires a
  tracking branch; detached checkouts must not be treated as normal update targets.
- Installation runs in a child Bash so its variables and traps cannot replace
  bootstrap cleanup state. Stage-to-stage sourcing remains unchanged.
- RPM Fusion Free and Nonfree are checked independently. `plocate` is explicitly
  provisioned before final `updatedb`; setup/upgrade failures receive diagnostics.
- VS Code no longer aborts because `dnf check-update` returns 100.
- Declining reboot returns success; other prompt failures still propagate.

Validation: 26 new isolated installation tests plus all 10 existing tests pass.
The test harness uses temporary HOME directories and a restricted command path;
privileged/package/reboot commands are fakes. Git integration tests use local
repositories with only the file protocol allowed, no system Git configuration,
and hooks disabled. No real installer stages or system operations were run.
The three changed shell scripts pass Bash syntax checks and ShellCheck;
`git diff --check` passes. Dedicated Python/shell formatters are not installed;
formatting was reviewed manually. Fresh-VM testing remains outstanding.

This batch deliberately implements policy-independent safety fixes before Phase 0
decisions. It does not fix the published download endpoint, make all installer
reruns safe, validate downloaded script authenticity, or certify Fedora support.

## Guided USB tooling: test-media preparation

Implemented separately from the existing sourced installer stages:

- [x] Fedora 44 Everything x86_64 Kickstart with Workstation/GNOME package
  selection; leave disk selection, encryption, keyboard/timezone and credentials
  interactive. No automatic partition wiping or embedded passwords.
- [x] Stage a GNOME first-login setup offer rather than run installation in
  Anaconda. Preserve existing bootstrap guards and pin both bootstrap and checkout
  to one committed revision. Explicitly warn about existing TTY autologin behavior.
- [x] Require a terminal and explicit confirmation; record private logs, result
  and an attempt marker. Block concurrent launches and automatic retries.
- [x] Add an ISO builder with existing-output protection, input SHA256 check,
  payload manifest, Fedora-version syntax validation and full EFI mkksiso path.
  Preparation mode needs no root privileges. No disk-writing code is included.
- [x] Add 21 isolated tests (57 total) for launcher and build safety.
- [x] Verify Fedora package/environment availability and Kickstart syntax.
- [ ] Build a real ISO from a signature-verified Fedora source image.
- [ ] Pass the UEFI VM, account-creation, encryption, first-login and failure gates.
- [ ] Identify/confirm USB device, flash and verify it, then test spare hardware.

See [the USB guide](kickstart-usb.md) for commands and recovery. `lorax` and system
`pykickstart` are not installed on the build host; isolated Kickstart validation
used a temporary pykickstart environment. No image has been built or flashed,
and no live desktop settings were changed. This does not close Phase 0 decisions
or certify the existing package/session installer.

Validation: all 57 unittests pass; Bash syntax, ShellCheck, Ruff formatting/lint,
and Fedora 44 Kickstart syntax pass. Tests do not execute a real installer.

## Objectives and constraints

- Reproduce the intended opinionated desktop from a declared fresh Fedora image.
- Preserve working installations and user-owned configuration.
- Make failure, retry, and update behavior understandable and testable.
- Keep mandatory desktop setup separate from personal data and hardware setup.
- Keep the implementation small: explicit shell stages and a simple dependency
  inventory are sufficient; no new provisioning framework is required.
- Do not expand upstream features or rename paths while fixing unrelated bugs.
- Never test installers or migrations against the daily-use workstation.

## Phase 0: Agree on the supported installation

Dependencies: none. Addresses A04, A05, A07, A08, A14, A15.

- [ ] Confirm the initial target: recommended starting point is Fedora 44 x86_64
  on a conventional mutable installation, not an Atomic variant.
- [ ] Select the supported base image: Workstation with GDM, or a minimal image
  with TTY startup. Supporting both requires separate integration tests.
- [ ] Choose the login/security policy, including whether autologin is wanted and
  whether encryption or immediate lock is a prerequisite.
- [ ] Confirm application choices: Ghostty versus Alacritty, Chrome versus
  Chromium, clipboard tools, Bluetooth UI, and NetworkManager UI.
- [ ] Classify every enabled feature as mandatory, optional-installable, or
  personal/manual; explicitly decide voice, translation, Docker, printing,
  preview picker, Zoom, private prompt collections, and hardware helpers.
- [ ] Choose a tested Hyprland/plugin version combination and update policy.
- [ ] Establish configuration ownership: managed defaults, user overrides,
  generated state, and secrets. Decide how existing files are adopted.

Deliverable: a concise support and feature/dependency table, including providers
already guaranteed by the chosen Fedora image. These are decisions, not grounds
for silently removing the project's opinionated defaults.

Exit gate: supported installation and expected first-login behavior are explicit.

## Phase 1: Repair bootstrap and early failures

Dependencies: Phase 0. Addresses A01–A04.

Primary files: `boot.sh`, `install.sh`, `install/vscode.sh`, `install/docker.sh`,
and the installation section of `README.md`.

- [ ] Repair the published endpoint and document a direct fallback.
- [ ] Check downloads for both transport failure and expected content before
  executing them; reject an HTML error page even if its status is successful.
- [x] Add fail-fast bootstrap handling and reject invalid refs before invocation.
- [x] Stop deleting existing checkouts; clone into temporary storage and validate
  before activation. Refuse or explicitly handle dirty existing checkouts.
- [ ] Add preflight checks for OS/release, architecture, Bash, user identity,
  privilege availability, and required installation session.
- [ ] Make system-upgrade behavior explicit and report failures from the start.
- [x] Check RPM Fusion Free and Nonfree independently.
- [ ] Provision the required DNF5 plugins and use the supported repository syntax.
- [x] Remove or correctly handle `dnf check-update` exit code 100.
- [x] Install `plocate` if locate functionality is wanted; otherwise remove the
  unconditional `updatedb` step.
- [ ] Create all required installation directories explicitly.
- [x] Distinguish declining reboot from an installation failure.

Tests to add:

- [x] Existing paths are refused before clone/ref/download operations; failed
  new clones/refs leave no published checkout or leftover staging directory.
- [ ] HTML response, HTTP error, and interrupted download are rejected.
- [ ] Unsupported environment exits before any mutation command is invoked.
- [x] RPM Fusion Free-only starting state still provisions Nonfree when needed.
- [x] VS Code skips the unnecessary update check and still propagates actual
  package-install failures.
- [ ] Minimal supported image has every finalization command available.

Exit gate: bootstrap is safe to retry and all known early/late command-presence
failure paths have regression coverage.

## Phase 2: Make stages explicit and configuration writes recoverable

Dependencies: Phase 1. Addresses A16, A17, A19.

Primary files: `install.sh`, `install/4-config.sh`, `install/backgrounds.sh`,
`install/theme.sh`, `install/nvim.sh`, and stages sharing shell state.

- [ ] Replace implicit glob ordering with an explicit ordered stage list.
- [ ] Identify stage inputs, outputs, prerequisites, and mandatory/optional status.
- [ ] Remove shared working-directory and shell-option assumptions.
- [ ] Give background/theme stages explicit access to their helper and directory;
  do not mechanically replace `source` with `bash` while this dependency remains.
- [ ] Execute isolated stages only after required inputs are passed explicitly.
- [ ] Separate package/file provisioning from graphical-session activation.
- [ ] Report stage name and failure cause; stop mandatory failures and summarize
  optional failures without falsely declaring those features installed.
- [ ] Back up or merge shell, Docker, editor, and portal files according to the
  ownership policy. Handle existing symlinks deliberately.
- [ ] Separate Neovim package detection from LazyVim configuration installation.
- [ ] Use temporary download/build directories, validate artifacts, and pin
  compatibility-sensitive source revisions/toolchains.
- [ ] Make repeat execution converge without repeated config appends, broken
  links, lost preferences, or unnecessary destructive rebuilds.

Tests to add:

- [ ] Stage order and prerequisite availability are deterministic.
- [ ] A stage cannot accidentally change a later stage's shell options or cwd.
- [ ] Background/theme setup works without inherited functions or variables.
- [ ] Two runs produce equivalent managed state.
- [ ] Existing regular files and symlinks follow the same documented backup policy.
- [ ] Preinstalled Neovim does not prevent required configuration provisioning.
- [ ] Interrupted execution can resume without deleting the previous working state.

Exit gate: orchestration and configuration ownership are reliable enough to
support the feature fixes without additional hidden dependencies.

## Phase 3: Close desktop and helper dependency gaps

Dependencies: Phases 0 and 2. Addresses A05, A06, A14, A15, A19.

Primary files: package stages, `config/hypr/hyprland.lua`,
`default/hypr/autostart.lua`, `default/hypr/bindings.lua`, `config/waybar/config`,
`applications/`, voice/translation installers, and affected `bin/` helpers.

- [ ] Provision the chosen terminal/browser and align all bindings and launchers.
- [ ] Install the chosen clipboard tools and a working authentication agent.
- [ ] Align network/Bluetooth UI with actual Fedora services; do not install iwd
  solely to satisfy a stale `iwctl` click action.
- [ ] Account for every active helper dependency, including `jq`, notifications,
  audio utilities, and optional `bt` dependencies.
- [ ] Point translation, Spotlight, and dictation bindings at managed executable
  paths or explicitly create their advertised links.
- [ ] Finish dictation installation, verify executable/model readiness, and use
  private per-user recording state.
- [ ] Provision an isolated translation environment and selected offline models.
  Keep any optional DeepL credential outside version control.
- [ ] Gate manual applications, Waybar modules, and launchers until available.
- [ ] Preserve and validate a working `tuned-ppd` or compatible PowerProfiles API
  provider; discover supported profiles instead of assuming all exist.
- [ ] Move private checkout paths and device-specific settings into explicit
  overrides; provide a sane monitor fallback.
- [ ] Make wallpaper/theme cycling handle missing assets, empty directories, and
  paths containing spaces without disrupting the current wallpaper.
- [ ] Define managed application assets; preserve unrelated user launchers and
  prune only previously managed retired files.

Tests to add:

- [ ] All mandatory autostart commands and desktop launcher executables resolve.
- [ ] Every enabled binding has a provisioned target or an explicit setup gate.
- [ ] Dictation and translation work without undocumented copying or global pip.
- [ ] An alternate username and no private repositories do not break startup.
- [ ] Power setup works with tuned-ppd, no battery, and fewer available profiles.
- [ ] Empty/broken theme state fails clearly while preserving the current display.
- [ ] Application sync preserves user-owned entries and reports real failures.

Exit gate: package and file provisioning matches every enabled desktop feature.

## Phase 4: Complete session and Lua integration

Dependencies: Phases 2–3. Addresses A07–A11.

Primary files: `install/hyprlandia.sh`, shell defaults, Hyprland Lua files,
`config/environment.d/`, and relevant feature installers.

- [ ] Implement the selected GDM or TTY login path and preserve required shell
  initialization before compositor startup.
- [ ] Establish PATH without accidental relative-directory command shadowing.
- [ ] Implement and document the chosen autologin/lock policy.
- [ ] Correct keyring environment propagation and graphical environment import
  into D-Bus activation and systemd user services.
- [ ] Verify input-method variables for GTK, Qt, SDL, and XWayland clients.
- [ ] Convert NVIDIA/picker integration from old Hyprlang patches to current Lua.
- [ ] Sequence Hyprtasking load completion before applying plugin configuration.
- [ ] Guard optional plugin bindings and surface useful load/ABI failures.
- [ ] Add a regression test for the converter's plugin-dispatcher output if the
  converter remains a supported maintenance tool.

Tests to add/run:

- [ ] First graphical login has no configuration errors and working core bindings.
- [ ] Compositor-launched applications receive the intended PATH/environment.
- [ ] Reminder timer notifications and their Wofi actions work after first login.
- [ ] Missing plugin does not break ordinary arrow/Escape behavior.
- [ ] Lock, unlock, suspend, wake, and compositor failure match the security policy.
- [ ] No active installer integration depends on obsolete `hyprland.conf` patches.

Exit gate: a clean installation reaches a usable session without manual repairs.

## Phase 5: Validate hardware and screen sharing

Dependencies: Phase 4. Addresses A11–A15.

Primary files: `install/nvidia.sh`, `install/zzz_hyprtasking.sh`,
`install/zzz_window_picker.sh`, `applications/Zoom.desktop`, hardware helpers.

- [ ] Validate NVIDIA GPU/driver support and exact package providers.
- [ ] Implement Secure Boot handling or explicitly stop with documented enrollment
  steps; never claim readiness when the kernel would reject the module.
- [ ] Verify akmod completion and target kernel before initramfs rebuild/reboot.
- [ ] Test plugin installation before the first session and after a compositor
  upgrade, including stale headers and failed build/load behavior.
- [ ] Establish standard Hyprland/GTK portal operation before adding workarounds.
- [ ] Remove unconditional RPM conflict overrides unless the issue is reproduced
  and a narrowly scoped, documented workaround is still necessary.
- [ ] Keep the preview picker independently installable from Zoom repair logic.
- [ ] Align Zoom launcher/wrapper behavior and defer session restarts until valid.
- [ ] Make Apple-display, AirPods, and fingerprint setup opt-in and Fedora-aware.

Acceptance checks:

- [ ] Intel/AMD installation does not depend on NVIDIA setup.
- [ ] NVIDIA module readiness is checked for Secure Boot on/off scenarios.
- [ ] Screen sharing works for monitor/window capture, stop/start, and resize.
- [ ] File chooser and another installed desktop session are not broken by portal
  configuration intended only for Hyprland.
- [ ] Optional-feature failure leaves a usable core desktop.

Exit gate: support claims match VM and real-hardware evidence.

## Phase 6: Repair updates and fresh/upgrade convergence

Dependencies: configuration ownership from Phase 2 and final state from Phases 3–5.
Addresses A17–A20.

Primary files: `bin/omarchy-update`, `migrations/`, config/application helpers,
tests, `README.md`, and historical conversion documentation.

- [ ] Require a successful, policy-compliant Git update before migrations.
- [ ] Execute migrations in isolation and record successful IDs in user state.
- [ ] Stop on failure; retry the failed migration without forgetting or replaying
  successfully completed predecessors.
- [ ] Define a fresh-install baseline and how existing installations adopt the
  journal without blindly rerunning destructive historical migrations.
- [ ] Replace destructive Docker configuration writes with preservation/merge.
- [ ] Preserve managed symlinks during configuration migrations.
- [ ] Install/verify replacement applications before removing old functionality.
- [ ] Reconcile managed application assets and configuration during updates.
- [ ] Document retries, migration state, ownership, optional setup, and recovery.
- [ ] Correct stale conversion claims and keep upstream feature adoption separate.

Tests to add:

- [ ] Failed Git update starts no migrations.
- [ ] Failed migration is retried on the next run, despite an advanced Git HEAD.
- [ ] Migration ordering and initial journal adoption are deterministic.
- [ ] Fresh and upgraded fixtures converge on equivalent managed state.
- [ ] Docker settings, user overrides, and managed symlinks survive update.

Exit gate: the repaired installer is not a one-use solution that immediately
drifts again on the first update.

## Phase 7: Adopt a new identity after name selection

Dependencies: user selects a name from [naming-proposals.md](naming-proposals.md)
or another candidate; migration safety from Phase 6 precedes path changes.

- [ ] Check project/package-name collisions, repository availability, trademarks,
  and relevant languages. Recheck domains immediately before registration.
- [ ] Choose display name, repository slug, executable prefix, config/state paths,
  environment-variable prefix, and bootstrap endpoint.
- [ ] Inventory all old-name references: scripts, imports, symlinks, themes,
  launchers, documentation, systemd units, migration state, and private overrides.
- [ ] Rename public-facing documentation separately from functional path changes.
- [ ] Migrate managed install/config/state paths without stranding existing links.
- [ ] Provide temporary compatibility commands/paths where existing bindings and
  user workflows need them; document a removal policy.
- [ ] Preserve MIT license and upstream copyright/attribution notices. Describe
  the project as inspired by Omarchy without suggesting official affiliation.
- [ ] Test both a fresh installation under the new name and migration from the
  old layout, including failed/interrupted migration recovery.

Exit gate: branding is coherent and existing installations continue to function.
Do not perform a blind global search-and-replace.

## Validation strategy and release gate

Use existing Python unittest infrastructure for regression tests where practical.
Mock external commands and use temporary HOME/XDG directories for shell lifecycle
tests. Ensure tests cannot invoke real sudo, package mutations, service changes,
or reboot on the host. Keep all existing tests.

| Environment/scenario | Required evidence |
| --- | --- |
| Fresh Fedora 44 x86_64, selected image | Package resolution, completed install, first reboot/login |
| Additional base image, if supported | Separate login/session integration result |
| Different username and display layout | No personal path or connector prerequisites |
| Existing shell/editor/Docker config | Preserved state and convergent rerun |
| Interrupted network/package/build stage | Explicit failure and safe retry |
| Missing optional app/plugin | Usable desktop and understandable setup/error message |
| Tuned-ppd and reduced hardware capabilities | Working profile selection and lock restoration |
| NVIDIA, Secure Boot on/off | Driver/module/initramfs and reboot verification |
| Existing installation update | Migration journal and managed-state convergence |
| Selected new identity | Fresh install and backwards-compatible migration |

Containers can check dependency resolution and non-graphical stages. A VM is
required for login, systemd, portals, and reboot; real hardware is needed for
GPU, monitor, and suspend claims.

- [ ] Shell syntax and agreed lint checks pass; distinguish intentional source
  analysis limitations from actionable warnings.
- [ ] Documentation formatting and local links validate.
- [ ] Existing and new regression tests pass without skipped failures.
- [ ] No secrets or private runtime state are committed.
- [ ] Fresh install, retry, and upgrade integration evidence is recorded with
  Fedora image, package versions, repository revision, and feature selection.
- [ ] Remaining unsupported combinations are documented explicitly.

Only then describe the installer as working for the declared support matrix.
