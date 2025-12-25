#!/usr/bin/env bash
#
#    _____  _______  ____   _____
#   |  __ \|__   __|/ __ \ / ____|
#   | |  | |  | |  | |  | | (___
#   | |  | |  | |  | |  | |\___ \
#   | |__| |  | |  | |__| |____) |
#   |_____/   |_|   \____/|_____/
#
#
#  DTOS-2025 Installer (Qtile + Awesome)
#  Inspired by Derek Taylor / DistroTube style
#
# This script assumes:
#   - Arch-based distro with pacman
# shellcheck disable=SC2016
#   - You are *not* root
#   - The following exist in this folder:
#       ./awesome/
#       ./qtile/
#       ./dmscripts/
#       ./shell-color-scripts/
#

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

if [ "$(id -u)" -eq 0 ]; then
    echo "==============================================================="
    echo "  ERROR: Do NOT run this script as root."
    echo "  Run it as your normal user. Sudo will be used when needed."
    echo "==============================================================="
    exit 1
fi

if ! command -v whiptail >/dev/null 2>&1; then
    echo "Installing 'libnewt' (whiptail)..."
    sudo pacman -S --needed --noconfirm libnewt
fi

# ---------------------------------------------------------------------------
# Whiptail colors (DT vibe)
# ---------------------------------------------------------------------------

export NEWT_COLORS="
root=white,blue
border=white,blue
window=black,lightgray
shadow=black,blue
title=white,blue
button=black,blue
actbutton=white,cyan
textbox=black,lightgray
"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

error() {
    whiptail --title "DTOS-2025 ERROR" --msgbox "$1" 10 70
    clear
    exit 1
}

run_step() {
    local msg="$1"
    shift
    whiptail --title "DTOS-2025" --infobox "$msg" 7 60
    "$@" || error "$msg"
}

# Download Weather Icons TTF directly (fallback when AUR is unavailable)
install_weather_icons_manual() {
    local url="https://github.com/erikflowers/weather-icons/archive/refs/heads/master.zip"
    local tmp_dir font_dir

    tmp_dir="$(mktemp -d)" || return 1
    font_dir="$HOME/.local/share/fonts/weather-icons"
    mkdir -p "$font_dir"

    if ! curl -L --fail --silent --show-error "$url" -o "$tmp_dir/weather-icons.zip"; then
        rm -rf "$tmp_dir"
        return 1
    fi

    if ! unzip -j "$tmp_dir/weather-icons.zip" "*/font/weathericons-regular-webfont.ttf" -d "$font_dir" >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        return 1
    fi

    fc-cache -f "$font_dir" >/dev/null 2>&1
    rm -rf "$tmp_dir"
    return 0
}

# ---------------------------------------------------------------------------
# Intro / warnings (DTOS-style)
# ---------------------------------------------------------------------------

# Welcome screen
whiptail --title "Installing DTOS-2025!" --msgbox "\
This script will set up a DT-style tiling desktop
(Xmonad, AwesomeWM and/or Qtile) plus tools and configs.

You will be asked a few questions before anything changes." 15 70

# Distro warning
if ! grep -qs 'ID=arch' /etc/os-release; then
    whiptail --title "Installing DTOS-2025!" --msgbox "\
WARNING: This installer is written for Arch Linux
and Arch-based distributions that use pacman.

Running it on anything else is very likely to break things." 15 72
fi

# Big caution screen
whiptail --title "Installing DTOS-2025!" --msgbox "\
This script installs a large number of packages and
overwrites some configuration files in your home directory.

It is best used on a fresh install or a test machine,
not a critical production system." 16 72

# Ask which window managers to install (like DTOS prompts)
INSTALL_XMONAD=n
INSTALL_AWESOME=n
INSTALL_QTILE=n

if whiptail --title "Window Managers" --yesno "\
Do you wish to install Xmonad? (recommended if unsure)" 10 60; then
    INSTALL_XMONAD=y
fi

if whiptail --title "Window Managers" --yesno "\
Do you wish to install AwesomeWM?" 10 60; then
    INSTALL_AWESOME=y
fi

