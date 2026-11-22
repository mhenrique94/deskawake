#!/usr/bin/env bash
set -euo pipefail
umask 022

SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/deskawake"
BIN_DIR="$HOME/.local/bin"
SERVICE="${XDG_DATA_HOME:-$HOME/.local/share}/dbus-1/services/org.local.DeskAwake.service"
AUTOSTART_DIR="$HOME/.config/autostart"
STATE_DIR="$HOME/.local/state/deskawake"
CONFIG_DIR="$HOME/.config/deskawake"
PLASMOID_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/plasma/plasmoids/org.local.deskawake"
KPKG_TOOL=${KPKG_TOOL:-kpackagetool6}

DAEMON_NAME="org.local.DeskAwake"
UI_NAME="org.local.DeskAwake.Ui"
DAEMON_OBJECT="/org/local/DeskAwake"
PURGE=0
PLASMOID_FAILED=0
GDBUS_BIN="$(command -v gdbus 2>/dev/null || true)"

usage() {
    cat <<'EOF'
Uso: ./uninstall.sh [--purge] [--help]

Remove a instalação do DeskAwake no perfil do usuário.

  --purge   remove também ~/.config/deskawake/
  --help    mostra esta ajuda

Sem --purge, a configuração do usuário é preservada.
EOF
}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'aviso: %s\n' "$*"
}

die_usage() {
    printf 'uninstall.sh: %s\n' "$*" >&2
    exit 2
}

system_package_installed() {
    dpkg-query -W -f='${Status}' deskawake 2>/dev/null \
        | grep -q 'install ok installed' \
        || [[ -e /usr/lib/deskawake ]]
}

while (($#)); do
    case "$1" in
        --purge)
            PURGE=1
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            die_usage "flag desconhecida: $1"
            ;;
    esac
    shift
done

if [[ -z "${HOME:-}" || "$HOME" != /* ]]; then
    printf 'uninstall.sh: HOME inválido; caminho absoluto obrigatório\n' >&2
    exit 2
fi

if [[ -n "${XDG_DATA_HOME:-}" && "$XDG_DATA_HOME" != /* ]]; then
    printf 'uninstall.sh: XDG_DATA_HOME inválido; caminho absoluto obrigatório\n' >&2
    exit 2
fi

if system_package_installed; then
    warn "pacote deskawake instalado system-wide; ele não é removido por este script (use \"apt remove deskawake\")"
fi

name_has_owner() {
    local name="$1"
    local output

    [[ -n "$GDBUS_BIN" ]] || return 1
    output=$(
        "$GDBUS_BIN" call --session \
            --dest org.freedesktop.DBus \
            --object-path /org/freedesktop/DBus \
            --method org.freedesktop.DBus.NameHasOwner "$name" \
            2>/dev/null
    ) || return 1
    [[ "$output" == *true* ]]
}

get_owner_pid() {
    local name="$1"
    local output
    local pid

    [[ -n "$GDBUS_BIN" ]] || return 1
    output=$(
        "$GDBUS_BIN" call --session \
            --dest org.freedesktop.DBus \
            --object-path /org/freedesktop/DBus \
            --method org.freedesktop.DBus.GetConnectionUnixProcessID "$name" \
            2>/dev/null
    ) || return 1
    pid="$(
        printf '%s' "$output" \
            | sed -n 's/.*uint32 \([0-9][0-9]*\).*/\1/p' \
            | head -n1
    )"
    [[ -n "$pid" ]] || return 1
    printf '%s' "$pid"
}

wait_name_gone() {
    local name="$1"
    local seconds="$2"
    local attempt

    for ((attempt = 0; attempt < seconds * 10; attempt++)); do
        name_has_owner "$name" || return 0
        sleep 0.1
    done
    return 1
}

terminate_name() {
    local name="$1"
    local use_quit="$2"
    local pid
    local attempt

    [[ -n "$GDBUS_BIN" ]] || return 0
    name_has_owner "$name" || return 0

    if [[ "$use_quit" == "yes" ]]; then
        "$GDBUS_BIN" call --session \
            --dest "$name" \
            --object-path "$DAEMON_OBJECT" \
            --method "$name.Quit" \
            >/dev/null 2>&1 || true
        wait_name_gone "$name" 3 || true
    fi

    if name_has_owner "$name"; then
        pid="$(get_owner_pid "$name" || true)"
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            for ((attempt = 0; attempt < 20; attempt++)); do
                kill -0 "$pid" 2>/dev/null || return 0
                sleep 0.1
            done
            kill -KILL "$pid" 2>/dev/null || true
        fi
    fi
}

remove_plasmoid() {
    if [[ -d "$PLASMOID_DIR" ]]; then
        if command -v "$KPKG_TOOL" >/dev/null 2>&1; then
            "$KPKG_TOOL" -t Plasma/Applet -r org.local.deskawake \
                >/dev/null 2>&1 || true
        fi
        if [[ -d "$PLASMOID_DIR" ]]; then
            rm -rf -- "$PLASMOID_DIR" 2>/dev/null || true
        fi
    fi

    if [[ -d "$PLASMOID_DIR" ]]; then
        warn "não foi possível remover o Plasmoid em \"$PLASMOID_DIR\""
        PLASMOID_FAILED=1
    fi
}

terminate_name "$DAEMON_NAME" yes
terminate_name "$UI_NAME" no
remove_plasmoid

rm -f -- "$SERVICE"
rm -f -- "$AUTOSTART_DIR/deskawake-daemon.desktop"
rm -f -- "$AUTOSTART_DIR/deskawake-widget.desktop"
rm -f -- "$BIN_DIR/deskawake"
rm -rf -- "$SHARE"
rm -rf -- "$STATE_DIR"

if ((PURGE)); then
    rm -rf -- "$CONFIG_DIR"
fi

if command -v systemd-inhibit >/dev/null 2>&1 \
    && systemd-inhibit --list 2>/dev/null | grep -qi 'DeskAwake'; then
    warn "ainda há inibição do DeskAwake; inspecione com: systemd-inhibit --list"
fi

if ((PURGE)); then
    log "configuração removida: \"$CONFIG_DIR\""
else
    log "configuração preservada: \"$CONFIG_DIR\" (use --purge para remover)"
fi

if ((PLASMOID_FAILED)); then
    warn "remoção do Plasmoid falhou; os demais arquivos foram removidos"
    exit 1
fi

log "desinstalação concluída"
