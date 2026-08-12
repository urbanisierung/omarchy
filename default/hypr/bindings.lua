-- Start default apps

hl.bind("SUPER + return", hl.dsp.exec(terminal))

hl.bind("SUPER SHIFT + F", hl.dsp.exec(fileManager))

hl.bind("SUPER + C", hl.dsp.exec(browser .. " --profile-directory=Default"))

-- bind = SUPER, M, exec, $music

hl.bind("SUPER + N", hl.dsp.exec(terminal .. " -e nvim"))

hl.bind("SUPER + Z", hl.dsp.exec(terminal .. " -e btop"))

-- bind = SUPER SHIFT, T, exec, $browser --profile-directory=Default --app="https://www.deepl.com/en/translator" --name="DeepL" --class="DeepL"

-- Offline Translation (Super + T)

hl.bind("SUPER + T", hl.dsp.exec("python3 ~/.local/bin/translate_manager.py offline"))

-- Online DeepL Translation (Super + Shift + T)

hl.bind("SUPER SHIFT + T", hl.dsp.exec("python3 ~/.local/bin/translate_manager.py deepl"))

hl.bind("SUPER + S", hl.dsp.exec("~/.local/bin/spotlight.sh"))

hl.bind("SUPER + A", hl.dsp.exec(browser .. " --profile-directory=Default --app=\"https://chatgpt.com\" --name=\"ChatGPT\""))

hl.bind("SUPER SHIFT + A", hl.dsp.exec(browser .. " --profile-directory=Default --app=\"https://grok.com\" --name=\"Grok\""))

hl.bind("SUPER SHIFT + D", hl.dsp.exec(terminal .. " -e lazydocker"))

hl.bind("SUPER + G", hl.dsp.exec(messenger))

-- bind = SUPER, O, exec, obsidian -disable-gpu

hl.bind("SUPER CTRL + P", hl.dsp.exec(passwordManager))

hl.bind("SUPER + X", hl.dsp.exec("code -enable-features=UseOzonePlatform --ozone-platform=wayland"))

hl.bind("SUPER + space", hl.dsp.exec("pkill wofi || wofi --show drun --sort-order=alphabetical"))

hl.bind("SUPER + D", hl.dsp.exec("pkill wofi || wofi --show drun --sort-order=alphabetical"))

hl.bind("SUPER SHIFT + SPACE", hl.dsp.exec("pkill -SIGUSR1 waybar"))

hl.bind("SUPER CTRL + SPACE", hl.dsp.exec("~/.local/share/omarchy/bin/swaybg-next"))

hl.bind("SUPER SHIFT CTRL + SPACE", hl.dsp.exec("~/.local/share/omarchy/bin/omarchy-theme-next"))

hl.bind("SUPER + K", hl.dsp.exec("~/.local/share/omarchy/bin/omarchy-show-keybindings"))

hl.bind("SUPER SHIFT + K", hl.dsp.exec("~/.local/share/omarchy/bin/omarchy-show-commands"))

hl.bind("SUPER SHIFT + U", hl.dsp.exec("~/.local/share/omarchy/bin/omarchy-claude-usage"))

hl.bind("SUPER + U", hl.dsp.exec("~/.local/share/omarchy/bin/omarchy-show-repos"))

hl.bind("SHIFT CTRL + M", hl.dsp.exec("copyq toggle"))

-- bind = SUPER, W, killactive,

hl.bind("SUPER SHIFT + Q", hl.dsp.killactive())

hl.bind("SUPER + F", hl.dsp.fullscreen())

hl.bind("SUPER SHIFT + R", hl.dsp.layoutmsg("movetoroot"))

-- End active session

hl.bind("SUPER + ESCAPE", hl.dsp.exec("hyprlock"))

hl.bind("SUPER CTRL + L", hl.dsp.exec("hyprlock"))

hl.bind("SUPER SHIFT + ESCAPE", hl.dsp.exec("systemctl suspend"))

hl.bind("SUPER ALT + ESCAPE", hl.dsp.exit())

hl.bind("SUPER CTRL + ESCAPE", hl.dsp.exec("reboot"))

hl.bind("SUPER SHIFT CTRL + ESCAPE", hl.dsp.exec("systemctl poweroff"))

local poweroff_submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend"

hl.bind("SUPER + O", hl.dsp.submap(poweroff_submap))