if whiptail --title "Window Managers" --yesno "\
Do you wish to install Qtile?" 10 60; then
    INSTALL_QTILE=y
fi

if [ "$INSTALL_XMONAD" = "n" ] && [ "$INSTALL_AWESOME" = "n" ] && [ "$INSTALL_QTILE" = "n" ]; then
    error "You must choose at least one window manager. Install cancelled."
fi

# Final confirmation, like DT's 'Shall we begin installing DTOS?'
if ! whiptail --title "Installing DTOS-2025!" --yesno "\
Shall we begin installing DTOS-2025 now?" 10 60; then
    clear
    echo "DTOS-2025: installation cancelled by user. Nothing changed."
    exit 0
fi

# ---------------------------------------------------------------------------
# System update
# ---------------------------------------------------------------------------

run_step "Updating system (pacman -Syu)..." sudo pacman -Syu --noconfirm

# ---------------------------------------------------------------------------
# Core packages
# ---------------------------------------------------------------------------

core_pkgs=(
    xorg-server xorg-xinit xorg-xrandr xorg-xsetroot xorg-xprop
    alacritty xterm thunar firefox
    rofi dmenu
    picom starship
    feh sxiv xwallpaper
    git fzf wget curl unzip
    python-psutil lm_sensors
    spice-vdagent
    noto-fonts ttf-dejavu ttf-liberation ttf-ubuntu-font-family
)

# Add WMs based on what the user chose
if [ "$INSTALL_XMONAD" = "y" ]; then
    core_pkgs+=(xmonad xmonad-contrib xmobar)
fi
if [ "$INSTALL_AWESOME" = "y" ]; then
    core_pkgs+=(awesome)
fi
if [ "$INSTALL_QTILE" = "y" ]; then
    core_pkgs+=(qtile)
fi

run_step "Installing core packages (window managers + tools)..." \
    sudo pacman -S --needed --noconfirm "${core_pkgs[@]}"

# ---------------------------------------------------------------------------
# Graphics drivers (Intel/AMD + virtual machines)
# ---------------------------------------------------------------------------

# Ensure lspci is available for GPU detection
if ! command -v lspci >/dev/null 2>&1; then
    run_step "Installing pciutils (for GPU detection)..." sudo pacman -S --needed --noconfirm pciutils
fi

gpu_info="$(lspci -nn | grep -Ei 'VGA|3D|Display' || true)"
gpu_drivers=()
virt_type=""

if echo "$gpu_info" | grep -qi intel; then
    gpu_drivers+=(
        mesa mesa-utils vulkan-mesa-layers libva-mesa-driver
        vulkan-intel intel-media-driver libva-intel-driver xf86-video-intel
    )
fi

if echo "$gpu_info" | grep -Eqi 'AMD|ATI'; then
    gpu_drivers+=(
        mesa mesa-utils vulkan-mesa-layers libva-mesa-driver
        vulkan-radeon mesa-vdpau xf86-video-amdgpu
    )
fi

# VM guest graphics drivers (installed only when running inside a VM)
if command -v systemd-detect-virt >/dev/null 2>&1; then
    virt_type="$(systemd-detect-virt 2>/dev/null || true)"
fi

case "$virt_type" in
    kvm|qemu)
        gpu_drivers+=(xf86-video-qxl xf86-video-fbdev)
        ;;
    oracle) # VirtualBox
        gpu_drivers+=(virtualbox-guest-utils virtualbox-guest-modules-arch)
        ;;
    vmware)
        gpu_drivers+=(xf86-video-vmware open-vm-tools)
        ;;
    microsoft) # Hyper-V
        gpu_drivers+=(xf86-video-fbdev)
        ;;
esac

