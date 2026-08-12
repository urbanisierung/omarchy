-- hide copyq after copy: https://copyq.readthedocs.io/en/latest/faq.html#why-doesn-t-the-main-window-close-on-tiling-window-managers

hl.on("hyprland.start", function()
    hl.exec_cmd("hypridle & mako & waybar & fcitx5")
    hl.exec_cmd("swaybg -i ~/.config/omarchy/current/background -m fill")
    hl.exec_cmd("systemctl --user start hyprpolkitagent")
    hl.exec_cmd("wl-clip-persist --clipboard regular & clipse -listen")
    hl.exec_cmd("copyq")
    hl.exec_cmd("~/github.com/urbanisierung/dotfiles/rsync-sync.sh")
    hl.exec_cmd("eval $(gnome-keyring-daemon --start) && export SSH_AUTH_SOCK")
end)
