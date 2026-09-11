-- hide copyq after copy: https://copyq.readthedocs.io/en/latest/faq.html#why-doesn-t-the-main-window-close-on-tiling-window-managers

hl.on("hyprland.start", function()
    hl.exec_cmd("hypridle & mako & waybar & fcitx5")
    hl.exec_cmd("swaybg -i ~/.config/omarchy/current/background -m fill")
    hl.exec_cmd("systemctl --user start hyprpolkitagent")
    hl.exec_cmd("wl-clip-persist --clipboard regular & clipse -listen")
    hl.exec_cmd("copyq")
    hl.exec_cmd("~/github.com/urbanisierung/dotfiles/rsync-sync.sh")
    hl.exec_cmd("eval $(gnome-keyring-daemon --start) && export SSH_AUTH_SOCK")
    hl.exec_cmd("~/.local/share/omarchy/bin/omarchy-powerprofile boot")

    -- Hyprtasking must be loaded before its config is applied. Doing this earlier
    -- in the config parse phase produces "unknown config key" errors.
    hl.exec_cmd("hyprpm reload -n")
    hl.exec_cmd("hyprctl eval 'hl.config({ plugin = { hyprtasking = { layout = [[grid]], gap_size = 8, border_size = 2, grid = { rows = 4, cols = 5 }, jump = { enabled = true, label_size = 32 } } } })'")
end)
