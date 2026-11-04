# Claude Desktop profiles

Open **Claude Profiles** in the application launcher, press **Super+Ctrl+C**,
or run `~/.local/share/omarchy/bin/omarchy-claude-desktop`.
Use Up/Down and Enter to choose; Escape cancels. Typing filters the menu.

Requires `claude-desktop-unofficial`, `wofi`, `hyprctl`, `flock`, and Python 3.
The application entry is installed by `omarchy-sync-applications`.

| Profile | Data directory | Suggested workspace |
| --- | --- | --- |
| Business | `~/.claude-instances/business` | 6 |
| Personal 1–10 | `~/.claude-instances/personal-1` … `personal-10` | 11–20 |

Profile directories are created automatically when first selected; no manual
folder setup is needed. This launcher uses Hyprland's Lua dispatcher API.

The matching workspace's profile is suggested first, even if already running.
All other free profiles come before running profiles, in numeric order.
“Free” means **not running**, not remaining subscription quota. Running rows
show the actual workspace, or “no visible window” for a tray-only instance.
Status refreshes when opening the menu and again before activating a selection.

Selecting a running window focuses it on its existing workspace. A new profile
opens on the workspace where the menu was invoked, not necessarily its suggested
workspace. Reopening a tray-only instance uses Electron's single-instance behavior.
Each profile keeps its own sign-in and settings; no existing default profile or
`second-profile` data is copied, modified, or adopted. Quit Claude fully (including
its tray instance) to make a profile free again.

## Sign-in and isolation limits

Sign in separately in each profile:

1. Select the profile and click its sign-in button.
2. Complete sign-in in the browser, choosing the intended business/personal account.
3. Allow the browser to open the `claude://` link.
4. In **Claude link / login**, select the **same profile** that started sign-in.

Only running profiles appear in the callback chooser. The login URL is forwarded
directly to that profile's data directory, not to the default Claude instance.
No callback URL is stored by this launcher, interpolated into shell code, or
sent through Hyprland.
Canceling the chooser discards the callback; restart sign-in in the app if needed.
The browser account/session is independent of the desktop profile, so verify
the account before approving each login.

`omarchy-sync-applications` installs the hidden user-level
`com.anthropic.Claude.desktop` entry and registers it for `x-scheme-handler/claude`
when Claude Desktop is installed. The app uses that desktop ID for protocol
registration, so its normal startup registration continues to use this router.
This changes `claude://` handling for this Linux user, including non-login links;
select a running destination profile for those links too. The system-wide
desktop entry and existing default profile data are not modified.

To revert, remove `~/.local/share/applications/com.anthropic.Claude.desktop` and
run `xdg-mime default claude-desktop-unofficial.desktop x-scheme-handler/claude`.
Syncing applications reinstalls the profile-aware handler.

These are separate Electron data directories, not OS sandboxes. Shared services
such as the keyring, protocol handler, global shortcuts, and Cowork helpers may
remain application-wide. Concurrent Cowork isolation is not guaranteed. Eleven
Electron instances can also consume substantial memory.