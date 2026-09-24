#!/bin/bash
set -euo pipefail

if [[ $# -gt 1 || ($# -eq 1 && $1 != --autostart) ]]; then
  echo "Usage: bash setup.sh [--autostart]" >&2
  exit 2
fi
autostart=${1:-}
payload_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-usb"
checkout="$HOME/.local/share/omarchy"

if [[ $(id -u) == 0 ]]; then
  echo "Sign in as your normal administrator user; do not run this launcher with sudo." >&2
  exit 1
fi
if [[ $(uname -m) != x86_64 || $(rpm -E '%fedora') != 44 ]]; then
  echo "This test launcher requires Fedora 44 x86_64." >&2
  exit 1
fi

umask 077
mkdir -p -- "$state_dir"
exec 9>"$state_dir/lock"
flock --nonblock 9 || exit 1

if [[ -e "$state_dir/attempted" ]]; then
  if [[ -z "$autostart" ]]; then
    echo "Setup was already attempted. Review $state_dir before any manual recovery."
    echo "Do not delete the checkout or retry the installer blindly."
  fi
  exit 0
fi
if [[ -e "$checkout" || -L "$checkout" ]]; then
  printf 'Refusing existing path: %s\n' "$checkout" >&2
  exit 1
fi
if [[ ! -t 0 || ! -t 1 ]]; then
  echo "Open this launcher in an interactive terminal." >&2
  exit 1
fi
revision=$(cat "$payload_dir/revision")
if [[ ! $revision =~ ^[0-9a-f]{40}$ || ! -s "$payload_dir/boot.sh" ]]; then
  echo "Missing or invalid pinned installation payload." >&2
  exit 1
fi
bash -n "$payload_dir/boot.sh"
for command in sudo script git; do
  command -v "$command" >/dev/null || {
    echo "Missing prerequisite: $command" >&2
    exit 1
  }
done

printf '\nOmarchy TEST installation, revision %s\n' "$revision"
echo "Use only on a disposable Fedora installation. Internet access is required."
echo "This runs the existing installer: it overwrites configuration, enables"
echo "TTY autologin, installs third-party software, and still has known defects."
echo "Disk encryption does not remove the risks of unattended unlocked sessions."
echo "Enter sudo/password prompts here, never in chat. Logs may contain personal data."
echo "Decline the installer's final reboot so results can be recorded first."
read -r -p "Type INSTALL to proceed (anything else defers): " answer
[[ $answer == INSTALL ]] || exit 0

# Mark before any privileged/network work. A crash must not cause a blind rerun.
printf '%s\n' "$revision" >"$state_dir/attempted"
log_file="$state_dir/install.log"
finish() {
  local result=$?
  trap - EXIT
  printf '%s\n' "$result" >"$state_dir/exit-status"
  if ((result == 0)); then
    printf '%s\n' "$revision" >"$state_dir/completed"
    echo "Installer exited successfully; reboot and validate the desktop manually."
  else
    printf 'Setup failed (exit %s). Do not retry automatically.\n' "$result" >&2
  fi
  printf 'Results: %s\n' "$state_dir"
  if [[ -n "$autostart" ]]; then
    read -r -p "Press Enter to close this terminal." _ || true
  fi
  exit "$result"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
sudo -v
export OMARCHY_REF="$revision"
# script supplies a PTY for gum/sudo and logs output, not raw password input.
printf -v install_command 'bash %q' "$payload_dir/boot.sh"
SHELL=/bin/bash script --quiet --return --flush --command "$install_command" "$log_file"
