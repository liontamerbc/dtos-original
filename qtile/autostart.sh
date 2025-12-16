#!/bin/sh
# DTOS Qtile autostart (Dan wallpaper-persist fix v2)

# Set keyboard layout explicitly (Qtile also has hook, but this is fine as backup)
setxkbmap gb &

# Start compositor (picom config is installed by DTOS-2025)
picom --config "$HOME/.config/picom/picom.conf" &

# Start network applet if installed
# nm-applet &

# Start any other tray apps you want
# volumeicon &
# Dunst notification daemon
dunst &

### WALLPAPER RESTORE LOGIC ###
# We try, in order:
#  1. Qtile-specific cache (~/.cache/wall_qtile) if it exists and is non-empty
#  2. Generic DTOS cache   (~/.cache/wall)      if it exists and is non-empty
#  3. Fallback: random DTOS wallpaper so we never get a black screen

WALL_QTILE="$HOME/.cache/wall_qtile"
WALL_GENERIC="$HOME/.cache/wall"
WALL_DIR="/usr/share/backgrounds/dtos-backgrounds"

if [ -s "$WALL_QTILE" ]; then
    # Non-empty Qtile-specific cache file – use it
    xargs xwallpaper --stretch <"$WALL_QTILE" &
elif [ -s "$WALL_GENERIC" ]; then
    # Non-empty generic cache – use that
    xargs xwallpaper --stretch <"$WALL_GENERIC" &
else
    # No valid cache, pick a random DTOS wallpaper
    if [ -d "$WALL_DIR" ]; then
        find "$WALL_DIR" -type f | shuf -n 1 | xwallpaper --stretch &
    fi
fi

# If you prefer nitrogen instead of xwallpaper, comment the whole block above
# and uncomment this:
# nitrogen --restore &

exit 0
