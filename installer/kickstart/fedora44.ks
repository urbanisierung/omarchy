# Guided test installation: storage, keyboard/timezone and user credentials
# deliberately remain unanswered. Never add blanket clearpart/zerombr here.
graphical
url --url=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/
lang en_US.UTF-8
rootpw --lock
selinux --enforcing
firewall --enabled
firstboot --enable
services --enabled=NetworkManager,gdm
halt

%packages
@^workstation-product-environment
initial-setup
git
sudo
gnome-terminal
util-linux
util-linux-script
%end

# Only stage files here: the project requires a real user's interactive session.
%post --nochroot --erroronfail --log=/mnt/sysroot/var/log/omarchy-usb-stage.log
set -eu
payload=/run/install/repo/omarchy-usb
target=/mnt/sysroot
install -d -m 0755 "$target/usr/local/lib/omarchy-usb"
for name in setup.sh boot.sh revision; do
  install -m 0644 "$payload/$name" "$target/usr/local/lib/omarchy-usb/$name"
done
install -D -m 0644 "$payload/omarchy-usb-setup.desktop" \
  "$target/etc/xdg/autostart/omarchy-usb-setup.desktop"
systemctl --root="$target" set-default graphical.target
%end
