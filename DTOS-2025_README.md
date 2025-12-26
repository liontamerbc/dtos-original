#####################################
#    _____  _______  ____   _____   #
#   |  __ \|__   __|/ __ \ / ____|  #
#   | |  | |  | |  | |  | | (___    #
#   | |  | |  | |  | |  | |\___ \   #
#   | |__| |  | |  | |__| |____) |  #
#   |_____/   |_|   \____/|_____/   #
#                                   #
#            DTOS-Original              #
#####################################

# DTOS-Original README

DTOS-Original is a modern, offline-capable, Derek Taylor–style desktop setup for
Arch-based systems. It provides:

- Qtile (DT-inspired configuration)
- AwesomeWM (DT-inspired configuration)
- dmscripts (local copy)
- shell-color-scripts (local copy)
- paru (AUR helper)
- Optional SDDM enablement

A clean, minimal, keyboard-driven workflow that *you* control.

---

## Included In This Pack

```
DTOS-Original/
 ├── install.sh
 ├── awesome/
 ├── qtile/
 ├── dmscripts/
 └── shell-color-scripts/
```

---

## Installation

```bash
unzip DTOS-Original.zip
cd DTOS-Original
chmod +x install.sh
./install.sh
```

---

## After Installation

### Wallpapers
Place wallpapers in:
```
~/Pictures/wallpapers
```

### SDDM Themes
Place themes in:
```
/usr/share/sddm/themes
```

Enable SDDM manually:
```bash
sudo systemctl enable sddm
```

---

## Updating Your Pack

Modify anything (configs, installer, scripts) then rebuild:

```bash
zip -r DTOS-Original.zip DTOS-Original
```

---

## Credits

Inspired by **Derek Taylor (DistroTube)**.
Linux is supposed to be fun — customize everything.
