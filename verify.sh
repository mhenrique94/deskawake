#!/usr/bin/env bash
set -euo pipefail
umask 022
export LC_ALL=C

SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/deskawake"
LAUNCHER="$HOME/.local/bin/deskawake"
SERVICE="${XDG_DATA_HOME:-$HOME/.local/share}/dbus-1/services/org.local.DeskAwake.service"
DESKTOP="${XDG_CURRENT_DESKTOP:-}"
KDE_POLL_SECONDS=8
MATE_POLL_SECONDS=3
SYSTEMD_POLL_SECONDS=3

FAILURES=0
LAST_OUTPUT=""
LAST_RC=0

usage() {
    cat <<'EOF'
Uso: ./verify.sh [--help]

Liga o DeskAwake, confere o estado D-Bus, o systemd-inhibit e o backend do
desktop, e desliga no final. O script sempre termina com o DeskAwake OFF.

  --help    mostra esta ajuda
EOF
}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'aviso: %s\n' "$*"
}

fail() {
    printf 'verify.sh: %s\n' "$*" >&2
    exit 1
}

die_usage() {
    printf 'verify.sh: %s\n' "$*" >&2
    exit 2
}

check_ok() {
    printf '[ok] %s\n' "$*"
}

check_fail() {
    printf '[falha] %s\n' "$*"
    FAILURES=$((FAILURES + 1))
}

