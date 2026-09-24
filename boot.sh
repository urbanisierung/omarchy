#!/bin/bash
set -e

INSTALL_DIR="$HOME/.local/share/omarchy"

# Bootstrap is for new installations, never for replacing a working checkout.
if [[ -e "$INSTALL_DIR" || -L "$INSTALL_DIR" ]]; then
  printf 'Refusing to replace existing path: %s\nReview the existing checkout before retrying installation.\n' "$INSTALL_DIR" >&2
  exit 1
fi

if [[ "${OMARCHY_REF:-}" == -* ]]; then
  printf 'Invalid OMARCHY_REF: %s\n' "$OMARCHY_REF" >&2
  exit 1
fi

ascii_art=' ▄██████▄    ▄▄▄▄███▄▄▄▄      ▄████████    ▄████████  ▄████████    ▄█    █▄    ▄██   ▄
███    ███ ▄██▀▀▀███▀▀▀██▄   ███    ███   ███    ███ ███    ███   ███    ███   ███   ██▄
███    ███ ███   ███   ███   ███    ███   ███    ███ ███    █▀    ███    ███   ███▄▄▄███
███    ███ ███   ███   ███   ███    ███  ▄███▄▄▄▄██▀ ███         ▄███▄▄▄▄███▄▄ ▀▀▀▀▀▀███
███    ███ ███   ███   ███ ▀███████████ ▀▀███▀▀▀▀▀   ███        ▀▀███▀▀▀▀███▀  ▄██   ███
███    ███ ███   ███   ███   ███    ███ ▀███████████ ███    █▄    ███    ███   ███   ███
███    ███ ███   ███   ███   ███    ███   ███    ███ ███    ███   ███    ███   ███   ███
 ▀██████▀   ▀█   ███   █▀    ███    █▀    ███    ███ ████████▀    ███    █▀     ▀█████▀
                                          ███    ███'

echo -e "\n$ascii_art\n"

rpm -q git &>/dev/null || sudo dnf install -y git

echo -e "\nCloning Omarchy..."
mkdir -p "$HOME/.local/share"
BOOTSTRAP_DIR=$(mktemp -d "$HOME/.local/share/.omarchy-install.XXXXXXXX")
trap 'rm -rf -- "$BOOTSTRAP_DIR"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
git clone https://github.com/urbanisierung/omarchy.git "$BOOTSTRAP_DIR/repo" >/dev/null

# Preserve branch tracking; other fetched refs are intentionally detached.
if [[ -n "${OMARCHY_REF:-}" ]]; then
  printf 'Using reference: %s\n' "$OMARCHY_REF"
  git -C "$BOOTSTRAP_DIR/repo" fetch origin "$OMARCHY_REF"
  if git -C "$BOOTSTRAP_DIR/repo" show-ref --verify --quiet "refs/remotes/origin/$OMARCHY_REF"; then
    git -C "$BOOTSTRAP_DIR/repo" checkout -B "$OMARCHY_REF" --track "origin/$OMARCHY_REF"
  else
    git -C "$BOOTSTRAP_DIR/repo" checkout --detach FETCH_HEAD
  fi
fi

# Validate before publishing; keep the checkout if installation itself fails.
if [[ ! -s "$BOOTSTRAP_DIR/repo/install.sh" ]]; then
  echo "Downloaded checkout has no nonempty install.sh." >&2
  exit 1
fi
bash -n "$BOOTSTRAP_DIR/repo/install.sh"
mv -T --no-clobber -- "$BOOTSTRAP_DIR/repo" "$INSTALL_DIR"
if [[ -d "$BOOTSTRAP_DIR/repo" ]]; then
  echo "Installation path appeared during bootstrap; refusing to replace it." >&2
  exit 1
fi

echo -e "\nInstallation starting..."
bash "$INSTALL_DIR/install.sh"
