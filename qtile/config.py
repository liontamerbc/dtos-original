# -*- coding: utf-8 -*-
import os
import socket
import subprocess
import shutil

from libqtile import qtile, layout, bar, widget, hook
from libqtile.config import Click, Drag, Group, KeyChord, Key, Match, Screen
from libqtile.log_utils import logger
from libqtile.lazy import lazy
from typing import List  # noqa: F401

try:
    import psutil  # noqa: F401
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False

IS_WAYLAND = os.environ.get("WAYLAND_DISPLAY") is not None

try:
    from libqtile.backend.wayland import InputConfig
except Exception:
    InputConfig = None

try:
    from qtile_extras.widget import StatusNotifier
except Exception:
    StatusNotifier = None

ENABLE_STATUS_NOTIFIER = True  # Toggle Wayland tray; keep on now that deps are installed

# ---------- Startup hooks ----------

# Set keyboard layout on every startup (skip the X11 command when on Wayland)
@hook.subscribe.startup
def startup():
    if not IS_WAYLAND:
        os.system("setxkbmap gb")

# Run autostart script once (your dtos autostart.sh)
@hook.subscribe.startup_once
def start_once():
    home = os.path.expanduser("~")
    subprocess.call([os.path.join(home, ".config", "qtile", "autostart.sh")])


# ---------- Basic settings ----------

mod = "mod4"              # SUPER/WIN
myTerm = "alacritty" if shutil.which("alacritty") else "xterm"
myBrowser = "firefox"
myVirt = "virt-manager"
myOffice = "libreoffice"
myPrime = "primevideo"
myNetflix = "netflix"
mySpotify = "spotify"
myReddit = "reddit-desktop-bin"
myChat = "whatsapp-for-linux"


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
        qtile.cmd_to_screen(target_screen)
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


def detect_primary_interface():
    """Return a best-guess network interface (non-loopback) or None."""
    try:
        entries = [e.name for e in os.scandir("/sys/class/net") if e.is_dir() and e.name != "lo"]
    except Exception:
        entries = []

    if not entries:
        return None

    # Prefer common prefixes; fallback to the first sorted entry.
    entries = sorted(entries)
    for prefix in ("en", "eth", "wl", "wlp"):
        for name in entries:
            if name.startswith(prefix):
                return name
    return entries[0]


def build_net_widget(foreground, background):
    iface = detect_primary_interface()
    if HAS_PSUTIL and iface:
        return widget.Net(
            interface=iface,
            format="Net: {down} ↓↑ {up}",
            foreground=foreground,
            background=background,
            padding=5,
        )
    text = "Net: N/A" if iface else "Net: no iface"
    return widget.TextBox(text=text, foreground=foreground, background=background, padding=5)


def build_memory_widget(foreground, background):
    if HAS_PSUTIL:
        return widget.Memory(
            foreground=foreground,
            background=background,
            mouse_callbacks={"Button1": lambda: qtile.cmd_spawn(myTerm + " -e htop")},
            fmt="Mem: {}",
            padding=5,
        )
    return widget.TextBox(text="Mem: N/A", foreground=foreground, background=background, padding=5)


def build_thermal_widget(foreground, background):
    if shutil.which("sensors"):
        try:
            return widget.ThermalSensor(
                foreground=foreground,
                background=background,
                threshold=90,
                fmt="Temp: {}",
                padding=5,
            )
        except Exception as err:
            logger.warning("ThermalSensor unavailable: %s", err)
    return widget.TextBox(text="Temp: N/A", foreground=foreground, background=background, padding=5)


# Wayland helpers
def build_tray_widget(background):
    """Return a tray widget or None when unavailable to avoid error placeholders."""
    if IS_WAYLAND:
        if not ENABLE_STATUS_NOTIFIER or StatusNotifier is None:
            return None
        try:
            import dbus_fast  # noqa: F401
        except Exception as err:
            logger.warning("StatusNotifier skipped (dbus-fast missing): %s", err)
            return None
        try:
            return StatusNotifier(background=background, padding=5)
        except Exception as err:
            logger.warning("StatusNotifier unavailable: %s", err)
            return None
    else:
        return widget.Systray(background=background, padding=5)

# Qtile cannot restart under Wayland; reload the config there instead.
restart_binding = lazy.reload_config() if IS_WAYLAND else lazy.restart()

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
    Key([mod], "Return", lazy.spawn(myTerm), desc="Launch terminal"),
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
    Key([mod], "n",
        lazy.function(focus_group_on_screen("VID")),
        lazy.spawn(myNetflix),
        desc="Netflix"),
    Key([mod], "c",
        lazy.function(focus_group_on_screen("CHAT")),
        lazy.spawn(myChat),
        desc="WhatsApp"),
    Key([mod], "s",
        lazy.function(focus_group_on_screen("MUS")),
        lazy.spawn(mySpotify),
        desc="Spotify"),

    # Focus specific monitor (0,1,2)
    Key([mod], "w", lazy.to_screen(0), desc="Focus monitor 1"),
    Key([mod], "e", lazy.to_screen(1), desc="Focus monitor 2"),
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
    Key([mod], "m", lazy.layout.maximize(), desc="Maximize / restore window"),
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
            layout="floating" if base == "GFX" else "monadtall",
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


# ---------- Layouts ----------

layout_theme = dict(
    border_width=2,
    margin=8,
    border_focus="e1acff",
    border_normal="1D2330",
)

layouts = [
    layout.MonadWide(**layout_theme),
    layout.Bsp(**layout_theme),
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


# ---------- Colors ----------

colors = [
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

    # Qtile only supports one tray; use the Wayland notifier widget when possible
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
        build_net_widget(colors[1], colors[3]),
        powerline(colors[3], colors[4]),
        build_thermal_widget(colors[1], colors[4]),
        powerline(colors[4], colors[5]),
        widget.CheckUpdates(
            update_interval=1800,
            distro="Arch_checkupdates",
            display_format="Updates: {updates} ",
            foreground=colors[1],
            colour_have_updates=colors[1],
            colour_no_updates=colors[1],
            mouse_callbacks={
                "Button1": lambda: qtile.cmd_spawn(
                    myTerm + " -e sudo pacman -Syu"
                )
            },
            padding=5,
            background=colors[5],
        ),
        powerline(colors[5], colors[6]),
        build_memory_widget(colors[1], colors[6]),
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
            format="%A, %B %d - %H:%M ",
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

# Wayland input configuration (keyboard layout)
wl_input_rules = {}
if IS_WAYLAND and InputConfig:
    wl_input_rules = {
        "type:keyboard": InputConfig(kb_layout="gb"),
    }
