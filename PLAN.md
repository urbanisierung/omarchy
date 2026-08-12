# Omarchy Fedora Fork — Upstream Feature Adoption Plan

> Comparison of [urbanisierung/omarchy](https://github.com/urbanisierung/omarchy) (Fedora fork) against [basecamp/omarchy](https://github.com/basecamp/omarchy) **v3.6.0** (upstream, Arch-based).
>
> Last reviewed: 2026-04-24

---

## Current State

| Aspect | Upstream (Arch) | Fork (Fedora) |
|--------|----------------|---------------|
| Version | v3.6.0 | — |
| bin/ scripts | ~150+ `omarchy-*` commands | 13 custom scripts |
| install/ | Restructured: subdirs + `.packages` manifests | 25 numbered/named scripts |
| themes/ | 20 themes (template-based via `colors.toml`) | 6 themes (static configs) |
| config/ | 25+ app directories | 11 directories |
| migrations/ | ~160 migration scripts | 8 migration scripts |
| App launcher | Walker | Wofi |
| Terminal multiplexer | Tmux (integrated) | — |
| AI tooling | Claude Code, OpenCode, Voxtype, Codex, Gemini | — |
| Menu system | Full `omarchy-menu` with nested submenus | — |

---

## Priority 1 — High-Impact Core Features

### 1.1 Tmux Integration

**Upstream since:** v3.4.0
**Source:** [`config/tmux/`](https://github.com/basecamp/omarchy/tree/dev/config/tmux), [`default/bash/`](https://github.com/basecamp/omarchy/tree/dev/default/bash)
**Key commits:** "Add Tmux with tailored config" (v3.4.0 release)

**What it adds:**
- Tailored tmux config with `t` alias to start a session
- AI-focused layouts:
  - `tdl` — Tmux Dev Layout (editor + terminal split)
  - `tdlm` — Tmux Dev Layout Multiplier (multiple panes)
  - `tsl` — Tmux Swarm Layout (multi-agent)
- Keybindings: `Alt+left/right` (windows), `Alt+up/down` (sessions), `Alt+Shift+Arrow` (swap windows)
- Tmux zoom indicator in status bar, `COPY` mode highlight
- `Super + Alt + Return` starts terminal in Tmux mode
- `omarchy-refresh-tmux`, `omarchy-restart-tmux` scripts

**Fedora notes:**
- `tmux` is available in Fedora repos (`dnf install tmux`) — no changes needed
- Bash aliases and config files are distro-agnostic, copy directly
- Migration [`1770638893.sh`](https://github.com/basecamp/omarchy/blob/dev/migrations/1770638893.sh) adds tmux config to existing installs

**Effort:** Medium
**Portability:** Excellent

---

### 1.2 Dynamic Theme System via `colors.toml`

**Upstream since:** v3.3.0
**Source:** [`themes/`](https://github.com/basecamp/omarchy/tree/dev/themes), [`bin/omarchy-theme-set-templates`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-theme-set-templates)
**Key commits:** "Add new colors.toml and template-based configs" (v3.3.0 release)

**What it adds:**
- Themes defined by a single `colors.toml` with ~24 color variables
- Template-based generation for all app configs (Alacritty, Ghostty, Kitty, btop, Chromium/Brave, mako, hyprlock, hyprland, sway, vscode, walker, waybar)
- 14 new themes beyond the 6 in the fork:
  - **Dark:** vantablack (OLED), hackerman, lumon, miasma, ethereal, matte-black, osaka-jade, ristretto, rose-pine
  - **Light:** catppuccin-latte, flexoki-light, white
  - **Special:** retro-82
- `omarchy-theme-install`, `omarchy-theme-remove`, `omarchy-theme-list`, `omarchy-theme-current`, `omarchy-theme-refresh`
- `omarchy-theme-set-browser` applies theme to Chromium/Brave via browser policies
- `omarchy-theme-set-keyboard` syncs keyboard backlight colors (Asus ROG, Framework 16)
- `omarchy-theme-bg-install`, `omarchy-theme-bg-next`, `omarchy-theme-bg-set` — background management
- `omarchy-theme-set-obsidian`, `omarchy-theme-set-vscode` — editor theme sync
- User themes: same name as built-in themes, overwrite individual files

**Fedora notes:**
- Template system is pure bash, fully portable
- Kvantum theming: Fedora uses `kvantum` (not `kvantum-qt5`)
- Browser policy paths are the same across distros
- Vantablack theme is optimized for OLED — worth prioritizing if you have an OLED display

**Effort:** High — requires reworking the existing static theme system
**Portability:** Excellent

---

### 1.3 Voice Dictation via Voxtype

**Upstream since:** v3.3.0
**Source:** [`bin/omarchy-voxtype-*`](https://github.com/basecamp/omarchy/tree/dev/bin), [`default/voxtype/`](https://github.com/basecamp/omarchy/tree/dev/default/voxtype), [`config/omarchy/`](https://github.com/basecamp/omarchy/tree/dev/config/omarchy)

**What it adds:**
- Local AI dictation using Whisper models, activated with `Super + Ctrl + X`
- Scripts: `omarchy-voxtype-install`, `omarchy-voxtype-config`, `omarchy-voxtype-model`, `omarchy-voxtype-status`, `omarchy-voxtype-remove`
- Default 150MB base English model, switchable via right-click on Waybar mic icon
- GPU acceleration when Vulkan is available (`omarchy-hw-vulkan` check)
- `pause_media` enabled by default so MPRIS players pause while dictating
- Clean up orphaned status processes on exit (v3.6.0 fix)

**Fedora notes:**
- Voxtype is an AUR package upstream — will need to be installed from source or a Copr repo on Fedora
- Check: `https://github.com/voxtype/voxtype` for build instructions
- Whisper model downloads are distro-agnostic
- Vulkan drivers: `dnf install vulkan-loader mesa-vulkan-drivers`

**Effort:** Medium
**Portability:** Good (main concern is Voxtype packaging)

---

### 1.4 Comprehensive Omarchy Menu System

**Upstream since:** v3.3.0+
**Source:** [`bin/omarchy-menu`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-menu), [`bin/omarchy-menu-keybindings`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-menu-keybindings)

**What it adds:**
- Central `omarchy-menu` triggered by `Super + Alt + Space` with nested submenus:
  - **Install:** AI, Development, Gaming, Services, Docker DBs, Terminal, Browser, Editors, Web Apps, TUIs
  - **Remove:** Development, Preinstalls, Web Apps, TUIs
  - **Setup:** Audio, DNS, Fingerprint, FIDO2, Security, System Sleep, Key Remapping
  - **Update:** Omarchy, Firmware, System Packages, AUR Packages, Refresh (per-app sub-items)
  - **Toggle:** Idle Lock, Nightlight, Notifications, Screensaver, Suspend, Touchpad, Waybar, Hybrid GPU, Window Gaps, Display Scaling
  - **System:** Lock, Logout, Reboot, Shutdown
- `omarchy-menu-keybindings` — visual keybinding reference
- Extensible via `~/.config/omarchy/extensions/menu.sh`

**Fedora notes:**
- Menu uses `gum` for TUI — already adapted in your fork (installed from GitHub releases)
- Sub-commands that call `omarchy-pkg-add`/`omarchy-pkg-install` use `pacman`/`yay` — need `dnf` wrappers
- Key dependency: `omarchy-pkg-add`, `omarchy-pkg-drop`, `omarchy-pkg-install`, `omarchy-pkg-missing`, `omarchy-pkg-present`, `omarchy-pkg-remove`, `omarchy-pkg-aur-accessible`, `omarchy-pkg-aur-add`, `omarchy-pkg-aur-install`
- AUR-related scripts (`omarchy-pkg-aur-*`) have no Fedora equivalent — replace with Copr or skip
- `omarchy-cmd-present`/`omarchy-cmd-missing` are distro-agnostic (use `command -v`)

**Effort:** High — this is the entire UX backbone; many sub-scripts need Fedora adaptation
**Portability:** Good (core menu is bash, but each action may call Arch-specific packaging)

---

### 1.5 AI Agent Integration

**Upstream since:** v3.3.0–v3.5.0
**Source:** [`default/bash/`](https://github.com/basecamp/omarchy/tree/dev/default/bash), [`bin/omarchy-install-*`](https://github.com/basecamp/omarchy/tree/dev/bin), [`bin/omarchy-npx-install`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-npx-install)

**What it adds:**
- `c` alias → OpenCode (multi-provider AI agent terminal)
- `cx` alias → Claude Code in accept-all mode
- `i` alias → IDE with opencode and claude
- Lazy-install npx stubs for: Opencode, Gemini CLI, Codex, Copilot CLI, Playwright
- `omarchy-sudo-passwordless-toggle` — temporarily grant sudo to AI agents for debugging (with time limit, extendable via explicit minutes)
- `omarchy-restart-opencode` — restart OpenCode gracefully
- Default OpenCode config in [`config/opencode/`](https://github.com/basecamp/omarchy/tree/dev/config/opencode)

**Fedora notes:**
- All aliases are pure bash — copy directly from `default/bash/`
- npx stubs require Node.js via mise — check your mise setup
- `omarchy-sudo-passwordless-toggle` is distro-agnostic (modifies `/etc/sudoers.d/`)
- OpenCode: install via `go install` or from AUR equivalent — check if available in Copr

**Effort:** Low–Medium
**Portability:** Excellent

---

## Priority 2 — Important Quality-of-Life Improvements

### 2.1 Revamped Screenshot & Screen Recording

**Upstream since:** v3.4.0+
**Source:** [`bin/omarchy-cmd-screenshot`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-cmd-screenshot), [`bin/omarchy-cmd-screenrecord`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-cmd-screenrecord), [`bin/omarchy-cmd-share`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-cmd-share)

**What it adds:**
- Single `PrintScr` flow: saves to file + clipboard simultaneously, notification offers edit via Satty
- No more `Shift + PrintScr` needed for clipboard-only
- `Super + Alt + ,` activates edit invitation from notification
- Screen recording: scrambled-frame detection + re-encoding guard, audio normalization to -14 LUFS, constant frame-rate for easier post-editing, webcam overlay with vertical framing
- `omarchy-cmd-share` for sharing recordings

**Fedora notes:**
- Dependencies: `wl-screenrec` or `wf-recorder`, `satty`, `slurp`, `grim`, `wl-clipboard`
- `wl-screenrec`: may need to build from source on Fedora (check Copr)
- `satty`: check Copr or build from source (`cargo install satty`)
- `grim`, `slurp`, `wl-clipboard`: available in Fedora repos
- Audio normalization uses `ffmpeg` — available everywhere

**Effort:** Low
**Portability:** Excellent (scripts are distro-agnostic once tools are installed)

---

### 2.2 Battery & Power Management

**Upstream since:** v3.4.0+
**Source:** [`bin/omarchy-battery-*`](https://github.com/basecamp/omarchy/tree/dev/bin), [`bin/omarchy-powerprofiles-*`](https://github.com/basecamp/omarchy/tree/dev/bin), [`bin/omarchy-ac-present`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-ac-present)

**What it adds:**
- `omarchy-battery-capacity` — current battery percentage
- `omarchy-battery-remaining` — percentage retrieval
- `omarchy-battery-remaining-time` — time to empty/full
- `omarchy-battery-status` — charging/discharging/full
- `omarchy-battery-monitor` — low battery monitoring with opt-in sound hook
- `omarchy-battery-present` — detect if battery exists
- `omarchy-ac-present` — detect AC power
- `omarchy-powerprofiles-init` — set performance profile on boot when on AC
- `omarchy-powerprofiles-list` — list available power profiles
- `omarchy-powerprofiles-set` — set power profile
- Automatic profile switching: performance on AC, balanced on battery
- Detailed battery notification on Waybar right-click (`Super + Ctrl + Alt + B`)

**Fedora notes:**
- `power-profiles-daemon` is the default on Fedora — fully compatible
- `powerprofilesctl` is the same binary name on both Arch and Fedora
- Battery sysfs paths (`/sys/class/power_supply/`) are distro-agnostic
- udev rules in [`default/udev/`](https://github.com/basecamp/omarchy/tree/dev/default/udev) are portable
- No package changes needed

**Effort:** Low
**Portability:** Excellent

---

### 2.3 Hibernation & Suspend Support

**Upstream since:** v3.3.0+
**Source:** [`bin/omarchy-hibernation-*`](https://github.com/basecamp/omarchy/tree/dev/bin)

**What it adds:**
- `omarchy-hibernation-setup` — creates swap subvolume sized to RAM, configures resume
- `omarchy-hibernation-available` — checks if hibernation is possible
- `omarchy-hibernation-remove` — removes swap subvolume and config
- Suspend-to-hibernate after 30 minutes (when supported)
- Toggle via Setup > System Sleep menu
- Upstream uses Limine bootloader config for resume — **your fork likely uses GRUB**

**Fedora notes:**
- Fedora uses GRUB2 by default, not Limine — resume kernel cmdline must go in `/etc/default/grub` + `grub2-mkconfig`
- Fedora uses `dracut` for initramfs (not `mkinitcpio`) — resume hook configuration differs
- Swap subvolume creation (btrfs) is the same
- `systemd-hibernate` and `suspend-then-hibernate` work identically
- **Adaptation required:** replace Limine/mkinitcpio references with GRUB/dracut equivalents

**Effort:** Medium
**Portability:** Needs Fedora-specific bootloader/initramfs adaptation

---

### 2.4 Hardware Detection System

**Upstream since:** v3.5.0+
**Source:** [`bin/omarchy-hw-*`](https://github.com/basecamp/omarchy/tree/dev/bin)

**What it adds:**
- `omarchy-hw-match` — generic hardware matcher (DMI/product name check)
- `omarchy-hw-external-monitors` — detect connected external displays
- `omarchy-hw-recover-internal-monitor` — re-enable laptop display when external removed
- `omarchy-hw-hybrid-gpu` — detect hybrid GPU setups
- `omarchy-hw-intel` / `omarchy-hw-intel-ptl` — Intel-specific optimizations (thermald, LPMD)
- `omarchy-hw-vulkan` — Vulkan availability check
- `omarchy-hw-touchpad` / `omarchy-haptic-touchpad` — touchpad detection and haptic support
- `omarchy-hw-dell-xps-oled`, `omarchy-hw-framework16`, `omarchy-hw-surface`, `omarchy-hw-asus-rog` — vendor-specific hardware handlers
- Lid close/open → disable/enable laptop display with external monitors

**Fedora notes:**
- Hardware detection uses `/sys/class/dmi/`, `lspci`, `hyprctl` — all distro-agnostic
- Intel thermal management: `thermald` and `intel-lpmd` may need Copr or manual install on Fedora
- GPU detection and switching is kernel-level, works the same
- Framework, Surface, Dell, Asus hardware handling is distro-agnostic

**Effort:** Medium
**Portability:** Mostly distro-agnostic

---

### 2.5 Walker App Launcher (Replaces Wofi)

**Upstream since:** ~v3.2+
**Source:** [`config/walker/`](https://github.com/basecamp/omarchy/tree/dev/config/walker), [`bin/omarchy-launch-walker`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-launch-walker), [`bin/omarchy-refresh-walker`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-refresh-walker), [`bin/omarchy-restart-walker`](https://github.com/basecamp/omarchy/blob/dev/bin/omarchy-restart-walker)

**What it adds:**
- Walker v2 as app launcher with crash recovery
- Theme integration via template system
- Emergency mode entry
- Better search providers (applications, commands, files)
- `omarchy-launch-walker` with GSK_RENDERER fix for some systems

**Fedora notes:**
- Walker is a Go binary — install from GitHub releases or build from source
- No Fedora repo package, but the AppImage or binary release works
- Config files are distro-agnostic
- Would replace current `config/wofi/` setup

**Effort:** Medium
**Portability:** Good (binary release works, just need to set up install path)

---

## Priority 3 — Nice-to-Have Additions

### 3.1 Hyprland Window Management Enhancements

**Source:** [`bin/omarchy-hyprland-*`](https://github.com/basecamp/omarchy/tree/dev/bin)

**What it adds:**
- `omarchy-hyprland-monitor-scaling-cycle` — cycle through 1x, 1.25x, 1.6x, 2x, 3x (forwards and backwards)
- `omarchy-hyprland-workspace-layout-toggle` — switch between scrolling and dwindle layouts (`Super + L`)
- `omarchy-hyprland-toggle` with persistent toggle state surviving `hyprctl reload` and restarts
- `omarchy-hyprland-window-gaps-toggle` — toggle window gaps
- `omarchy-hyprland-window-single-square-aspect-toggle` — 1:1 aspect ratio for single windows
- `omarchy-hyprland-active-window-transparency-toggle`
- `omarchy-hyprland-window-pop` — pop window to floating
- `omarchy-toggle-*` scripts: idle, nightlight, notifications, screensaver, suspend, touchpad, waybar

**Fedora notes:** All Hyprland-specific, fully distro-agnostic. Copy scripts directly.

**Effort:** Low
**Portability:** Excellent

---

### 3.2 New Config Directories

**Source:** [`config/`](https://github.com/basecamp/omarchy/tree/dev/config)

| Directory | Purpose | In Fork? |
|-----------|---------|----------|
| `config/git/` | Better git defaults | No |
| `config/fontconfig/` | Fix emoji rendering in Alacritty | No |
| `config/opencode/` | Disable auto-update | No |
| `config/swayosd/` | OSD styling | No |
| `config/autostart/` | Fcitx5 management | No |
| `config/omarchy/` | Central Omarchy config/state | No |
| `config/starship.toml` | Prompt configuration | No |
| `config/tmux/` | Tmux configuration | No |
| `config/walker/` | Walker launcher config | No |
| `config/elephant/` | Elephant menu / emoji picker | No |
| `config/chromium/Default/` | Chromium dark mode | No |
| `config/kitty/` | Kitty terminal config | No |
| `config/ghostty/` | Ghostty terminal config | No |
| `config/imv/` | Image viewer keybindings | No |
| `config/wiremix/` | Audio mixer config | No |

**Fedora notes:** All config files are distro-agnostic. Copy directly.

**Effort:** Low
**Portability:** Excellent

---

### 3.3 Additional Installers

**Source:** [`bin/omarchy-install-*`](https://github.com/basecamp/omarchy/tree/dev/bin)

| Installer | Upstream Package | Fedora Equivalent |
|-----------|-----------------|-------------------|
| `omarchy-install-tailscale` | `tailscale` | `dnf install tailscale` or official repo |
| `omarchy-install-nordvpn` | AUR `nordvpn-bin` | Official NordVPN Linux repo |
| `omarchy-install-steam` | `steam` | `dnf install steam` (RPM Fusion) |
| `omarchy-install-geforce-now` | Chromium-based | Same approach (browser) |
| `omarchy-install-once` | Docker-based | Docker is same everywhere |
| `omarchy-install-xbox-controllers` | `xone-dkms` | `dnf install xone` or DKMS from source |
| `omarchy-install-dropbox` | AUR `dropbox` | `dnf install dropbox` or Flatpak |
| `omarchy-install-dev-env` | mise-based | mise works same on Fedora |
| `omarchy-install-chromium-google-account` | Custom extension | Distro-agnostic |
| `omarchy-install-vscode` | AUR `visual-studio-code-bin` | Official MS repo |
| `omarchy-install-docker-dbs` | Docker images | Distro-agnostic |

**Effort:** Medium
**Portability:** Each needs Fedora package mapping

---

### 3.4 Restructured Install System

**Upstream since:** ~v3.4.0+
**Source:** [`install/`](https://github.com/basecamp/omarchy/tree/dev/install)

Upstream restructured from flat numbered scripts to:
```
install/
  config/           # Config file installation and linking
  first-run/        # First-boot setup (monitor recovery, etc.)
  helpers/          # Shared helper functions
  login/            # Login manager (SDDM) + snapper setup
  packaging/        # Package installation logic + lazy npx stubs
  post-install/     # Post-install tasks (hibernation, etc.)
  preflight/        # Pre-install checks
  omarchy-base.packages    # Base package manifest
  omarchy-other.packages   # Optional package manifest
```

**Fedora notes:**
- Package manifests would need complete rewrite with Fedora package names
- `packaging/` heavily uses `pacman`/`yay` — needs `dnf` adaptation
- `login/` uses SDDM config — same on Fedora if using SDDM
- `helpers/` likely distro-agnostic

**Effort:** High
**Portability:** Structure is good, content needs Fedora rewrite

---

### 3.5 Bash Helpers & Aliases

**Source:** [`default/bash/`](https://github.com/basecamp/omarchy/tree/dev/default/bash), [`default/bashrc`](https://github.com/basecamp/omarchy/blob/dev/default/bashrc)

**What it adds:**
- `ga <branch>` / `gd <branch>` — git worktree create/remove helpers
- `sff` — fuzzy find + send file over scp
- `eff` — fuzzy find + open result in `$EDITOR`
- `fip`/`dip`/`lip` — SSH port forwarding helpers for web dev
- Tab-cycle completion for bash file/directory expansion
- Lazy `try` command initialization (faster bash startup)
- `i` alias for IDE mode with AI agents

**Fedora notes:** Pure bash — copy directly.

**Effort:** Low
**Portability:** Excellent

---

### 3.6 Waybar Enhancements

**Source:** [`config/waybar/`](https://github.com/basecamp/omarchy/tree/dev/config/waybar)

**What it adds:**
- Battery widget with right-click for detailed notification
- Omarchy icon glyph (custom `omarchy.ttf` font)
- Recording indicator during screen capture
- Bluetooth off icon when adapter is disabled
- Idle-lock and notification-silencing indicator icons
- Headset icon for audio
- Voxtype status indicator (mic icon when dictating)

**Fedora notes:** Waybar config is distro-agnostic. Custom font needs to be installed.

**Effort:** Low
**Portability:** Excellent

---

### 3.7 Default Directory Additions

**Source:** [`default/`](https://github.com/basecamp/omarchy/tree/dev/default)

| Directory | Purpose | Fedora Notes |
|-----------|---------|-------------|
| `default/elephant/` | Elephant menu (system action picker) | Distro-agnostic |
| `default/ghostty/` | Ghostty terminal defaults | Distro-agnostic |
| `default/chromium/extensions/copy-url/` | Copy URL extension | Distro-agnostic |
| `default/limine/` | Limine bootloader configs | **N/A — Fedora uses GRUB** |
| `default/mako/` | Notification daemon defaults | Distro-agnostic |
| `default/nautilus-python/extensions/` | "Open in Terminal" + LocalSend | Distro-agnostic |
| `default/omarchy-skill/` | OpenCode/Claude skill file | Distro-agnostic |
| `default/pacman/` | Pacman config | **N/A — Fedora uses dnf** |
| `default/plymouth/` | Boot splash | Fedora has Plymouth built-in |
| `default/sddm/omarchy/` | Styled SDDM login | Same if using SDDM |
| `default/snapper/` | Btrfs snapshot configs | Same if using btrfs |
| `default/systemd/` | Systemd unit overrides | Distro-agnostic |
| `default/udev/` | Hardware event rules (Framework, power) | Distro-agnostic |
| `default/voxtype/` | Voxtype default config | Distro-agnostic |
| `default/walker/` | Walker launcher defaults | Distro-agnostic |
| `default/waybar/indicators/` | Notification silencing indicator | Distro-agnostic |
| `default/wireplumber/` | Audio soft mixing opt-in | Distro-agnostic |

---

## Migration Strategy

The upstream migration system (`migrations/`) uses timestamp-based scripts that run once during `omarchy-update`. Your fork has 8 migrations vs upstream's ~160.

**Recommended approach:**
1. **Do NOT blindly port all 160 migrations** — most are Arch/pacman-specific
2. Categorize each migration:
   - **Distro-agnostic** (config file changes, symlinks, directory creation) → port directly
   - **Package management** (pacman/yay commands) → rewrite with `dnf` or skip
   - **Bootloader** (Limine/mkinitcpio) → rewrite for GRUB/dracut or skip
   - **AUR-specific** → skip or find Fedora equivalent
3. Create a `fedora-migrations/` or adapt the existing `migrations/` directory
4. Consider tagging migrations with the upstream version they correspond to

---

## Fedora-Specific Gotchas

| Area | Arch (upstream) | Fedora (fork) |
|------|----------------|---------------|
| Package manager | `pacman -S` / `yay -S` | `dnf install` |
| AUR | `yay` / `omarchy-pkg-aur-*` | Copr repos or build from source |
| Bootloader | Limine (+ limine-snapper) | GRUB2 |
| Initramfs | mkinitcpio | dracut |
| Boot splash | Plymouth (configured via Limine) | Plymouth (configured via GRUB) |
| Login manager | SDDM | SDDM (or GDM if GNOME was default) |
| Kernel headers | `linux-headers` | `kernel-devel` |
| Font packages | `ttf-*`, `otf-*` via pacman/AUR | `google-noto-*`, `fira-code-fonts`, etc. |
| Video acceleration | `intel-media-driver` | `intel-media-driver` (RPM Fusion) |
| Nvidia | `nvidia-dkms` | `akmod-nvidia` (RPM Fusion) |

---

## Suggested Implementation Order

```
Phase 1 — Quick Wins (1-2 days)
  ├── 1.5 AI Agent Integration (aliases + npx stubs)
  ├── 2.1 Screenshot & Screen Recording scripts
  ├── 2.2 Battery & Power Management scripts
  ├── 3.1 Hyprland Window Management scripts
  ├── 3.5 Bash Helpers & Aliases
  └── 3.6 Waybar Enhancements

Phase 2 — Core Infrastructure (3-5 days)
  ├── 1.1 Tmux Integration
  ├── 1.4 Menu System (with dnf wrapper for pkg scripts)
  ├── 2.4 Hardware Detection System
  └── 2.5 Walker App Launcher (replace wofi)

Phase 3 — Theme Overhaul (3-5 days)
  └── 1.2 Dynamic Theme System via colors.toml

Phase 4 — Advanced Features (2-3 days)
  ├── 1.3 Voxtype Dictation
  ├── 2.3 Hibernation & Suspend (GRUB/dracut adaptation)
  └── 3.3 Additional Installers (per-installer dnf mapping)

Phase 5 — Structural Alignment (ongoing)
  ├── 3.4 Install System Restructuring
  └── Migration System alignment
```

---

## References

- **Upstream repo:** https://github.com/basecamp/omarchy
- **Upstream releases:** https://github.com/basecamp/omarchy/releases
- **v3.3.0 release (Voxtype, themes, OpenCode, hibernation):** https://github.com/basecamp/omarchy/releases/tag/v3.3.0
- **v3.4.0 release (Tmux, screenshot, menu, Claude Code):** https://github.com/basecamp/omarchy/releases/tag/v3.4.0
- **v3.5.0 release (Panther Lake, ONCE, hardware detection):** https://github.com/basecamp/omarchy/releases/tag/v3.5.0
- **v3.6.0 release (toggles, lid close, battery, OLED):** https://github.com/basecamp/omarchy/releases/tag/v3.6.0
- **Upstream bin/ directory:** https://github.com/basecamp/omarchy/tree/dev/bin
- **Upstream config/ directory:** https://github.com/basecamp/omarchy/tree/dev/config
- **Upstream themes/ directory:** https://github.com/basecamp/omarchy/tree/dev/themes
- **Upstream install/ directory:** https://github.com/basecamp/omarchy/tree/dev/install
- **Upstream migrations/ directory:** https://github.com/basecamp/omarchy/tree/dev/migrations
- **Upstream default/ directory:** https://github.com/basecamp/omarchy/tree/dev/default
