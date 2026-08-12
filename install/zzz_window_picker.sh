#!/bin/bash
# =============================================================================
# Zoom Screen Sharing Fix for Fedora + Hyprland
# =============================================================================
# Fixes all known issues with Zoom screen sharing on Wayland/Hyprland:
#   - Portal conflicts between xdg-desktop-portal-gnome and -hyprland
#   - DMA-BUF format renegotiation loop (black screen)
#   - Screen share dying after window resize / stop+restart
#   - Missing/bad share picker (replaces with preview-based picker)
#
# Usage: bash setup-zoom-hyprland.sh
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()      { echo -e "${GREEN}[ OK ]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERR ]${NC} $*"; }
log_section() { echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${BLUE} $*${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}"; }

# =============================================================================
# STEP 1 — Install system dependencies
# =============================================================================
log_section "Step 1: Installing system dependencies"

PACKAGES=(
    xdg-desktop-portal
    xdg-desktop-portal-hyprland
    xdg-desktop-portal-gtk
    pipewire
    wireplumber
    gtk4
    gtk4-devel
    meson
    ninja-build
    wayland-protocols-devel
    wayland-devel
    pkg-config
    cargo
    rustup
    git
    clang
)

log_info "Installing packages via dnf..."
sudo dnf install -y "${PACKAGES[@]}" || {
    log_warn "Some packages may have failed — continuing anyway"
}

# Install gtk4-layer-shell (runtime)
log_info "Installing gtk4-layer-shell..."
sudo dnf install -y gtk4-layer-shell.x86_64 || log_warn "gtk4-layer-shell install failed"

# Install gtk4-layer-shell-devel — has a known Fedora packaging conflict,
# so we use rpm --replacefiles to work around it
log_info "Installing gtk4-layer-shell-devel (working around Fedora packaging conflict)..."
TMP_DIR=$(mktemp -d)
pushd "$TMP_DIR" > /dev/null
if dnf download gtk4-layer-shell-devel.x86_64 2>/dev/null; then
    sudo rpm -i --replacefiles gtk4-layer-shell-devel-*.rpm && \
        log_ok "gtk4-layer-shell-devel installed via rpm --replacefiles" || \
        log_warn "gtk4-layer-shell-devel install failed — may already be installed"
else
    log_warn "Could not download gtk4-layer-shell-devel, trying direct install..."
    sudo dnf install -y gtk4-layer-shell-devel.x86_64 --allowerasing || \
        log_warn "gtk4-layer-shell-devel install failed"
fi
popd > /dev/null
rm -rf "$TMP_DIR"

log_ok "System dependencies done"

# =============================================================================
# STEP 2 — Install Rust nightly toolchain (needed for share-picker)
# =============================================================================
log_section "Step 2: Setting up Rust nightly toolchain"

if ! command -v rustup &>/dev/null; then
    log_info "Installing rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain nightly
    source "$HOME/.cargo/env"
else
    log_info "rustup already installed, installing nightly toolchain..."
    rustup toolchain install nightly
fi

log_ok "Rust nightly ready"

# =============================================================================
# STEP 3 — Build and install hyprland-preview-share-picker
# =============================================================================
log_section "Step 3: Building hyprland-preview-share-picker"

PICKER_DIR="$HOME/.local/src/hyprland-preview-share-picker"

if [[ -d "$PICKER_DIR" ]]; then
    log_info "Updating existing clone..."
    git -C "$PICKER_DIR" pull
    git -C "$PICKER_DIR" submodule update --recursive
else
    log_info "Cloning repository..."
    mkdir -p "$(dirname "$PICKER_DIR")"
    git clone --recursive https://github.com/WhySoBad/hyprland-preview-share-picker "$PICKER_DIR"
fi

pushd "$PICKER_DIR" > /dev/null
log_info "Building (this may take a few minutes)..."
RUSTUP_TOOLCHAIN=nightly cargo build --release

log_info "Installing binary to /usr/local/bin..."
sudo install -Dm755 target/release/hyprland-preview-share-picker /usr/local/bin/
popd > /dev/null

log_ok "hyprland-preview-share-picker installed"

# =============================================================================
# STEP 4 — Configure xdg-desktop-portal-hyprland (xdph.conf)
# =============================================================================
log_section "Step 4: Configuring xdg-desktop-portal-hyprland"

mkdir -p "$HOME/.config/hypr"

cat > "$HOME/.config/hypr/xdph.conf" << 'EOF'
screencopy {
    # Use the preview-based share picker instead of the default Qt one
    custom_picker_binary = hyprland-preview-share-picker
    # Auto-tick "allow restore token" so the picker is skipped on subsequent shares
    allow_token_by_default = true
    max_fps = 60
}
EOF

log_ok "xdph.conf written to ~/.config/hypr/xdph.conf"

# =============================================================================
# STEP 5 — Configure portal backend selection (hyprland-portals.conf)
#           Ensures Hyprland's portal wins over gnome's even when both are
#           installed (gnome-shell hard-depends on xdg-desktop-portal-gnome)
# =============================================================================
log_section "Step 5: Configuring portal backend priority"

mkdir -p "$HOME/.config/xdg-desktop-portal"

cat > "$HOME/.config/xdg-desktop-portal/hyprland-portals.conf" << 'EOF'
[preferred]
default = hyprland;gtk
org.freedesktop.impl.portal.ScreenCast = hyprland
org.freedesktop.impl.portal.Screenshot = hyprland
org.freedesktop.impl.portal.RemoteDesktop = hyprland
EOF

log_ok "hyprland-portals.conf written"

# =============================================================================
# STEP 6 — Write portal restart script
#           Kills gnome portal (which auto-starts and conflicts) and restarts
#           the hyprland portal cleanly on each Hyprland session start
# =============================================================================
log_section "Step 6: Writing portal restart script"

cat > "$HOME/.config/hypr/fix-portals.sh" << 'EOF'
#!/bin/bash
# Runs on Hyprland startup via exec-once
# Kills any competing portal backends and starts a clean hyprland portal

sleep 2

# Kill gnome portal — it auto-starts even in Hyprland sessions and conflicts
killall xdg-desktop-portal-gnome 2>/dev/null || true
killall xdg-desktop-portal-gtk   2>/dev/null || true
killall xdg-desktop-portal-hyprland 2>/dev/null || true
killall xdg-desktop-portal       2>/dev/null || true

sleep 1

/usr/libexec/xdg-desktop-portal-hyprland &
sleep 2
/usr/libexec/xdg-desktop-portal &
EOF

chmod +x "$HOME/.config/hypr/fix-portals.sh"
log_ok "fix-portals.sh written to ~/.config/hypr/fix-portals.sh"

# =============================================================================
# STEP 7 — Write Zoom wrapper script
#           Ensures portal is clean before Zoom starts, sets correct env vars
# =============================================================================
log_section "Step 7: Writing Zoom wrapper script"

mkdir -p "$HOME/.local/bin"

cat > "$HOME/.local/bin/zoomw" << 'EOF'
#!/bin/bash
# Zoom wrapper for Hyprland/Wayland
# Kills the gnome portal and restarts the hyprland portal fresh before launch
# to avoid the black screen on second share attempt

# Kill gnome portal that fights with hyprland portal
killall xdg-desktop-portal-gnome 2>/dev/null || true

# Ensure hyprland portal is running and fresh
systemctl --user restart xdg-desktop-portal-hyprland.service
sleep 1
systemctl --user restart xdg-desktop-portal.service
sleep 1

# Launch Zoom with German keyboard layout
# QT_QPA_PLATFORM is intentionally left as Wayland (no xcb override)
XKB_DEFAULT_LAYOUT=de zoom "$@"
EOF

chmod +x "$HOME/.local/bin/zoomw"
log_ok "Zoom wrapper written to ~/.local/bin/zoomw"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    log_warn "~/.local/bin is not in your PATH — add this to your shell rc:"
    echo '    export PATH="$HOME/.local/bin:$PATH"'
fi

# =============================================================================
# STEP 8 — Write portal rescue keybind script
#           Hit Super+Shift+P after a share goes black to recover without
#           restarting Zoom or leaving the meeting
# =============================================================================
log_section "Step 8: Writing portal rescue script"

cat > "$HOME/.config/hypr/fix-screenshare.sh" << 'EOF'
#!/bin/bash
# Restart portal without touching Zoom
# Bind to a key in hyprland.conf:
#   bind = SUPER SHIFT, P, exec, ~/.config/hypr/fix-screenshare.sh
systemctl --user restart xdg-desktop-portal-hyprland.service
sleep 1
systemctl --user restart xdg-desktop-portal.service
EOF

chmod +x "$HOME/.config/hypr/fix-screenshare.sh"
log_ok "Rescue script written to ~/.config/hypr/fix-screenshare.sh"

# =============================================================================
# STEP 9 — Patch hyprland.conf
# =============================================================================
log_section "Step 9: Patching hyprland.conf"

HYPRCONF="$HOME/.config/hypr/hyprland.conf"

if [[ ! -f "$HYPRCONF" ]]; then
    log_warn "hyprland.conf not found at $HYPRCONF — skipping auto-patch"
    log_warn "Add these lines manually to your hyprland config:"
else
    # Check what's already there and only add missing lines
    ADDITIONS=""

    grep -q "XDG_CURRENT_DESKTOP" "$HYPRCONF" || \
        ADDITIONS+=$'\nenv = XDG_CURRENT_DESKTOP, Hyprland'
    grep -q "XDG_SESSION_TYPE" "$HYPRCONF" || \
        ADDITIONS+=$'\nenv = XDG_SESSION_TYPE, wayland'
    grep -q "XDG_SESSION_DESKTOP" "$HYPRCONF" || \
        ADDITIONS+=$'\nenv = XDG_SESSION_DESKTOP, Hyprland'
    grep -q "dbus-update-activation-environment" "$HYPRCONF" || \
        ADDITIONS+=$'\nexec-once = dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP'
    grep -q "fix-portals.sh" "$HYPRCONF" || \
        ADDITIONS+=$'\nexec-once = ~/.config/hypr/fix-portals.sh'
    grep -q "fix-screenshare.sh" "$HYPRCONF" || \
        ADDITIONS+=$'\nbind = SUPER SHIFT, P, exec, ~/.config/hypr/fix-screenshare.sh'

    if [[ -n "$ADDITIONS" ]]; then
        cp "$HYPRCONF" "$HYPRCONF.bak"
        log_info "Backed up hyprland.conf to hyprland.conf.bak"
        printf "\n# === Zoom screen sharing fix (added by setup-zoom-hyprland.sh) ===%s\n" \
            "$ADDITIONS" >> "$HYPRCONF"
        log_ok "hyprland.conf patched"
    else
        log_ok "hyprland.conf already has all required lines — nothing to add"
    fi
fi

# Print what to add manually if conf wasn't found
if [[ ! -f "$HYPRCONF" ]]; then
    cat << 'MANUAL'
    env = XDG_CURRENT_DESKTOP, Hyprland
    env = XDG_SESSION_TYPE, wayland
    env = XDG_SESSION_DESKTOP, Hyprland
    exec-once = dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP
    exec-once = ~/.config/hypr/fix-portals.sh
    bind = SUPER SHIFT, P, exec, ~/.config/hypr/fix-screenshare.sh
MANUAL
fi

# =============================================================================
# STEP 10 — Patch zoomus.conf
# =============================================================================
log_section "Step 10: Patching Zoom config"

ZOOMCONF="$HOME/.config/zoomus.conf"

if [[ -f "$ZOOMCONF" ]]; then
    cp "$ZOOMCONF" "$ZOOMCONF.bak"
    log_info "Backed up zoomus.conf"

    # enableWaylandShare
    if grep -q "^enableWaylandShare=" "$ZOOMCONF"; then
        sed -i 's/^enableWaylandShare=.*/enableWaylandShare=true/' "$ZOOMCONF"
    else
        echo "enableWaylandShare=true" >> "$ZOOMCONF"
    fi

    # xwayland — set to false for native Wayland mode
    if grep -q "^xwayland=" "$ZOOMCONF"; then
        sed -i 's/^xwayland=.*/xwayland=false/' "$ZOOMCONF"
    else
        echo "xwayland=false" >> "$ZOOMCONF"
    fi

    # enableMiniWindow — disable to avoid resize-triggered stream teardown
    if grep -q "^enableMiniWindow=" "$ZOOMCONF"; then
        sed -i 's/^enableMiniWindow=.*/enableMiniWindow=false/' "$ZOOMCONF"
    else
        echo "enableMiniWindow=false" >> "$ZOOMCONF"
    fi

    log_ok "zoomus.conf patched"
else
    log_warn "zoomus.conf not found — Zoom hasn't been run yet, or is in a different location"
    log_warn "After first Zoom launch, re-run this script or manually set:"
    echo "    enableWaylandShare=true"
    echo "    xwayland=false"
    echo "    enableMiniWindow=false"
fi

# =============================================================================
# STEP 11 — Restart portals now
# =============================================================================
log_section "Step 11: Restarting portals"

systemctl --user restart xdg-desktop-portal-hyprland.service && \
    log_ok "xdg-desktop-portal-hyprland restarted" || \
    log_warn "Failed to restart xdg-desktop-portal-hyprland"

sleep 1

systemctl --user restart xdg-desktop-portal.service && \
    log_ok "xdg-desktop-portal restarted" || \
    log_warn "Failed to restart xdg-desktop-portal"

# =============================================================================
# Done
# =============================================================================
log_section "All done!"

echo ""
echo -e "  ${GREEN}How to use Zoom:${NC}"
echo "    Run Zoom via the wrapper:  zoomw"
echo "    In Zoom: Settings → Share Screen → Advanced → set 'Pipewire Mode'"
echo ""
echo -e "  ${GREEN}If screen share goes black mid-meeting:${NC}"
echo "    Press  Super + Shift + P  to rescue the portal without leaving the meeting"
echo ""
echo -e "  ${YELLOW}Log out and back in (or reboot) for all hyprland.conf changes to take effect.${NC}"
echo ""