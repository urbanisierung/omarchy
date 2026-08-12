-- See https://wiki.hyprland.org/Configuring/Window-Rules/ for more

-- Hyprland 0.53+ syntax

hl.window_rule({
    suppress_event = "maximize",
    match = { class = ".*" },
})

-- Tag all windows for default opacity (apps can override with -default-opacity tag)

hl.window_rule({
    tag = "+default-opacity",
    match = { class = ".*" },
})

-- Fix some dragging issues with XWayland

hl.window_rule({
    no_focus = true,
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
})

-- App-specific tweaks (may remove default-opacity tag)

-- source = ~/.local/share/omarchy/default/hypr/apps.conf

-- Apply default opacity after apps have had a chance to opt out

hl.window_rule({
    opacity = { 0.97, 0.9 },
    match = { tag = "default-opacity" },
})
