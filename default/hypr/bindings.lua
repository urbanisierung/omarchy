-- Start default apps

hl.bind("SUPER + return", hl.dsp.exec_cmd(terminal))

hl.bind("SUPER + SHIFT + F", hl.dsp.exec_cmd(fileManager))

hl.bind("SUPER + C", hl.dsp.exec_cmd(browser .. " --profile-directory=Default"))

-- bind = SUPER, M, exec, $music

hl.bind("SUPER + N", hl.dsp.exec_cmd(terminal .. " -e nvim"))

hl.bind("SUPER + Z", hl.dsp.exec_cmd(terminal .. " -e btop"))

-- bind = SUPER SHIFT, T, exec, $browser --profile-directory=Default --app="https://www.deepl.com/en/translator" --name="DeepL" --class="DeepL"

-- Offline Translation (Super + T)

hl.bind("SUPER + T", hl.dsp.exec_cmd("python3 ~/.local/bin/translate_manager.py offline"))

-- Online DeepL Translation (Super + Shift + T)

hl.bind("SUPER + SHIFT + T", hl.dsp.exec_cmd("python3 ~/.local/bin/translate_manager.py deepl"))

hl.bind("SUPER + S", hl.dsp.exec_cmd("~/.local/bin/spotlight.sh"))

hl.bind("SUPER + A", hl.dsp.exec_cmd(browser .. " --profile-directory=Default --app=\"https://chatgpt.com\" --name=\"ChatGPT\""))

hl.bind("SUPER + SHIFT + A", hl.dsp.exec_cmd(browser .. " --profile-directory=Default --app=\"https://grok.com\" --name=\"Grok\""))

hl.bind("SUPER + SHIFT + D", hl.dsp.exec_cmd(terminal .. " -e lazydocker"))

hl.bind("SUPER + G", hl.dsp.exec_cmd(messenger))

-- bind = SUPER, O, exec, obsidian -disable-gpu

hl.bind("SUPER + CTRL + P", hl.dsp.exec_cmd(passwordManager))

hl.bind("SUPER + X", hl.dsp.exec_cmd("code -enable-features=UseOzonePlatform --ozone-platform=wayland"))

hl.bind("SUPER + space", hl.dsp.exec_cmd("pkill wofi || wofi --show drun --sort-order=alphabetical"))

hl.bind("SUPER + D", hl.dsp.exec_cmd("pkill wofi || wofi --show drun --sort-order=alphabetical"))

hl.bind("SUPER + SHIFT + SPACE", hl.dsp.exec_cmd("pkill -SIGUSR1 waybar"))

