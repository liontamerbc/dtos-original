std = "lua54"

exclude_files = {
    "awesome/freedesktop/**",
    "awesome/lain/**",
    "awesome/themes/**",
}

files["awesome/**"] = {
    globals = {
        "awesome",
        "awful",
        "beautiful",
        "capi",
        "client",
        "dpi",
        "gears",
        "helpers",
        "lain",
        "mouse",
        "mousegrabber",
        "naughty",
        "root",
        "screen",
        "tag",
        "timer",
        "wibox",
        "widget",
        -- common widget state tables
        "bat_now",
        "coretemp_now",
        "cpu_now",
        "fs_now",
        "mem_now",
        "mpd_now",
        "net_now",
        "tpbat",
        "tpbat_now",
        "volume_now",
        "weather_now",
    },
    allow_defined_top = true,
    unused_args = false,
    redefined_local = false,
    max_line_length = 160,
}

files["awesome/rc.lua"] = {
    unused = false,
    redefined_local = false,
    max_line_length = 200,
}
