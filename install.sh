#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
bin_dir="$HOME/.local/bin"
command_path="$bin_dir/chronata"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"

say() {
    printf '%s\n' "$1"
}

fail() {
    printf 'chronata install: %s\n' "$1" >&2
    exit 1
}

require_python() {
    command -v python3 >/dev/null 2>&1 || fail "Python 3.10 or newer is needed; install python3 with your package manager"
    python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || fail "Python 3.10 or newer is needed; this machine has $(python3 --version)"
}

link_command() {
    mkdir -p "$bin_dir"
    ln -sfn "$here/backend/bin/chronata" "$command_path"
    say "command:  $command_path"
    case ":$PATH:" in
        *":$bin_dir:"*) ;;
        *) say "          $bin_dir is not on your PATH; add it to type 'chronata' anywhere" ;;
    esac
}

add_launcher() {
    mkdir -p "$data_home/applications"
    cat > "$data_home/applications/chronata.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Chronata
GenericName=Time log
Exec="$command_path" ui
Icon=appointment-soon
Terminal=false
Categories=Office;
ENTRY
    say "launcher: Chronata, in your applications menu"
}

start_with_systemd() {
    unit_dir="$config_home/systemd/user"
    mkdir -p "$unit_dir"
    cat > "$unit_dir/chronata.service" <<UNIT
[Unit]
Description=Chronata: page, PC on/off records and reminders
PartOf=graphical-session.target
After=graphical-session.target

[Service]
ExecStart="$command_path" service
ExecStop="$command_path" shutting-down
UMask=0077
TimeoutStopSec=20
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical-session.target
UNIT
    systemctl --user daemon-reload
    systemctl --user enable chronata.service >/dev/null 2>&1
    systemctl --user restart chronata.service
    say "running:  in the background now, and from every login (systemd)"
}

start_with_autostart() {
    mkdir -p "$config_home/autostart"
    cat > "$config_home/autostart/chronata.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Chronata in the background
Exec="$command_path" service
NoDisplay=true
X-GNOME-Autostart-enabled=true
ENTRY
    say "running:  from your next login; to start it now, run: chronata service &"
}

mention_missing_tools() {
    command -v notify-send >/dev/null 2>&1 || say "missing:  notify-send, so no reminders pop up (it comes with libnotify)"
    command -v zenity >/dev/null 2>&1 || command -v kdialog >/dev/null 2>&1 || say "missing:  zenity or kdialog, so clocking in from a bar opens the page instead"
    command -v git >/dev/null 2>&1 || say "missing:  git, needed only to save the log to a git repository"
}

remove_install() {
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user disable --now chronata.service >/dev/null 2>&1 || true
    fi
    rm -f "$config_home/systemd/user/chronata.service" "$config_home/autostart/chronata.desktop" "$data_home/applications/chronata.desktop"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload >/dev/null 2>&1 || true
    fi
    if [ "$(readlink "$command_path" 2>/dev/null)" = "$here/backend/bin/chronata" ]; then
        rm -f "$command_path"
    fi
    say "removed:  the chronata command, the launcher and the background service"
    say "kept:     your log and settings, in $data_home/chronata and $config_home/chronata"
}

if [ "${1:-}" = "--remove" ]; then
    remove_install
    exit 0
fi

require_python
link_command
add_launcher
if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
    start_with_systemd
else
    start_with_autostart
fi
mention_missing_tools
say "next:     chronata setup   (your shift, lunch and main client or project)"
