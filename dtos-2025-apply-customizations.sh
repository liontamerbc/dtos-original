#!/usr/bin/env bash
# DTOS-2025 post-install custom setup
# Apply your DTOS dmscripts, Qtile, Xresources and (optionally) dmenu
# after a fresh install so SUPER+P and dm-* Just Work™.

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info() { printf '\033[1;32m[INFO]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
error() {
    printf '\033[1;31m[ERR]\033[0m %s\n' "$*" >&2
    exit 1
}

if [ "$EUID" -eq 0 ]; then
    error "Do NOT run this as root. Run it as your normal user."
fi

info "Applying DTOS-2025 customizations from: $BASE_DIR"

# 1) DMSCRIPTS CONFIG
mkdir -p "$HOME/.config/dmscripts"

if [ -f "$HOME/.config/dmscripts/config" ]; then
    backup="$HOME/.config/dmscripts/config.backup.$(date +%F-%H%M%S)"
    warn "Existing dmscripts config detected. Backing up to: $backup"
    cp "$HOME/.config/dmscripts/config" "$backup"
fi

if [ -f "$BASE_DIR/dmscripts/config/config" ]; then
    info "Installing DTOS dmscripts config -> ~/.config/dmscripts/config"
    cp "$BASE_DIR/dmscripts/config/config" "$HOME/.config/dmscripts/config"
    chmod +x "$HOME/.config/dmscripts/config"
else
    warn "DTOS dmscripts config not found in bundle. Skipping."
fi

# 2) DMSCRIPTS SCRIPTS
mkdir -p "$HOME/.local/bin"

if compgen -G "$HOME/.local/bin/dm-*" >/dev/null; then
    backup_dir="$HOME/.local/bin/dm-backup-$(date +%F-%H%M%S)"
    warn "Existing dm-* scripts detected. Backing up to: $backup_dir"
    mkdir -p "$backup_dir"
    mv "$HOME"/.local/bin/dm-* "$backup_dir"/
fi

if compgen -G "$BASE_DIR/dmscripts/scripts/dm-*" >/dev/null; then
    info "Installing dm-* scripts from bundle -> ~/.local/bin/"
    cp "$BASE_DIR"/dmscripts/scripts/dm-* "$HOME/.local/bin/"
    chmod +x "$HOME"/.local/bin/dm-*
else
    warn "No dm-* scripts found in $BASE_DIR/dmscripts/scripts. Skipping."
fi

# _dm-helper.sh
if [ -f "$BASE_DIR/dmscripts/scripts/_dm-helper.sh" ]; then
    info "Installing _dm-helper.sh -> ~/.local/bin/"
    cp "$BASE_DIR/dmscripts/scripts/_dm-helper.sh" "$HOME/.local/bin/"
    chmod +x "$HOME/.local/bin/_dm-helper.sh"
fi

# 3) QTILE CONFIG
mkdir -p "$HOME/.config/qtile"

if [ -f "$HOME/.config/qtile/config.py" ]; then
    backup="$HOME/.config/qtile/config.py.backup.$(date +%F-%H%M%S)"
    warn "Existing Qtile config.py detected. Backing up to: $backup"
    cp "$HOME/.config/qtile/config.py" "$backup"
fi

if [ -f "$BASE_DIR/qtile/config.py" ]; then
    info "Installing Qtile config.py -> ~/.config/qtile/config.py"
    cp "$BASE_DIR/qtile/config.py" "$HOME/.config/qtile/config.py"
fi

if [ -f "$HOME/.config/qtile/autostart.sh" ]; then
    backup="$HOME/.config/qtile/autostart.sh.backup.$(date +%F-%H%M%S)"
    warn "Existing Qtile autostart.sh detected. Backing up to: $backup"
    cp "$HOME/.config/qtile/autostart.sh" "$backup"
fi

if [ -f "$BASE_DIR/qtile/autostart.sh" ]; then
    info "Installing Qtile autostart.sh -> ~/.config/qtile/autostart.sh"
    cp "$BASE_DIR/qtile/autostart.sh" "$HOME/.config/qtile/autostart.sh"
    chmod +x "$HOME/.config/qtile/autostart.sh"
fi

# 4) XRESOURCES (we'll use DTOS-2025/.Xresources if present)
if [ -f "$BASE_DIR/.Xresources" ]; then
    if [ -f "$HOME/.Xresources" ]; then
        backup="$HOME/.Xresources.backup.$(date +%F-%H%M%S)"
        warn "Existing ~/.Xresources detected. Backing up to: $backup"
        cp "$HOME/.Xresources" "$backup"
    fi

    info "Installing Xresources -> ~/.Xresources"
    cp "$BASE_DIR/.Xresources" "$HOME/.Xresources"

    info "Merging Xresources into X with xrdb"
    xrdb "$HOME/.Xresources" || warn "xrdb failed. Run 'xrdb ~/.Xresources' manually later."
else
    warn "No .Xresources file found in bundle. Skipping Xresources."
fi

# 5) DTOS DMENU BINARIES (if you ship compiled dmenu in DTOS-2025/dmenu/)
if [ -f "$BASE_DIR/dmenu/dmenu" ] && [ -f "$BASE_DIR/dmenu/dmenu_run" ]; then
    info "Found DTOS dmenu and dmenu_run in bundle (DTOS-2025/dmenu)."

    if command -v sudo >/dev/null 2>&1; then
        echo
        info "About to install DTOS dmenu to /usr/local/bin (requires sudo)."
        sudo cp "$BASE_DIR/dmenu/dmenu" "$BASE_DIR/dmenu/dmenu_run" /usr/local/bin/
        sudo chmod 755 /usr/local/bin/dmenu /usr/local/bin/dmenu_run
    else
        warn "sudo not found. Please manually copy dmenu and dmenu_run to /usr/local/bin as root."
    fi
else
    warn "DTOS dmenu binaries not present in DTOS-2025/dmenu. Skipping dmenu install."
fi

info "DTOS-2025 customizations applied."
echo
echo "You probably want to log out and back into Qtile,"
echo "or run:  qtile cmd-obj -o cmd -f restart"
echo
