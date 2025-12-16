#!/usr/bin/env bash

# Simple CLI for shell-color-scripts with safer path detection

if [[ "$DEV" -gt 0 ]]; then
    searched_paths=("./colorscripts")
else
    searched_paths=(
        "$HOME/.local/share/shell-color-scripts/colorscripts"
        "$HOME/.local/bin"
        "/usr/local/share/shell-color-scripts/colorscripts"
        "/usr/share/shell-color-scripts/colorscripts"
        "/opt/shell-color-scripts/colorscripts"
    )
fi

DIR_COLORSCRIPTS=""
for candidate in "${searched_paths[@]}"; do
    if [[ -d "$candidate" ]]; then
        DIR_COLORSCRIPTS="$candidate"
        break
    fi
done

if [[ -z "$DIR_COLORSCRIPTS" ]]; then
    echo "colorscript: no colorscripts directory found. Checked: ${searched_paths[*]}"
    exit 1
fi

if command -v find &>/dev/null; then
    LS_CMD="$(command -v find) ${DIR_COLORSCRIPTS} -maxdepth 1 -type f"
    LS_CMD_B="$(command -v find) ${DIR_COLORSCRIPTS}/blacklisted -maxdepth 1 -type f"
else
    LS_CMD="$(command -v ls) ${DIR_COLORSCRIPTS}"
    LS_CMD_B="$(command -v ls) ${DIR_COLORSCRIPTS}/blacklisted"
fi

list_colorscripts="$($LS_CMD | xargs -I {} basename {} | cut -d ' ' -f 1 | nl)"
length_colorscripts="$($LS_CMD | wc -l)"
list_blacklist="$($LS_CMD_B 2>/dev/null | xargs -I {} basename {} | cut -d ' ' -f 1 | nl || true)"
length_blacklist="$($LS_CMD_B 2>/dev/null | wc -l || 0)"

fmt_help="  %-20s\t%-54s\n"
function _help() {
    echo "Description: A collection of terminal color scripts."
    echo ""
    echo "Usage: colorscript [OPTION] [SCRIPT NAME/INDEX]"
    printf "%s" "${fmt_help}" \
        "-h, --help, help" "Print this help." \
        "-l, --list, list" "List all installed color scripts." \
        "-r, --random, random" "Run a random color script." \
        "-e, --exec, exec" "Run a specified color script by SCRIPT NAME or INDEX." \
        "-b, --blacklist, blacklist" "Blacklist a color script by SCRIPT NAME or INDEX." \
        "-u, --unblacklist, unblacklist" "Unblacklist a color script by SCRIPT NAME or INDEX." \
        "-a, --all, all" "List the outputs of all colorscripts with their SCRIPT NAME"
}

function _assert_has_colorscripts() {
    if [[ "$length_colorscripts" -le 0 ]]; then
        echo "colorscript: no color scripts found in ${DIR_COLORSCRIPTS}."
        exit 1
    fi
}

function _list() {
    _assert_has_colorscripts
    count="$($LS_CMD | wc -l)"
    echo "There are ${count} installed color scripts:"
    echo "${list_colorscripts}"
}

function _list_blacklist() {
    echo "There are $length_blacklist blacklisted color scripts:"
    echo "${list_blacklist}"
}

function _random() {
    _assert_has_colorscripts
    declare -i random_index=$RANDOM%$length_colorscripts
    [[ $random_index -eq 0 ]] && random_index=1

    random_colorscript="$(echo "${list_colorscripts}" | sed -n "${random_index}p" |
        tr -d ' ' | tr '\t' ' ' | cut -d ' ' -f 2)"
    # echo "${random_colorscript}"
    exec "${DIR_COLORSCRIPTS}/${random_colorscript}"
}

function ifhascolorscipt() {
    [[ -e "${DIR_COLORSCRIPTS}/$1" ]] && echo "Has this color script."
}

function _run_by_name() {
    _assert_has_colorscripts
    if [[ "$1" == "random" ]]; then
        _random
    elif [[ -n "$(ifhascolorscipt "$1")" ]]; then
        exec "${DIR_COLORSCRIPTS}/$1"
    else
        echo "Input error, Don't have color script named $1."
        exit 1
    fi
}

function _run_by_index() {
    _assert_has_colorscripts
    if [[ "$1" -gt 0 && "$1" -le "${length_colorscripts}" ]]; then

        colorscript="$(echo "${list_colorscripts}" | sed -n "${1}p" |
            tr -d ' ' | tr '\t' ' ' | cut -d ' ' -f 2)"
        exec "${DIR_COLORSCRIPTS}/${colorscript}"
    else
        echo "Input error, Don't have color script indexed $1."
        exit 1
    fi
}

function _run_colorscript() {
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        _run_by_index "$1"
    else
        _run_by_name "$1"
    fi
}

function _run_all() {
    _assert_has_colorscripts
    shopt -s nullglob
    for s in "$DIR_COLORSCRIPTS"/*; do
        echo "${s##*/}:"
        "$s"
        echo
    done
    shopt -u nullglob
}

function _blacklist_colorscript() { # by name only
    if [ ! -d "${DIR_COLORSCRIPTS}/blacklisted" ]; then
        sudo mkdir "${DIR_COLORSCRIPTS}/blacklisted"
    fi
    sudo mv "${DIR_COLORSCRIPTS}/$1" "${DIR_COLORSCRIPTS}/blacklisted"
}

function _unblacklist_colorscript() { # by name only
    if [ -f "${DIR_COLORSCRIPTS}/blacklisted/$1" ]; then
        sudo mv "${DIR_COLORSCRIPTS}/blacklisted/$1" "${DIR_COLORSCRIPTS}"
    else
        echo "Input error. Script $1 is not blacklisted!"
    fi
}

case "$#" in
0)
    _help
    ;;
1)
    case "$1" in
    -h | --help | help)
        _help
        ;;
    -l | --list | list)
        _list
        ;;
    -b | --blacklist | blacklist)
        _list_blacklist
        ;;
    -r | --random | random)
        _random
        ;;
    -a | --all | all)
        _run_all
        ;;
    *)
        echo "Input error."
        exit 1
        ;;
    esac
    ;;
2)
    if [[ "$1" == "-e" || "$1" == "--exec" || "$1" == "exec" ]]; then
        _run_colorscript "$2"
    elif [[ "$1" == "-b" || "$1" == "--blacklist" || "$1" == "blacklist" ]]; then
        _blacklist_colorscript "$2"
    elif [[ "$1" == "-u" || "$1" == "--unblacklist" || "$1" == "unblacklist" ]]; then
        _unblacklist_colorscript "$2"
    else
        echo "Input error."
        exit 1
    fi
    ;;
*)
    echo "Input error, too many arguments."
    exit 1
    ;;
esac
