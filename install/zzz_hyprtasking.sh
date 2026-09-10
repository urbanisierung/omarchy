# Install the hyprtasking plugin: provides the SUPER + E workspace overview grid
# (a maintained successor to hyprexpo, which upstream removed from hyprland-plugins).
#
# hyprtasking is a compositor plugin, so it must be built against the exact
# Hyprland ABI via hyprpm. `hyprpm update -f` forces a header refresh so the
# plugin matches the running Hyprland (a plain `hyprpm update` can falsely report
# "up to date" and produce a "Mismatched headers" load error).

# Build dependencies for compiling Hyprland plugins via hyprpm
sudo dnf install -y \
  git cmake meson ninja-build gcc-c++ pkgconf-pkg-config \
  hyprland-devel hyprutils-devel hyprlang-devel hyprcursor-devel \
  hyprgraphics-devel aquamarine-devel pixman-devel cairo-devel pango-devel

# Refresh headers to match the installed Hyprland, then add + enable the plugin.
hyprpm update -f
hyprpm add https://github.com/raybbian/hyprtasking || true
hyprpm enable hyprtasking

# The plugin is loaded on session start by `hyprpm reload -n`
# (see config/hypr/hyprland.lua).
