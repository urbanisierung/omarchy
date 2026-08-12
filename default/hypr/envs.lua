-- Cursor size

hl.env("XCURSOR_SIZE", "24")

hl.env("HYPRCURSOR_SIZE", "24")

-- Force all apps to use Wayland

hl.env("GDK_BACKEND", "wayland")

hl.env("QT_QPA_PLATFORM", "wayland")

hl.env("QT_STYLE_OVERRIDE", "kvantum")

hl.env("SDL_VIDEODRIVER", "wayland")

hl.env("MOZ_ENABLE_WAYLAND", "1")

hl.env("ELECTRON_OZONE_PLATFORM_HINT", "wayland")

hl.env("OZONE_PLATFORM", "wayland")

hl.config({
    xwayland = {
        force_zero_scaling = true,
    },
})

-- Make Chromium use XCompose and all Wayland

hl.env("CHROMIUM_FLAGS", "\"--enable-features=UseOzonePlatform --ozone-platform=wayland --gtk-version=4\"")

-- Make .desktop files available for wofi

hl.env("XDG_DATA_DIRS", "/usr/share:/usr/local/share:~/.local/share")

-- Use XCompose file

hl.env("XCOMPOSEFILE", "~/.XCompose")

-- Don't show update on first launch

hl.config({
    ecosystem = {
        no_update_news = true,
    },
})