while (($#)); do
    case "$1" in
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

if [[ -x "$LAUNCHER" ]]; then
    DESKAWAKE="$LAUNCHER"
elif [[ -x "$SHARE/bin/deskawake" ]]; then
    DESKAWAKE="$SHARE/bin/deskawake"
else
    fail "DeskAwake não instalado; rode ./install.sh"
fi

if [[ ! -f "$SERVICE" ]]; then
    fail "DeskAwake não instalado; rode ./install.sh"
fi

for tool in gdbus systemd-inhibit; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        fail "dependência de diagnóstico ausente: $tool"
    fi
done

cleanup() {
    "$DESKAWAKE" off >/dev/null 2>&1 || true
}

trap 'cleanup' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

capture_action() {
    local action="$1"
    local output
    local rc

    set +e
    output=$("$DESKAWAKE" "$action" 2>/dev/null)
    rc=$?
    set -e
    LAST_OUTPUT="$output"
    LAST_RC="$rc"
}

systemd_has_deskawake() {
    systemd-inhibit --list 2>/dev/null | grep -qi 'DeskAwake'
}

mate_get_inhibitors() {
    gdbus call --session \
        --dest org.mate.ScreenSaver \
        --object-path /org/mate/ScreenSaver \
        --method org.mate.ScreenSaver.GetInhibitors \
        2>/dev/null || true
}

kde_active_inhibitions() {
    gdbus call --session \
        --dest org.kde.Solid.PowerManagement \
        --object-path /org/kde/Solid/PowerManagement/PolicyAgent \
        --method org.freedesktop.DBus.Properties.Get \
        org.kde.Solid.PowerManagement.PolicyAgent \
        ActiveInhibitions \
        2>/dev/null || true
}

kde_has_inhibition() {
    gdbus call --session \
        --dest org.kde.Solid.PowerManagement \
        --object-path /org/kde/Solid/PowerManagement/PolicyAgent \
        --method org.kde.Solid.PowerManagement.PolicyAgent.HasInhibition 4 \
        2>/dev/null || true
}

check_mate_on() {
    local output=""
    local attempt

    for ((attempt = 0; attempt < MATE_POLL_SECONDS * 10; attempt++)); do
        output="$(mate_get_inhibitors)"
        if printf '%s' "$output" | grep -qi 'deskawake'; then
            break
        fi
        sleep 0.1
    done

    if printf '%s' "$output" | grep -qi 'deskawake'; then
        check_ok "GetInhibitors contém deskawake"
    else
        check_fail "GetInhibitors contém deskawake"
    fi

    if command -v mate-screensaver-command >/dev/null 2>&1; then
        output="$(mate-screensaver-command -q 2>/dev/null || true)"
        if printf '%s' "$output" | grep -qiE 'deskawake|inibida'; then
            check_ok "mate-screensaver-command -q lista o DeskAwake"
        else
            check_fail "mate-screensaver-command -q lista o DeskAwake"
        fi
    fi
}

check_mate_off() {
    local output=""
    local attempt

    for ((attempt = 0; attempt < MATE_POLL_SECONDS * 10; attempt++)); do
        output="$(mate_get_inhibitors)"
        if ! printf '%s' "$output" | grep -qi 'deskawake'; then
            break
        fi
        sleep 0.1
    done

    if printf '%s' "$output" | grep -qi 'deskawake'; then
        check_fail "GetInhibitors liberou deskawake"
    else
        check_ok "GetInhibitors liberou deskawake"
    fi

    if command -v mate-screensaver-command >/dev/null 2>&1; then
        output="$(mate-screensaver-command -q 2>/dev/null || true)"
        if printf '%s' "$output" | grep -qi 'deskawake'; then
            check_fail "mate-screensaver-command -q sem deskawake"
        else
            check_ok "mate-screensaver-command -q sem deskawake"
        fi
    fi
}

check_kde_on() {
    local output=""
    local attempt

    for ((attempt = 0; attempt < KDE_POLL_SECONDS * 10; attempt++)); do
        output="$(kde_active_inhibitions)"
        if printf '%s' "$output" | grep -qi 'deskawake' \
            && printf '%s' "$output" | grep -qi 'DeskAwake active'; then
            break
        fi
        sleep 0.1
    done

    if printf '%s' "$output" | grep -qi 'deskawake' \
        && printf '%s' "$output" | grep -qi 'DeskAwake active'; then
        check_ok "ActiveInhibitions contém deskawake / DeskAwake active"
    else
        check_fail "ActiveInhibitions contém deskawake / DeskAwake active"
    fi

    output="$(kde_has_inhibition)"
    if printf '%s' "$output" | grep -qi 'true'; then
        check_ok "HasInhibition(4) = true"
    else
        check_fail "HasInhibition(4) = true"
    fi
}

check_kde_off() {
    local output=""
    local attempt

    for ((attempt = 0; attempt < KDE_POLL_SECONDS * 10; attempt++)); do
        output="$(kde_active_inhibitions)"
        if ! printf '%s' "$output" | grep -qi 'deskawake'; then
            break
        fi
        sleep 0.1
    done

    if printf '%s' "$output" | grep -qi 'deskawake'; then
        check_fail "ActiveInhibitions liberou deskawake"
    else
        check_ok "ActiveInhibitions liberou deskawake"
    fi

    output="$(kde_has_inhibition)"
    log "informativo: HasInhibition(4) = $output"
}

capture_action off

capture_action on
if [[ "$LAST_RC" -eq 0 && "$LAST_OUTPUT" == "on" ]]; then
    check_ok "daemon respondeu on"
else
    check_fail "daemon respondeu on"
fi

if systemd_has_deskawake; then
    check_ok "systemd-inhibit contém DeskAwake"
else
    check_fail "systemd-inhibit contém DeskAwake"
fi

capture_action status
if [[ "$LAST_RC" -eq 0 && "$LAST_OUTPUT" == "on" ]]; then
    check_ok "status = on"
else
    check_fail "status = on"
fi

shopt -s nocasematch
if [[ "$DESKTOP" == *"mate"* ]]; then
    check_mate_on
elif [[ "$DESKTOP" == *"kde"* || "$DESKTOP" == *"plasma"* ]]; then
    check_kde_on
else
    warn "desktop desconhecido: executando apenas as checagens genéricas"
fi
shopt -u nocasematch

capture_action off
if [[ "$LAST_RC" -eq 0 && "$LAST_OUTPUT" == "off" ]]; then
    check_ok "daemon respondeu off"
else
    check_fail "daemon respondeu off"
fi

for ((attempt = 0; attempt < SYSTEMD_POLL_SECONDS * 10; attempt++)); do
    systemd_has_deskawake || break
    sleep 0.1
done

if systemd_has_deskawake; then
    check_fail "sem systemd-inhibit órfão"
else
    check_ok "sem systemd-inhibit órfão"
fi

capture_action status
if [[ "$LAST_RC" -eq 1 && "$LAST_OUTPUT" == "off" ]]; then
    check_ok "status = off"
else
    check_fail "status = off"
fi

shopt -s nocasematch
if [[ "$DESKTOP" == *"mate"* ]]; then
    check_mate_off
elif [[ "$DESKTOP" == *"kde"* || "$DESKTOP" == *"plasma"* ]]; then
    check_kde_off
fi
shopt -u nocasematch

if ((FAILURES == 0)); then
    log "verify: OK"
    exit 0
fi

log "verify: FALHOU"
exit 1
