# Omarchy Installation Script for Fedora Linux
# Adapted from the original Arch Linux version

# Exit immediately if a command exits with a non-zero status
set -e

# Report failures during repository setup and upgrades as well as later stages.
trap 'echo "Omarchy installation failed! Review the error before retrying: bash ~/.local/share/omarchy/install.sh" >&2' ERR

# Fedora-specific prerequisites
echo "Ensuring Fedora prerequisites are met..."

# Enable RPM Fusion repositories (needed for multimedia and proprietary packages)
for repository in free nonfree; do
  release="rpmfusion-${repository}-release"
  if ! rpm -q "$release" &>/dev/null; then
    echo "Enabling RPM Fusion $repository repository..."
    sudo dnf install -y "https://download1.rpmfusion.org/${repository}/fedora/${release}-$(rpm -E %fedora).noarch.rpm"
  fi
done

# Update system packages
echo "Updating system packages..."
sudo dnf update -y

# Finalization uses updatedb; do not depend on the selected Fedora image having it.
sudo dnf install -y plocate

# Install everything
for f in ~/.local/share/omarchy/install/*.sh; do
  # shellcheck disable=SC1090 # The ordered stage paths are expanded at runtime.
  source "$f"
done

# Ensure locate is up to date now that everything has been installed
sudo updatedb

if gum confirm "Reboot to apply all settings?"; then
  reboot
else
  reboot_status=$?
  if ((reboot_status != 1)); then
    exit "$reboot_status"
  fi
fi