hl.bind("SHIFT + S", hl.dsp.exec("systemctl poweroff"), { submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend" })

hl.bind("SHIFT + E", hl.dsp.exit(), { submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend" })

hl.bind("SHIFT + R", hl.dsp.exec("reboot"), { submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend" })

hl.bind("SHIFT + L", hl.dsp.exec("systemctl suspend"), { submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend" })

hl.bind("Escape", hl.dsp.submap("reset"), { submap = "shift (s)hutdown | (e)xit | (r)eboot | (l) suspend" })

-- Control tiling

hl.bind("SUPER + J", hl.dsp.layoutmsg("togglesplit"))

hl.bind("SUPER + P", hl.dsp.pseudo())

-- bind = SUPER, V, togglefloating,

hl.bind("SUPER + V", hl.dsp.layoutmsg("preselect b"))

hl.bind("SUPER + H", hl.dsp.layoutmsg("preselect r"))

-- Move focus with mainMod + arrow keys

hl.bind("SUPER + left", hl.dsp.movefocus("l"))

hl.bind("SUPER + right", hl.dsp.movefocus("r"))

hl.bind("SUPER + up", hl.dsp.movefocus("u"))

hl.bind("SUPER + down", hl.dsp.movefocus("d"))

-- Switch workspaces with mainMod + [0-9]

hl.bind("SUPER + code:10", hl.dsp.workspace("1"))

hl.bind("SUPER + code:11", hl.dsp.workspace("2"))

hl.bind("SUPER + code:12", hl.dsp.workspace("3"))

hl.bind("SUPER + code:13", hl.dsp.workspace("4"))

hl.bind("SUPER + code:14", hl.dsp.workspace("5"))

hl.bind("SUPER + code:15", hl.dsp.workspace("6"))

hl.bind("SUPER + code:16", hl.dsp.workspace("7"))

hl.bind("SUPER + code:17", hl.dsp.workspace("8"))

hl.bind("SUPER + code:18", hl.dsp.workspace("9"))

hl.bind("SUPER + code:19", hl.dsp.workspace("10"))

hl.bind("SUPER ALT + code:10", hl.dsp.workspace("11"))

hl.bind("SUPER ALT + code:11", hl.dsp.workspace("12"))

hl.bind("SUPER ALT + code:12", hl.dsp.workspace("13"))

hl.bind("SUPER ALT + code:13", hl.dsp.workspace("14"))

hl.bind("SUPER ALT + code:14", hl.dsp.workspace("15"))

hl.bind("SUPER ALT + code:15", hl.dsp.workspace("16"))

hl.bind("SUPER ALT + code:16", hl.dsp.workspace("17"))

hl.bind("SUPER ALT + code:17", hl.dsp.workspace("18"))

hl.bind("SUPER ALT + code:18", hl.dsp.workspace("19"))

hl.bind("SUPER ALT + code:19", hl.dsp.workspace("10"))

-- Move active window to a workspace with mainMod + SHIFT + [0-9]

hl.bind("SUPER SHIFT + code:10", hl.dsp.movetoworkspace("1"))

hl.bind("SUPER SHIFT + code:11", hl.dsp.movetoworkspace("2"))

hl.bind("SUPER SHIFT + code:12", hl.dsp.movetoworkspace("3"))

hl.bind("SUPER SHIFT + code:13", hl.dsp.movetoworkspace("4"))

hl.bind("SUPER SHIFT + code:14", hl.dsp.movetoworkspace("5"))

hl.bind("SUPER SHIFT + code:15", hl.dsp.movetoworkspace("6"))

hl.bind("SUPER SHIFT + code:16", hl.dsp.movetoworkspace("7"))

hl.bind("SUPER SHIFT + code:17", hl.dsp.movetoworkspace("8"))

hl.bind("SUPER SHIFT + code:18", hl.dsp.movetoworkspace("9"))

hl.bind("SUPER SHIFT + code:19", hl.dsp.movetoworkspace("10"))

-- Move active window to workspaces 11-19 with mainMod + SHIFT + ALT + [0-9]

hl.bind("SUPER SHIFT ALT + code:10", hl.dsp.movetoworkspace("11"))

hl.bind("SUPER SHIFT ALT + code:11", hl.dsp.movetoworkspace("12"))

hl.bind("SUPER SHIFT ALT + code:12", hl.dsp.movetoworkspace("13"))

hl.bind("SUPER SHIFT ALT + code:13", hl.dsp.movetoworkspace("14"))

hl.bind("SUPER SHIFT ALT + code:14", hl.dsp.movetoworkspace("15"))

hl.bind("SUPER SHIFT ALT + code:15", hl.dsp.movetoworkspace("16"))

hl.bind("SUPER SHIFT ALT + code:16", hl.dsp.movetoworkspace("17"))

hl.bind("SUPER SHIFT ALT + code:17", hl.dsp.movetoworkspace("18"))

hl.bind("SUPER SHIFT ALT + code:18", hl.dsp.movetoworkspace("19"))

hl.bind("SUPER SHIFT ALT + code:19", hl.dsp.movetoworkspace("20"))

-- Swap active window with the one next to it with mainMod + SHIFT + arrow keys

hl.bind("SUPER SHIFT + left", hl.dsp.swapwindow("l"))

hl.bind("SUPER SHIFT + right", hl.dsp.swapwindow("r"))

hl.bind("SUPER SHIFT + up", hl.dsp.swapwindow("u"))

hl.bind("SUPER SHIFT + down", hl.dsp.swapwindow("d"))

-- Resize active window

hl.bind("SUPER + minus", hl.dsp.resizeactive("-100 0"))

hl.bind("SUPER + equal", hl.dsp.resizeactive("100 0"))

hl.bind("SUPER SHIFT + minus", hl.dsp.resizeactive("0 -100"))

hl.bind("SUPER SHIFT + equal", hl.dsp.resizeactive("0 100"))

-- Scroll through existing workspaces with mainMod + scroll

hl.bind("SUPER + mouse_down", hl.dsp.workspace("e+1"))

hl.bind("SUPER + mouse_up", hl.dsp.workspace("e-1"))

-- Move/resize windows with mainMod + LMB/RMB and dragging

hl.bind("SUPER + mouse:272", hl.dsp.movewindow(), { mouse = true })

hl.bind("SUPER + mouse:273", hl.dsp.resizewindow(), { mouse = true })

-- Laptop multimedia keys for volume and LCD brightness

hl.bind("XF86AudioRaiseVolume", hl.dsp.exec("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { repeating = true, locked = true })

hl.bind("XF86AudioLowerVolume", hl.dsp.exec("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { repeating = true, locked = true })

hl.bind("XF86AudioMute", hl.dsp.exec("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { repeating = true, locked = true })

hl.bind("XF86AudioMicMute", hl.dsp.exec("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { repeating = true, locked = true })

hl.bind("XF86MonBrightnessUp", hl.dsp.exec("brightnessctl -e4 -n2 set 5%+"), { repeating = true, locked = true })

hl.bind("XF86MonBrightnessDown", hl.dsp.exec("brightnessctl -e4 -n2 set 5%-"), { repeating = true, locked = true })

-- Control Apple Display brightness

hl.bind("CTRL + F1", hl.dsp.exec("~/.local/share/omarchy/bin/apple-display-brightness -5000"))

hl.bind("CTRL + F2", hl.dsp.exec("~/.local/share/omarchy/bin/apple-display-brightness +5000"))

hl.bind("SHIFT CTRL + F2", hl.dsp.exec("~/.local/share/omarchy/bin/apple-display-brightness +60000"))

-- Requires playerctl

hl.bind("XF86AudioNext", hl.dsp.exec("playerctl next"), { locked = true })

hl.bind("XF86AudioPause", hl.dsp.exec("playerctl play-pause"), { locked = true })

hl.bind("XF86AudioPlay", hl.dsp.exec("playerctl play-pause"), { locked = true })

hl.bind("XF86AudioPrev", hl.dsp.exec("playerctl previous"), { locked = true })

-- Screenshots

hl.bind("SUPER SHIFT + P", hl.dsp.exec("grim -g \"$(slurp)\" -t ppm - | satty --filename - --fullscreen --output-filename ~/Pictures/Screenshots/satty-$(date '+%Y%m%d-%H:%M:%S').png  --copy-command \"wl-copy\" --early-exit"))

hl.bind("PRINT", hl.dsp.exec("hyprshot -m region"))

hl.bind("SHIFT + PRINT", hl.dsp.exec("hyprshot -m window"))

hl.bind("CTRL + PRINT", hl.dsp.exec("hyprshot -m output"))

-- Color picker

hl.bind("SUPER + PRINT", hl.dsp.exec("hyprpicker -a"))

-- Clipse

hl.bind("CTRL SUPER + V", hl.dsp.exec(terminal .. " --class clipse -e clipse"))
