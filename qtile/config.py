# -*- coding: utf-8 -*-
import json
import os
import socket
import subprocess
import urllib.request
from pathlib import Path

os.environ["PATH"] = os.pathsep.join([
    os.environ.get("PATH", ""),
    os.path.expanduser("~/.local/bin"),
])

from libqtile import qtile, layout, bar, widget, hook
from libqtile.config import Click, Drag, Group, KeyChord, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.log_utils import logger
from typing import List  # noqa: F401

try:
    # Wayland-only: used to set keyboard layout without setxkbmap
    from libqtile.backend.wayland import InputConfig
except Exception:
    InputConfig = None

# ---------- Startup hooks ----------

def is_wayland():
    try:
        return qtile.core.name == "wayland"
    except Exception:
        return bool(os.environ.get("WAYLAND_DISPLAY"))

# Set keyboard layout on every startup
@hook.subscribe.startup
def startup():
    if not is_wayland():
        os.system("setxkbmap gb")

# Run autostart script once (your dtos autostart.sh)
@hook.subscribe.startup_once
def start_once():
    home = os.path.expanduser("~")
    subprocess.call([os.path.join(home, ".config", "qtile", "autostart.sh")])


# ---------- Basic settings ----------

mod = "mod4"              # SUPER/WIN
myTerm = "alacritty"
myBrowser = "firefox"
myVirt = "virt-manager"
myOffice = "libreoffice"
myPrime = "primevideo"
myNetflix = "netflix"
myYouTube = "youtube"
myYTMusic = "youtube-music-desktop-app"
myReddit = "reddit-desktop-bin"
myChat = "whatsapp-for-linux"

# Wayland input rules (ignored on X11). Keeps keyboard layout in sync without setxkbmap.
wl_input_rules = {}
if InputConfig is not None:
    wl_input_rules = {"type:keyboard": InputConfig(kb_layout="gb")}

# Toggle Wayland tray (StatusNotifier). Enabled now that dbus-fast is installed.
ENABLE_STATUS_NOTIFIER = True


# ---------- Helper window move functions ----------

def window_to_prev_group(qtile):
    if qtile.currentWindow is not None:
        i = qtile.groups.index(qtile.currentGroup)
        qtile.currentWindow.togroup(qtile.groups[i - 1].name)


def window_to_next_group(qtile):
    if qtile.currentWindow is not None:
        i = qtile.groups.index(qtile.currentGroup)
        qtile.currentWindow.togroup(qtile.groups[i + 1].name)


def window_to_previous_screen(qtile):
    i = qtile.screens.index(qtile.current_screen)
    if i != 0:
        group = qtile.screens[i - 1].group.name
        qtile.current_window.togroup(group)


def window_to_next_screen(qtile):
    i = qtile.screens.index(qtile.current_screen)
    if i + 1 != len(qtile.screens):
        group = qtile.screens[i + 1].group.name
        qtile.current_window.togroup(group)


def switch_screens(qtile):
    i = qtile.screens.index(qtile.current_screen)
    group = qtile.screens[i - 1].group
    qtile.current_screen.set_group(group)


def total_updates_count():
    """Count repo updates (pacman/Pamac) plus AUR updates (yay/paru)."""
    def _count(cmd):
        try:
            result = subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except FileNotFoundError:
            return None
        lines = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            # Only count lines that look like package entries, skip pacman candy art.
            if not stripped or not stripped[0].isalnum():
                continue
            lines.append(stripped)
        return len(lines)

    repo = _count(["checkupdates"])
    if repo is None:
        repo = _count(["pamac", "checkupdates", "--no-aur", "--quiet"])
    repo = repo or 0

    aur = _count(["yay", "-Qua"])
    if aur is None:
        aur = _count(["paru", "-Qua"])
    aur = aur or 0

    return str(repo + aur)