if [ ${#gpu_drivers[@]} -gt 0 ]; then
    # De-duplicate before installing so we don't spam pacman with repeats on hybrid setups
    declare -A seen_drivers=()
    unique_gpu_drivers=()
    for pkg in "${gpu_drivers[@]}"; do
        if [ -z "${seen_drivers[$pkg]}" ]; then
            unique_gpu_drivers+=("$pkg")
            seen_drivers[$pkg]=1
        fi
    done

    run_step "Installing graphics drivers (Intel/AMD/VM)..." \
        sudo pacman -S --needed --noconfirm "${unique_gpu_drivers[@]}"
else
    whiptail --title "Graphics Drivers" --msgbox "No Intel/AMD GPU detected via lspci.

If you expected one, install drivers manually." 12 72
fi

# ---------------------------------------------------------------------------
# Wallpaper tools (sxiv, xwallpaper)
# ---------------------------------------------------------------------------

run_step "Installing wallpaper tools (sxiv, xwallpaper)..." \
    sudo pacman -S --needed --noconfirm sxiv xwallpaper

# ---------------------------------------------------------------------------
# Build tools (required for paru/AUR packages)
# ---------------------------------------------------------------------------

run_step "Installing base-devel (needed for building paru/AUR packages)..." \
    sudo pacman -S --needed --noconfirm base-devel

# ---------------------------------------------------------------------------
# Ensure ~/.local/bin is on PATH (dmscripts, dm-run, etc.)
# ---------------------------------------------------------------------------

for rc in "$HOME/.profile" "$HOME/.bashrc"; do
    if [ -f "$rc" ]; then
        if ! grep -q 'HOME/.local/bin' "$rc" 2>/dev/null; then
            printf '\n# Ensure local bin is on PATH\nexport PATH="$HOME/.local/bin:$PATH"\n' >>"$rc"
        fi
    else
        printf '#!/bin/sh\n# Ensure local bin is on PATH\nexport PATH="$HOME/.local/bin:$PATH"\n' >"$rc"
    fi
done

# ---------------------------------------------------------------------------
# Paru
# ---------------------------------------------------------------------------

if ! command -v paru >/dev/null 2>&1; then
    run_step "Installing paru (AUR helper)..." bash -c '
    cd "$HOME"
    if [ ! -d paru ]; then
      git clone https://aur.archlinux.org/paru.git
    fi
    cd paru
    makepkg -si --noconfirm
  '
fi

mkdir -p "$HOME/.config/paru"
cat >"$HOME/.config/paru/paru.conf" <<EOF
[options]
BottomUp
SudoLoop
CleanAfter
EOF

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

whiptail --title "DTOS-2025" --infobox "Font installation skipped (disabled in installer)." 7 60

# ---------------------------------------------------------------------------
# SDDM (optional)
# ---------------------------------------------------------------------------

if whiptail --title "Enable SDDM?" --yesno "SDDM is a graphical login manager.

Would you like to install and enable SDDM now?" 12 60; then
    run_step "Installing SDDM..." sudo pacman -S --needed --noconfirm sddm
    run_step "Enabling SDDM..." sudo systemctl enable sddm.service --force
else
    whiptail --title "SDDM Skipped" --msgbox "SDDM will NOT be enabled.

You can enable it later with:
  sudo systemctl enable sddm
" 12 60
fi

# ---------------------------------------------------------------------------
# dmscripts from local pack
# ---------------------------------------------------------------------------

if [ -d "$SCRIPT_DIR/dmscripts" ]; then
    run_step "Installing dmscripts from local pack..." bash -c '
    mkdir -p "$HOME/.local/bin"
    if [ -d "'"$SCRIPT_DIR"'/dmscripts/scripts" ]; then
      cp "'"$SCRIPT_DIR"'/dmscripts/scripts/"* "$HOME/.local/bin/" 2>/dev/null || true
      chmod +x "$HOME/.local/bin/"*
    fi

    sudo mkdir -p /etc/dmscripts
    if [ -f "'"$SCRIPT_DIR"'/dmscripts/config/config" ]; then
      sudo cp "'"$SCRIPT_DIR"'/dmscripts/config/config" /etc/dmscripts/config
    fi

    mkdir -p "$HOME/.config/dmscripts"
    if [ -f /etc/dmscripts/config ]; then
      cp /etc/dmscripts/config "$HOME/.config/dmscripts/config"
      sed -i "s/DMTERM=\"st -e\"/DMTERM=\"alacritty -e\"/" "$HOME/.config/dmscripts/config" 2>/dev/null || true
    fi
  '
else
    whiptail --title "dmscripts Warning" --msgbox "No ./dmscripts directory found next to install.sh.

Skipping dmscripts install." 10 70
fi

# ---------------------------------------------------------------------------
# Custom dm-setbg override from project root
# ---------------------------------------------------------------------------

if [ -f "$SCRIPT_DIR/dm-setbg" ]; then
    run_step "Installing custom dm-setbg script..." bash -c '
    mkdir -p "$HOME/.local/bin"
    cp "'"$SCRIPT_DIR"'/dm-setbg" "$HOME/.local/bin/dm-setbg"
    chmod +x "$HOME/.local/bin/dm-setbg"
  '
fi

# ---------------------------------------------------------------------------
# shell-color-scripts from local pack
# ---------------------------------------------------------------------------

if [ -d "$SCRIPT_DIR/shell-color-scripts" ]; then
    run_step "Installing shell-color-scripts from local pack..." bash -c '
    colors_dir="$HOME/.local/share/shell-color-scripts/colorscripts"
    bin_dir="$HOME/.local/bin"
    mkdir -p "$colors_dir" "$bin_dir"

    if [ -d "'"$SCRIPT_DIR"'/shell-color-scripts/colorscripts" ]; then
      shopt -s nullglob
      for f in "'"$SCRIPT_DIR"'/shell-color-scripts/colorscripts/"*; do
        cp "$f" "$colors_dir/"
        chmod +x "$colors_dir/$(basename "$f")"
      done
      shopt -u nullglob
    fi

    if [ -f "'"$SCRIPT_DIR"'/shell-color-scripts/colorscript.sh" ]; then
      cp "'"$SCRIPT_DIR"'/shell-color-scripts/colorscript.sh" "$bin_dir/colorscript"
      chmod +x "$bin_dir/colorscript"
    fi

    if ! grep -q "colorscript -r" "$HOME/.bashrc" 2>/dev/null; then
      echo "if command -v colorscript >/dev/null 2>&1; then colorscript -r; fi" >> "$HOME/.bashrc"
    fi
  '
else
    whiptail --title "shell-color-scripts Warning" --msgbox "No ./shell-color-scripts directory found next to install.sh.

Skipping shell-color-scripts install." 10 70
fi

# ---------------------------------------------------------------------------
# Picom config and AMD TearFree
# ---------------------------------------------------------------------------

run_step "Deploying picom config (vsync + AMD-friendly)..." bash -c '
  mkdir -p "$HOME/.config/picom"
  if [ -f "'"$SCRIPT_DIR"'/picom/picom.conf" ]; then
    cp "'"$SCRIPT_DIR"'/picom/picom.conf" "$HOME/.config/picom/picom.conf"
  fi
'

# Install AMD TearFree xorg snippet if AMD GPU detected
if lspci | grep -qi "AMD/ATI" && [ -f "$SCRIPT_DIR/picom/20-amdgpu-tearfree.conf" ]; then
    run_step "Installing AMD TearFree Xorg snippet..." bash -c '
    sudo install -Dm644 "'"$SCRIPT_DIR"'/picom/20-amdgpu-tearfree.conf" /etc/X11/xorg.conf.d/20-amdgpu-tearfree.conf
  '
fi

# ---------------------------------------------------------------------------
# GTK tweaks (Thunar background colors)
# ---------------------------------------------------------------------------

if [ -d "$SCRIPT_DIR/gtk-3.0" ]; then
    run_step "Applying GTK tweaks for Thunar..." bash -c '
      mkdir -p "$HOME/.config/gtk-3.0"
      cp "'"$SCRIPT_DIR"'/gtk-3.0/gtk.css" "$HOME/.config/gtk-3.0/gtk.css"
    '
fi

# ---------------------------------------------------------------------------
# DTOS backgrounds
# ---------------------------------------------------------------------------

if [ -d "$SCRIPT_DIR/dtos-backgrounds" ]; then
    run_step "Installing DTOS backgrounds..." bash -c '
    sudo mkdir -p /usr/share/backgrounds/dtos-2025
    sudo cp -r "'"$SCRIPT_DIR"'/dtos-backgrounds/"* /usr/share/backgrounds/dtos-2025/ 2>/dev/null || true
  '
else
    whiptail --title "Backgrounds Warning" --msgbox "No ./dtos-backgrounds directory found next to install.sh.

Skipping backgrounds install." 10 70
fi

# ---------------------------------------------------------------------------
# Xmonad / Awesome / Qtile configs
# ---------------------------------------------------------------------------

if [ "$INSTALL_XMONAD" = "y" ]; then
    if [ -d "$SCRIPT_DIR/xmonad" ]; then
        run_step "Copying Xmonad config..." bash -c '
      mkdir -p "$HOME/.config"
      cp -r "'"$SCRIPT_DIR"'/xmonad" "$HOME/.config/"
    '
    else
        whiptail --title "Xmonad Warning" --msgbox "You chose to install Xmonad but no ./xmonad directory
was found next to install.sh.

Xmonad config will NOT be copied." 12 70
    fi
fi

if [ "$INSTALL_AWESOME" = "y" ]; then
    if [ -d "$SCRIPT_DIR/awesome" ]; then
        run_step "Copying AwesomeWM config..." bash -c '
      mkdir -p "$HOME/.config"
      cp -r "'"$SCRIPT_DIR"'/awesome" "$HOME/.config/"
    '
    else
        whiptail --title "AwesomeWM Warning" --msgbox "You chose to install AwesomeWM but no ./awesome directory
was found next to install.sh.

AwesomeWM config will NOT be copied." 12 70
    fi
fi

if [ "$INSTALL_QTILE" = "y" ]; then
    if [ -d "$SCRIPT_DIR/qtile" ]; then
        run_step "Copying Qtile config..." bash -c '
      mkdir -p "$HOME/.config"
      cp -r "'"$SCRIPT_DIR"'/qtile" "$HOME/.config/"
      chmod +x "$HOME/.config/qtile/autostart.sh" 2>/dev/null || true
    '
    else
        whiptail --title "Qtile Warning" --msgbox "You chose to install Qtile but no ./qtile directory
was found next to install.sh.

Qtile config will NOT be copied." 12 70
    fi
fi

# ---------------------------------------------------------------------------
# Alacritty config (static DT palette)
# ---------------------------------------------------------------------------

if [ -d "$SCRIPT_DIR/alacritty" ]; then
    run_step "Copying Alacritty config..." bash -c '
      mkdir -p "$HOME/.config"
      cp -r "'"$SCRIPT_DIR"'/alacritty" "$HOME/.config/"
  '
fi

# ---------------------------------------------------------------------------
# Pywal removal (keep palette static)
# ---------------------------------------------------------------------------

if command -v wal >/dev/null 2>&1 || pacman -Q pywal >/dev/null 2>&1 || [ -d "$HOME/.config/wal" ] || [ -d "$HOME/.cache/wal" ]; then
    run_step "Removing pywal and its caches..." bash -c '
      # Uninstall pywal if the package is present
      if pacman -Q pywal >/dev/null 2>&1; then
        sudo pacman -Rns --noconfirm pywal || true
      fi

      # Drop wal caches/config so themes stop reapplying
      rm -rf "$HOME/.config/wal" "$HOME/.cache/wal"

      # Reset Xresources to the static DT palette if available
      if [ -f "'"$SCRIPT_DIR"'/.Xresources" ]; then
        cp "'"$SCRIPT_DIR"'/.Xresources" "$HOME/.Xresources"
        xrdb "$HOME/.Xresources" || true
      fi
    '
fi

# ---------------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------------

whiptail --title "DTOS-2025 Installed" --msgbox "DTOS-2025 installation is complete.

You can now:
  • Reboot and choose your DTOS window manager (Xmonad / AwesomeWM / Qtile)
  • Or start them from a TTY with startx (if configured)
Enjoy your DTOS-2025 desktop." 18 72

if whiptail --title "Reboot Now?" --yesno "Do you want to reboot now?" 8 40; then
    reboot
fi

clear
echo "DTOS-2025 installation finished. Reboot when ready."

# Install dunst auto-setup script
mkdir -p "$HOME/.local/bin"
cp "$(dirname "$0")/dtos-dunst-setup" "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/dtos-dunst-setup"
