-- Learn how to configure Hyprland: https://wiki.hyprland.org/Configuring/

-- Change your personal monitor setup in here to keep the main config portable

dofile(os.getenv("HOME") .. "/.config/hypr/monitors.lua")  -- was: source = ~/.config/hypr/monitors.conf

-- Default applications

terminal = "ghostty"

fileManager = "nautilus --new-window"

browser = "google-chrome --new-window --ozone-platform=wayland"

music = "spotify"

passwordManager = "1password"

messenger = "signal-desktop"

webapp = browser .. " --app"

-- Use defaults Omarchy defaults

dofile(os.getenv("HOME") .. "/.local/share/omarchy/default/hypr/autostart.lua")  -- was: source = ~/.local/share/omarchy/default/hypr/autostart.conf

dofile(os.getenv("HOME") .. "/.local/share/omarchy/default/hypr/bindings.lua")  -- was: source = ~/.local/share/omarchy/default/hypr/bindings.conf

dofile(os.getenv("HOME") .. "/.local/share/omarchy/default/hypr/envs.lua")  -- was: source = ~/.local/share/omarchy/default/hypr/envs.conf

dofile(os.getenv("HOME") .. "/.local/share/omarchy/default/hypr/looknfeel.lua")  -- was: source = ~/.local/share/omarchy/default/hypr/looknfeel.conf

dofile(os.getenv("HOME") .. "/.local/share/omarchy/default/hypr/input.lua")  -- was: source = ~/.local/share/omarchy/default/hypr/input.conf

dofile(os.getenv("HOME") .. "/.local/share/omarchy/default/hypr/windows.lua")  -- was: source = ~/.local/share/omarchy/default/hypr/windows.conf

dofile(os.getenv("HOME") .. "/.config/omarchy/current/theme/hyprland.lua")  -- was: source = ~/.config/omarchy/current/theme/hyprland.conf

-- Extra autostart processes (uncomment to run Dropbox)

-- exec-once = dropbox-cli start

-- Extra env variables

hl.env("GDK_SCALE", "2")

-- Extra bindings

-- bind = SUPER, A, exec, $webapp="https://chatgpt.com"

-- bind = SUPER SHIFT, A, exec, $webapp="https://grok.com"

-- bind = SUPER, C, exec, $webapp="https://app.hey.com/calendar/weeks/"

-- bind = SUPER, E, exec, $webapp="https://app.hey.com"

hl.bind("SUPER + Y", hl.dsp.exec_cmd(webapp .. "=\"https://youtube.com/\""))

hl.bind("SUPER + SHIFT + G", hl.dsp.exec_cmd(webapp .. "=\"https://web.whatsapp.com/\""))

hl.bind("SUPER + ALT + G", hl.dsp.exec_cmd(webapp .. "=\"https://messages.google.com/web/conversations\""))

-- bind = SUPER, X, exec, $webapp="https://x.com/"

hl.bind("SUPER + SHIFT + X", hl.dsp.exec_cmd(webapp .. "=\"https://x.com/compose/post\""))

hl.bind("SUPER + SHIFT + M", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-remind"))

-- Ack/dismiss the current notification (e.g. a fired reminder) from the keyboard

hl.bind("SUPER + BackSpace", hl.dsp.exec_cmd("makoctl dismiss"))

-- Open the current notification's action (reminder Snooze/Ack chooser)

hl.bind("SUPER + SHIFT + BackSpace", hl.dsp.exec_cmd("makoctl invoke"))

-- Resize window

hl.bind("SUPER + CTRL + R", hl.dsp.submap("resize"))

hl.bind("right", hl.dsp.window.resize({ x = 50, y = 0, relative = true }), { submap = "resize" })

hl.bind("left", hl.dsp.window.resize({ x = -50, y = 0, relative = true }), { submap = "resize" })

hl.bind("up", hl.dsp.window.resize({ x = 0, y = -50, relative = true }), { submap = "resize" })

hl.bind("down", hl.dsp.window.resize({ x = 0, y = 50, relative = true }), { submap = "resize" })

hl.bind("Return", hl.dsp.submap("reset"), { submap = "resize" })

hl.bind("SUPER + R", hl.dsp.exec_cmd("~/hyprwhspr/transcribe.sh"))

hl.bind("SUPER + E", function() hl.dispatch("hyprexpo:expo", "toggle") end)

-- Control your input devices

-- See https://wiki.hypr.land/Configuring/Variables/#input

hl.config({
    input = {
        kb_layout = "de,us",
        kb_options = "compose:caps,grp:alt_space_toggle",
        repeat_rate = 40,
        repeat_delay = 600,
        touchpad = {
            scroll_factor = 0.4,
        },
    },
})

-- Scroll faster in the terminal

-- windowrule = scrolltouchpad 1.5, class:Alacritty

hl.config({
    plugin = {
        hyprexpo = {
            columns = 5,
            gap_size = 5,
            bg_col = "rgb(111111)",
            workspace_method = "center current",
            enable_gesture = true,
            gesture_distance = 300,
        },
    },
})

hl.on("hyprland.start", function()
    hl.exec_cmd("hyprpm reload -n")
end)