def brimscombe_temp():
    """Fetch current temp with one decimal for Brimscombe via Open-Meteo."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=51.7265&longitude=-2.1940"
        "&current=temperature_2m"
        "&timezone=Europe/London"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            temp = data.get("current", {}).get("temperature_2m")
            if temp is None:
                return "Brimscombe -- C"
            return f"Brimscombe {float(temp):.1f} C"
    except Exception:
        return "Brimscombe -- C"

# Workspace helpers: per-screen group names and focus helpers
BASE_GROUPS = ["DEV", "WWW", "SYS", "DOC", "VBOX", "CHAT", "MUS", "VID", "GFX"]
# Use letter tags to keep group names unique per screen without showing numbers.
SCREEN_TAGS = ["A", "B"]  # Extend if you add more monitors
NUM_SCREENS = len(SCREEN_TAGS)


def group_name(base, screen_index):
    return f"{base}-{SCREEN_TAGS[screen_index]}"


def focus_group_on_screen(base, screen_index=None):
    def _inner(qtile):
        target_screen = screen_index if screen_index is not None else qtile.current_screen.index
        name = group_name(base, target_screen)
        qtile.to_screen(target_screen)
        qtile.groups_map[name].toscreen(target_screen)

    return _inner


def move_window_to_group(base, screen_index=None):
    """Move focused window to the group on the given (or current) screen."""
    def _inner(qtile):
        target_screen = screen_index if screen_index is not None else qtile.current_screen.index
        name = group_name(base, target_screen)
        if qtile.current_window:
            qtile.current_window.togroup(name)

    return _inner

# Systray helper
def build_tray_widget(background):
    """Return a tray widget or None when unavailable to avoid error placeholders."""
    on_wayland = is_wayland()
    if on_wayland:
        if not ENABLE_STATUS_NOTIFIER:
            return None
        if not hasattr(widget, "StatusNotifier"):
            return None
        # Requires dbus-next; skip cleanly if missing.
        try:
            import dbus_next  # noqa: F401
        except Exception as err:
            logger.warning("StatusNotifier skipped (dbus-next missing): %s", err)
            return None
        try:
            return widget.StatusNotifier(background=background, padding=5)
        except Exception as err:
            logger.warning("StatusNotifier unavailable: %s", err)
            return None
    else:
        return widget.Systray(background=background, padding=5)

# Qtile cannot restart under Wayland; reload the config there instead.
restart_binding = lazy.reload_config() if is_wayland() else lazy.restart()

# ---------- Keybindings ----------

keys = [
    # The essentials
    Key([mod, "shift"], "Return", lazy.spawn("dm-run"), desc="Run Launcher"),
    Key([mod, "shift"], "r", restart_binding,
        desc="Reload config (Wayland) / Restart Qtile (X11)"),
    Key([mod, "shift"], "q", lazy.shutdown(), desc="Shutdown Qtile"),
    Key([mod, "shift"], "e", lazy.spawn("emacsclient -c -a emacs"), desc="Doom Emacs"),
    Key([mod], "Tab", lazy.next_layout(), desc="Toggle through layouts"),
    Key([mod], "q", lazy.window.kill(), desc="Kill active window"),

    # My app keybindings
    Key([mod], "Return",
        lazy.function(focus_group_on_screen("DEV")),
        lazy.spawn(myTerm),
        desc="Launch terminal (DEV workspace)"),
    Key([mod], "b",
        lazy.function(focus_group_on_screen("WWW")),
        lazy.spawn(myBrowser),
        desc="Firefox"),
    Key([mod], "v",
        lazy.function(focus_group_on_screen("VBOX")),
        lazy.spawn(myVirt),
        desc="virt-manager"),
    Key([mod], "o",
        lazy.function(focus_group_on_screen("DOC")),
        lazy.spawn(myOffice),
        desc="LibreOffice"),
    Key([mod], "a",
        lazy.function(focus_group_on_screen("VID")),
        lazy.spawn(myPrime),
        desc="Prime Video"),
    Key([mod, "shift"], "n",
        lazy.function(focus_group_on_screen("VID")),
        lazy.spawn(myNetflix),
        desc="Netflix"),
    Key([mod], "c",
        lazy.function(focus_group_on_screen("CHAT")),
        lazy.spawn(myChat),
        desc="WhatsApp"),
    Key([mod], "m",
        lazy.function(focus_group_on_screen("MUS")),
        lazy.spawn(myYTMusic),
        desc="YouTube Music"),
    Key([mod], "y",
        lazy.function(focus_group_on_screen("VID")),
        lazy.spawn(myYouTube),
        desc="YouTube"),

    # Focus specific monitor (0,1,2). Use Ctrl+Super+e to keep the Super+e chord free.
    Key([mod], "w", lazy.to_screen(0), desc="Focus monitor 1"),
    Key([mod, "control"], "e", lazy.to_screen(1), desc="Focus monitor 2"),
    Key([mod], "r", lazy.to_screen(2), desc="Focus monitor 3"),

    # Cycle monitors
    Key([mod], "period", lazy.next_screen(), desc="Focus next monitor"),
    Key([mod], "comma", lazy.prev_screen(), desc="Focus previous monitor"),

    # Move focused window to previous/next monitor and follow it
    Key([mod, "shift"], "comma",
        lazy.function(window_to_previous_screen),
        lazy.prev_screen(),
        desc="Move window to previous monitor and follow"),

    Key([mod, "shift"], "period",
        lazy.function(window_to_next_screen),
        lazy.next_screen(),
        desc="Move window to next monitor and follow"),

    # Treetab controls
    Key([mod, "shift"], "h", lazy.layout.move_left(), desc="TreeTab move left"),
    Key([mod, "shift"], "l", lazy.layout.move_right(), desc="TreeTab move right"),

    # Window controls
    Key([mod], "Down", lazy.layout.down(), desc="Focus down"),
    Key([mod], "Up", lazy.layout.up(), desc="Focus up"),
    Key([mod], "Left", lazy.layout.left(), desc="Focus left"),
    Key([mod], "Right", lazy.layout.right(), desc="Focus right"),

    Key([mod, "shift"], "Up",
        lazy.layout.shuffle_up(), lazy.layout.section_up(),
        desc="Move window up"),
    Key([mod, "shift"], "Down",
        lazy.layout.shuffle_down(), lazy.layout.section_down(),
        desc="Move window down"),
    Key([mod, "shift"], "Left",
        lazy.layout.shuffle_left(), lazy.layout.section_left(),
        desc="Move window left"),
    Key([mod, "shift"], "Right",
        lazy.layout.shuffle_right(), lazy.layout.section_right(),
        desc="Move window right"),

    Key([mod], "h",
        lazy.layout.shrink(), lazy.layout.decrease_nmaster(),
        desc="Shrink window / decrease master count"),
    Key([mod], "l",
        lazy.layout.grow(), lazy.layout.increase_nmaster(),
        desc="Grow window / increase master count"),
    Key([mod, "shift"], "m", lazy.layout.maximize(), desc="Maximize / restore window"),
    Key([mod], "n", lazy.layout.normalize(), desc="Normalize window sizes"),
    Key([mod, "shift"], "f", lazy.window.toggle_floating(), desc="Toggle floating"),
    Key([mod], "f", lazy.window.toggle_fullscreen(), desc="Toggle fullscreen"),

    # Stack controls
    Key([mod, "shift"], "Tab",
        lazy.layout.rotate(), lazy.layout.flip(),
        desc="Rotate stack / flip layout"),
    Key([mod], "space", lazy.layout.next(), desc="Move focus to other pane(s)"),
    Key([mod, "shift"], "space", lazy.layout.toggle_split(),
        desc="Toggle split / unsplit stack"),

    # Emacs key chord: SUPER + e then key
    KeyChord([mod], "e", [
        Key([], "e",
            lazy.spawn("emacsclient -c -a 'emacs'"),
            desc="Emacsclient Dashboard"),
        Key([], "a",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(emms)' "
                       "--eval '(emms-play-directory-tree \"~/Music/\")'"),
            desc="EMMS music"),
        Key([], "b",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(ibuffer)'"),
            desc="Emacs Ibuffer"),
        Key([], "d",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(dired nil)'"),
            desc="Emacs Dired"),
        Key([], "i",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(erc)'"),
            desc="Emacs ERC"),
        Key([], "n",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(elfeed)'"),
            desc="Emacs Elfeed"),
        Key([], "s",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(eshell)'"),
            desc="Emacs Eshell"),
        Key([], "v",
            lazy.spawn("emacsclient -c -a 'emacs' --eval '(+vterm/here nil)'"),
            desc="Emacs Vterm"),
        Key([], "w",
            lazy.spawn("emacsclient -c -a 'emacs' --eval "
                       "'(doom/window-maximize-buffer(eww \"distro.tube\"))'"),
            desc="Emacs EWW browser"),
    ]),

    # Dmenu scripts key chord: SUPER + p then key
    KeyChord([mod], "p", [
        Key([], "h", lazy.spawn("dm-hub"), desc="List all dmscripts"),
        Key([], "a", lazy.spawn("dm-sounds"), desc="Choose ambient sound"),
        Key([], "b", lazy.spawn("dm-setbg"), desc="Set background"),
        Key([], "c", lazy.spawn("dtos-colorscheme"), desc="Color scheme"),
        Key([], "e", lazy.spawn("dm-confedit"), desc="Edit config file"),
        Key([], "i", lazy.spawn("dm-maim"), desc="Take screenshot"),
        Key([], "k", lazy.spawn("dm-kill"), desc="Kill processes"),
        Key([], "m", lazy.spawn("dm-man"), desc="View manpages"),
        Key([], "n", lazy.spawn("dm-note"), desc="Notes"),
        Key([], "o", lazy.spawn("dm-bookman"), desc="Browser bookmarks"),
        Key([], "p", lazy.spawn("passmenu -p 'Pass: '"), desc="Pass menu"),
        Key([], "q", lazy.spawn("dm-logout"), desc="Logout menu"),
        Key([], "r", lazy.spawn("dm-radio"), desc="Online radio"),
        Key([], "s", lazy.spawn("dm-websearch"), desc="Web search"),
        Key([], "t", lazy.spawn("dm-translate"), desc="Translate text"),
    ]),
]


# ---------- Groups ----------

def build_screen_groups(screen_index):
    return [
        Group(
            name=group_name(base, screen_index),
            label=base,
            layout="floating" if base == "GFX" else "bsp",
        )
        for base in BASE_GROUPS
    ]


screen_groups = {index: build_screen_groups(index) for index in range(NUM_SCREENS)}
groups = [grp for screen_list in screen_groups.values() for grp in screen_list]

# Use custom bindings below instead of simple_key_binder to keep groups pinned per screen
dgroups_key_binder = None

# Group keybindings: mod+number follows the currently focused monitor
for index, base in enumerate(BASE_GROUPS, start=1):
    keys.extend([
        Key([mod], str(index),
            lazy.function(focus_group_on_screen(base)),
            desc=f"Focus {base} on current monitor"),
        Key([mod, "shift"], str(index),
            lazy.function(move_window_to_group(base)),
            desc=f"Move window to {base} on current monitor"),
    ])


# After restart, force BSP as the default layout (GFX stays floating)
@hook.subscribe.startup_complete
def set_default_layouts():
    for grp in qtile.groups_map.values():
        base = grp.name.split("-")[0]
        if base == "GFX":
            grp.setlayout("floating")
        else:
            grp.setlayout("bsp")


# ---------- Colors ----------

FALLBACK_COLORS = [
    ["#282c34", "#282c34"],
    ["#1c1f24", "#1c1f24"],
    ["#dfdfdf", "#dfdfdf"],
    ["#ff6c6b", "#ff6c6b"],
    ["#98be65", "#98be65"],
    ["#da8548", "#da8548"],
    ["#51afef", "#51afef"],
    ["#c678dd", "#c678dd"],
    ["#46d9ff", "#46d9ff"],
    ["#a9a1e1", "#a9a1e1"],
]


def load_wal_colors():
    """Pull colors from pywal cache; fall back to a static palette."""
    cache_file = Path.home() / ".cache" / "wal" / "colors.json"
    if not cache_file.exists():
        return FALLBACK_COLORS

    try:
        with cache_file.open() as f:
            wal = json.load(f)
        palette = wal.get("colors", {})
        special = wal.get("special", {})

        def pick(key, fallback):
            return palette.get(key, fallback)

        background = special.get("background", pick("color0", FALLBACK_COLORS[0][0]))
        foreground = special.get("foreground", pick("color7", FALLBACK_COLORS[2][0]))

        return [
            [background, background],
            [pick("color0", FALLBACK_COLORS[1][0])] * 2,
            [foreground, foreground],
            [pick("color1", FALLBACK_COLORS[3][0])] * 2,
            [pick("color2", FALLBACK_COLORS[4][0])] * 2,
            [pick("color3", FALLBACK_COLORS[5][0])] * 2,
            [pick("color4", FALLBACK_COLORS[6][0])] * 2,
            [pick("color5", FALLBACK_COLORS[7][0])] * 2,
            [pick("color6", FALLBACK_COLORS[8][0])] * 2,
            [pick("color7", FALLBACK_COLORS[9][0])] * 2,
        ]
    except Exception as err:
        logger.warning("Falling back to default colors (wal load failed): %s", err)
        return FALLBACK_COLORS


colors = load_wal_colors()


# ---------- Layouts ----------

layout_theme = dict(
    border_width=2,
    margin=8,
    border_focus=colors[6][0],
    border_normal=colors[1][0],
)

layouts = [
    layout.Bsp(**layout_theme),
    layout.MonadWide(**layout_theme),
    layout.Columns(**layout_theme),
    layout.RatioTile(**layout_theme),
    layout.Tile(shift_windows=True, **layout_theme),
    layout.VerticalTile(**layout_theme),
    layout.Matrix(**layout_theme),
    layout.Zoomy(**layout_theme),
    layout.MonadTall(**layout_theme),
    layout.Max(**layout_theme),
    layout.TreeTab(
        font="Ubuntu",
        fontsize=10,
        sections=["FIRST", "SECOND", "THIRD", "FOURTH"],
        section_fontsize=10,
        border_width=2,
        bg_color="1c1f24",
        active_bg="c678dd",
        active_fg="000000",
        inactive_bg="a9a1e1",
        inactive_fg="1c1f24",
        padding_left=0,
        padding_x=0,
        padding_y=5,
        section_top=10,
        section_bottom=20,
        level_shift=8,
        vspace=3,
        panel_width=200,
    ),
    layout.Floating(**layout_theme),
]


prompt = "{0}@{1}: ".format(os.environ["USER"], socket.gethostname())

widget_defaults = dict(
    font="Ubuntu Bold",
    fontsize=10,
    padding=2,
    background=colors[0],
)
extension_defaults = widget_defaults.copy()


# ---------- Bar / Widgets ----------

def init_widgets_list(visible_groups, include_systray=True):
    # Helper to create powerline-style separators
    def powerline(bg, fg):
        return widget.TextBox(
            text="",
            font="Ubuntu Mono",
            fontsize=40,
            padding=-6,
            background=bg,
            foreground=fg,
        )

    widgets = [
        widget.Sep(
            linewidth=0,
            padding=6,
            foreground=colors[2],
            background=colors[0],
        ),
        widget.GroupBox(
            font="Ubuntu Bold",
            fontsize=9,
            margin_y=3,
            margin_x=0,
            padding_y=5,
            padding_x=3,
            borderwidth=3,
            active=colors[2],
            inactive=colors[7],
            rounded=False,
            highlight_color=colors[1],
            highlight_method="line",
            visible_groups=visible_groups,
            this_current_screen_border=colors[6],
            this_screen_border=colors[4],
            other_current_screen_border=colors[6],
            other_screen_border=colors[4],
            foreground=colors[2],
            background=colors[0],
        ),
        widget.TextBox(
            text="|",
            font="Ubuntu Mono",
            background=colors[0],
            foreground="#474747",
            padding=2,
            fontsize=14,
        ),
        widget.CurrentLayout(
            foreground=colors[2],
            background=colors[0],
            padding=5,
        ),
        widget.TextBox(
            text="|",
            font="Ubuntu Mono",
            background=colors[0],
            foreground="#474747",
            padding=2,
            fontsize=14,
        ),
        widget.WindowName(
            foreground=colors[6],
            background=colors[0],
            padding=0,
        ),
    ]

    # Qtile only supports one systray; avoid adding it to every monitor
    if include_systray:
        tray = build_tray_widget(colors[0])
        if tray:
            widgets.append(tray)

    widgets += [
        widget.Sep(
            linewidth=0,
            padding=6,
            foreground=colors[0],
            background=colors[0],
        ),

        # Right side status with powerline separators
        powerline(colors[0], colors[3]),
        widget.Net(
            interface="wlp6s0",
            format="Net: {down} ↓↑ {up}",
            foreground=colors[1],
            background=colors[3],
            padding=5,
        ),
        powerline(colors[3], colors[4]),
        widget.GenPollText(
            func=brimscombe_temp,
            update_interval=900,
            foreground=colors[1],
            background=colors[4],
            padding=5,
        ),
        powerline(colors[4], colors[5]),
        widget.GenPollText(
            update_interval=1800,
            func=total_updates_count,
            fmt="Updates: {} ",
            foreground=colors[1],
            background=colors[5],
            mouse_callbacks={
                "Button1": lambda: qtile.spawn(myTerm + " -e yay -Syu")
            },
            padding=5,
        ),
        powerline(colors[5], colors[6]),
        widget.Memory(
            foreground=colors[1],
            background=colors[6],
            mouse_callbacks={
                "Button1": lambda: qtile.spawn(myTerm + " -e htop")
            },
            measure_mem="G",
            format="{MemUsed:.1f}/{MemTotal:.1f}",
            fmt="Mem: {}",
            padding=5,
        ),
        powerline(colors[6], colors[7]),
        widget.Volume(
            foreground=colors[1],
            background=colors[7],
            fmt="Vol: {}",
            padding=5,
        ),
        powerline(colors[7], colors[8]),
        widget.KeyboardLayout(
            foreground=colors[1],
            background=colors[8],
            fmt="KB: {}",
            padding=5,
        ),
        powerline(colors[8], colors[9]),
        widget.Clock(
            foreground=colors[1],
            background=colors[9],
            format="%A, %B %d - %H:%M:%S ",
        ),
    ]

    return widgets


def init_widgets_screen1():
    return init_widgets_list([g.name for g in screen_groups[0]], include_systray=True)


def init_widgets_screen2():
    return init_widgets_list([g.name for g in screen_groups[1]], include_systray=False)


def init_screens():
    return [
        Screen(top=bar.Bar(widgets=init_widgets_screen1(), opacity=1.0, size=20)),
        Screen(top=bar.Bar(widgets=init_widgets_screen2(), opacity=1.0, size=20)),
    ]


screens = init_screens()


# ---------- Mouse, floating, general behaviour ----------

mouse = [
    Drag(
        [mod],
        "Button1",
        lazy.window.set_position_floating(),
        start=lazy.window.get_position(),
    ),
    Drag(
        [mod],
        "Button3",
        lazy.window.set_size_floating(),
        start=lazy.window.get_size(),
    ),
    Click([mod], "Button2", lazy.window.bring_to_front()),
]

dgroups_app_rules: List = []  # type: ignore
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False

floating_layout = layout.Floating(
    float_rules=[
        *layout.Floating.default_float_rules,
        Match(title="Confirmation"),
        Match(title="Qalculate!"),
        Match(wm_class="kdenlive"),
        Match(wm_class="pinentry-gtk-2"),
    ]
)

auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True
auto_minimize = True

wmname = "LG3D"