hl.bind("SUPER + CTRL + SPACE", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/swaybg-next"))

hl.bind("SUPER + ALT + P", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-powerprofile toggle"))

hl.bind("SUPER + SHIFT + CTRL + SPACE", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-theme-next"))

hl.bind("SUPER + K", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-show-keybindings"))

hl.bind("SUPER + SHIFT + K", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-show-commands"))

hl.bind("SUPER + SHIFT + U", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-claude-usage"))

hl.bind("SUPER + U", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-show-repos"))

hl.bind("SHIFT + CTRL + M", hl.dsp.exec_cmd("copyq toggle"))

-- bind = SUPER, W, killactive,

hl.bind("SUPER + SHIFT + Q", hl.dsp.window.close())

hl.bind("SUPER + F", hl.dsp.window.fullscreen())

hl.bind("SUPER + SHIFT + R", hl.dsp.layout("movetoroot"))

-- End active session

hl.bind("SUPER + ESCAPE", hl.dsp.exec_cmd("loginctl lock-session"))

hl.bind("SUPER + CTRL + L", hl.dsp.exec_cmd("loginctl lock-session"))

hl.bind("SUPER + SHIFT + ESCAPE", hl.dsp.exec_cmd("systemctl suspend"))

hl.bind("SUPER + ALT + ESCAPE", hl.dsp.exit())

hl.bind("SUPER + CTRL + ESCAPE", hl.dsp.exec_cmd("reboot"))

hl.bind("SUPER + SHIFT + CTRL + ESCAPE", hl.dsp.exec_cmd("systemctl poweroff"))

poweroff_submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend"

hl.bind("SUPER + O", hl.dsp.submap("shift (s)hutdown | (e)xit | (r)eboot | (l) suspend"))

hl.define_submap("shift (s)hutdown | (e)xit | (r)eboot | (l) suspend", function()
    hl.bind("SHIFT + S", hl.dsp.exec_cmd("systemctl poweroff"))
    hl.bind("SHIFT + E", hl.dsp.exit())
    hl.bind("SHIFT + R", hl.dsp.exec_cmd("reboot"))
    hl.bind("SHIFT + L", hl.dsp.exec_cmd("systemctl suspend"))
    hl.bind("Escape", hl.dsp.submap("reset"))
end)

-- Control tiling

hl.bind("SUPER + J", hl.dsp.layout("togglesplit"))

hl.bind("SUPER + P", hl.dsp.window.pseudo())

-- bind = SUPER, V, togglefloating,

hl.bind("SUPER + V", hl.dsp.layout("preselect b"))

hl.bind("SUPER + H", hl.dsp.layout("preselect r"))

-- Move focus with mainMod + arrow keys

hl.bind("SUPER + left", hl.dsp.focus({ direction = "left" }))

hl.bind("SUPER + right", hl.dsp.focus({ direction = "right" }))

hl.bind("SUPER + up", hl.dsp.focus({ direction = "up" }))

hl.bind("SUPER + down", hl.dsp.focus({ direction = "down" }))

-- Switch workspaces with mainMod + [0-9]

hl.bind("SUPER + code:10", hl.dsp.focus({ workspace = 1 }))

hl.bind("SUPER + code:11", hl.dsp.focus({ workspace = 2 }))

hl.bind("SUPER + code:12", hl.dsp.focus({ workspace = 3 }))

hl.bind("SUPER + code:13", hl.dsp.focus({ workspace = 4 }))

hl.bind("SUPER + code:14", hl.dsp.focus({ workspace = 5 }))

hl.bind("SUPER + code:15", hl.dsp.focus({ workspace = 6 }))

hl.bind("SUPER + code:16", hl.dsp.focus({ workspace = 7 }))

hl.bind("SUPER + code:17", hl.dsp.focus({ workspace = 8 }))

hl.bind("SUPER + code:18", hl.dsp.focus({ workspace = 9 }))

hl.bind("SUPER + code:19", hl.dsp.focus({ workspace = 10 }))

hl.bind("SUPER + ALT + code:10", hl.dsp.focus({ workspace = 11 }))

hl.bind("SUPER + ALT + code:11", hl.dsp.focus({ workspace = 12 }))

hl.bind("SUPER + ALT + code:12", hl.dsp.focus({ workspace = 13 }))

hl.bind("SUPER + ALT + code:13", hl.dsp.focus({ workspace = 14 }))

hl.bind("SUPER + ALT + code:14", hl.dsp.focus({ workspace = 15 }))

hl.bind("SUPER + ALT + code:15", hl.dsp.focus({ workspace = 16 }))

hl.bind("SUPER + ALT + code:16", hl.dsp.focus({ workspace = 17 }))

hl.bind("SUPER + ALT + code:17", hl.dsp.focus({ workspace = 18 }))

hl.bind("SUPER + ALT + code:18", hl.dsp.focus({ workspace = 19 }))

hl.bind("SUPER + ALT + code:19", hl.dsp.focus({ workspace = 10 }))

-- Move active window to a workspace with mainMod + SHIFT + [0-9]

hl.bind("SUPER + SHIFT + code:10", hl.dsp.window.move({ workspace = 1 }))

hl.bind("SUPER + SHIFT + code:11", hl.dsp.window.move({ workspace = 2 }))

hl.bind("SUPER + SHIFT + code:12", hl.dsp.window.move({ workspace = 3 }))

hl.bind("SUPER + SHIFT + code:13", hl.dsp.window.move({ workspace = 4 }))

hl.bind("SUPER + SHIFT + code:14", hl.dsp.window.move({ workspace = 5 }))

hl.bind("SUPER + SHIFT + code:15", hl.dsp.window.move({ workspace = 6 }))

hl.bind("SUPER + SHIFT + code:16", hl.dsp.window.move({ workspace = 7 }))

hl.bind("SUPER + SHIFT + code:17", hl.dsp.window.move({ workspace = 8 }))

hl.bind("SUPER + SHIFT + code:18", hl.dsp.window.move({ workspace = 9 }))

hl.bind("SUPER + SHIFT + code:19", hl.dsp.window.move({ workspace = 10 }))

-- Move active window to workspaces 11-19 with mainMod + SHIFT + ALT + [0-9]

hl.bind("SUPER + SHIFT + ALT + code:10", hl.dsp.window.move({ workspace = 11 }))

hl.bind("SUPER + SHIFT + ALT + code:11", hl.dsp.window.move({ workspace = 12 }))

hl.bind("SUPER + SHIFT + ALT + code:12", hl.dsp.window.move({ workspace = 13 }))

hl.bind("SUPER + SHIFT + ALT + code:13", hl.dsp.window.move({ workspace = 14 }))

hl.bind("SUPER + SHIFT + ALT + code:14", hl.dsp.window.move({ workspace = 15 }))

hl.bind("SUPER + SHIFT + ALT + code:15", hl.dsp.window.move({ workspace = 16 }))

hl.bind("SUPER + SHIFT + ALT + code:16", hl.dsp.window.move({ workspace = 17 }))

hl.bind("SUPER + SHIFT + ALT + code:17", hl.dsp.window.move({ workspace = 18 }))

hl.bind("SUPER + SHIFT + ALT + code:18", hl.dsp.window.move({ workspace = 19 }))

hl.bind("SUPER + SHIFT + ALT + code:19", hl.dsp.window.move({ workspace = 20 }))

-- Swap active window with the one next to it with mainMod + SHIFT + arrow keys

hl.bind("SUPER + SHIFT + left", hl.dsp.window.swap({ direction = "left" }))

hl.bind("SUPER + SHIFT + right", hl.dsp.window.swap({ direction = "right" }))

hl.bind("SUPER + SHIFT + up", hl.dsp.window.swap({ direction = "up" }))

hl.bind("SUPER + SHIFT + down", hl.dsp.window.swap({ direction = "down" }))

-- Resize active window

hl.bind("SUPER + minus", hl.dsp.window.resize({ x = -100, y = 0, relative = true }))

hl.bind("SUPER + equal", hl.dsp.window.resize({ x = 100, y = 0, relative = true }))

hl.bind("SUPER + SHIFT + minus", hl.dsp.window.resize({ x = 0, y = -100, relative = true }))

hl.bind("SUPER + SHIFT + equal", hl.dsp.window.resize({ x = 0, y = 100, relative = true }))

-- Scroll through existing workspaces with mainMod + scroll

hl.bind("SUPER + mouse_down", hl.dsp.focus({ workspace = "e+1" }))

hl.bind("SUPER + mouse_up", hl.dsp.focus({ workspace = "e-1" }))

-- Move/resize windows with mainMod + LMB/RMB and dragging

hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })

hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Laptop multimedia keys for volume and LCD brightness

hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { repeating = true, locked = true })

hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { repeating = true, locked = true })

hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { repeating = true, locked = true })

hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { repeating = true, locked = true })

-- Toggle AirPods Pro connection (audio + mic) for video calls

hl.bind("SUPER + ALT + A", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/omarchy-airpods-toggle"))

hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"), { repeating = true, locked = true })

hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"), { repeating = true, locked = true })

-- Control Apple Display brightness

hl.bind("CTRL + F1", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/apple-display-brightness -5000"))

hl.bind("CTRL + F2", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/apple-display-brightness +5000"))

hl.bind("SHIFT + CTRL + F2", hl.dsp.exec_cmd("~/.local/share/omarchy/bin/apple-display-brightness +60000"))

-- Requires playerctl

hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })

hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })

hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })

hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })

-- Screenshots

hl.bind("SUPER + SHIFT + P", hl.dsp.exec_cmd("grim -g \"$(slurp)\" -t ppm - | satty --filename - --fullscreen --output-filename ~/Pictures/Screenshots/satty-$(date '+%Y%m%d-%H:%M:%S').png  --copy-command \"wl-copy\" --early-exit"))

hl.bind("PRINT", hl.dsp.exec_cmd("hyprshot -m region"))

hl.bind("SHIFT + PRINT", hl.dsp.exec_cmd("hyprshot -m window"))

hl.bind("CTRL + PRINT", hl.dsp.exec_cmd("hyprshot -m output"))

-- Color picker

hl.bind("SUPER + PRINT", hl.dsp.exec_cmd("hyprpicker -a"))

-- Clipse

hl.bind("CTRL + SUPER + V", hl.dsp.exec_cmd(terminal .. " --class clipse -e clipse"))
