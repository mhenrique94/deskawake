#!/usr/bin/env bash
set -euo pipefail
umask 022

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/deskawake"
BIN_DIR="$HOME/.local/bin"
SERVICE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dbus-1/services"
AUTOSTART_DIR="$HOME/.config/autostart"
PLASMOID_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/plasma/plasmoids/org.local.deskawake"
KPKG_TOOL=${KPKG_TOOL:-kpackagetool6}

TARGET=""
INSTALL_DEPS=0
WANT_GTK=0
WANT_KDE=0
KPKG_AVAILABLE=1
STAGE=""
TEMP_FILES=()

usage() {
    cat <<'EOF'
Uso: ./install.sh [--all | --only-mate | --only-kde] [--install-deps] [--help]

Instala o DeskAwake no perfil do usuário, sem gravar fora do HOME.

  --all          instala todos os alvos disponíveis (daemon, GTK e Plasmoid)
  --only-mate    instala o daemon e a UI GTK do MATE
  --only-kde     instala o daemon e o Plasmoid do Plasma
  --install-deps mostra os comandos apt e verifica as dependências
  --help         mostra esta ajuda

Sem uma flag de alvo, o desktop é detectado por XDG_CURRENT_DESKTOP.

Exemplos:
  ./install.sh                  # detecta MATE ou KDE automaticamente
  ./install.sh --only-mate      # daemon + widget GTK
  ./install.sh --all            # instala tudo o que estiver disponível

Este instalador não requer privilégios administrativos.
EOF
}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'aviso: %s\n' "$*"
}

die() {
    printf 'install.sh: %s\n' "$*" >&2
    exit 1
}

die_usage() {
    printf 'install.sh: %s\n' "$*" >&2
    exit 2
}

cleanup() {
    local file
    for file in "${TEMP_FILES[@]}"; do
        rm -f -- "$file"
    done
    if [[ -n "$STAGE" && -d "$STAGE" ]]; then
        rm -rf -- "$STAGE"
    fi
}

trap cleanup EXIT

set_target() {
    if [[ -n "$TARGET" && "$TARGET" != "$1" ]]; then
        die_usage "flags de alvo mutuamente exclusivas"
    fi
    TARGET="$1"
}

while (($#)); do
    case "$1" in
        --all)
            set_target all
            ;;
        --only-mate)
            set_target mate
            ;;
        --only-kde)
            set_target kde
            ;;
        --install-deps)
            INSTALL_DEPS=1
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
    printf 'install.sh: HOME inválido; caminho absoluto obrigatório\n' >&2
    exit 2
fi

if [[ -n "${XDG_DATA_HOME:-}" && "$XDG_DATA_HOME" != /* ]]; then
    printf 'install.sh: XDG_DATA_HOME inválido; caminho absoluto obrigatório\n' >&2
    exit 2
fi

if [[ -z "$TARGET" && "$INSTALL_DEPS" -eq 0 ]]; then
    desktop="${XDG_CURRENT_DESKTOP:-}"
    # O Plasma expõe "KDE" ou "PLASMA" em XDG_CURRENT_DESKTOP.
    shopt -s nocasematch
    if [[ "$desktop" == *"mate"* ]]; then
        TARGET="mate"
    elif [[ "$desktop" == *"kde"* || "$desktop" == *"plasma"* ]]; then
        TARGET="kde"
    else
        shopt -u nocasematch
        die_usage "não foi possível detectar o desktop (XDG_CURRENT_DESKTOP); use --only-mate, --only-kde ou --all"
    fi
    shopt -u nocasematch
fi

case "$TARGET" in
    all)
        WANT_GTK=1
        WANT_KDE=1
        ;;
    mate)
        WANT_GTK=1
        ;;
    kde)
        WANT_KDE=1
        ;;
esac

have_command() {
    command -v "$1" >/dev/null 2>&1
}

have_python_module() {
    python3 -c "import $1" >/dev/null 2>&1
}

have_gtk() {
    python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1
}

have_kpackage_tool() {
    command -v "$KPKG_TOOL" >/dev/null 2>&1
}

kpackage_status() {
    if have_kpackage_tool; then
        printf 'ok'
    else
        printf 'ausente'
    fi
}

universal_deps_ok() {
    have_command python3 \
        && have_python_module gi \
        && have_python_module dbus \
        && have_command systemd-inhibit \
        && have_command gdbus
}

dep_status() {
    if have_command "$1"; then
        printf 'ok'
    else
        printf 'ausente'
    fi
}

module_status() {
    if have_python_module "$1"; then
        printf 'ok'
    else
        printf 'ausente'
    fi
}

print_deps() {
    printf '%s\n' "Dependências obrigatórias (runtime):"
    printf '%s\n' "  apt install python3-gi python3-dbus systemd libglib2.0-bin"
    printf '\n%s\n' "KDE (necessário apenas para o Plasmoid):"
    printf '%s\n' "  apt install kpackagetool6"
    printf '\n%s\n' "Opcional (fonte Inter):"
    printf '%s\n' "  apt install fonts-inter"
    printf '\n%s\n' "Verificação:"
    printf '  %-16s %s\n' "python3" "$(dep_status python3)"
    printf '  %-16s %s\n' "gi" "$(module_status gi)"
    printf '  %-16s %s\n' "dbus" "$(module_status dbus)"
    printf '  %-16s %s\n' "systemd-inhibit" "$(dep_status systemd-inhibit)"
    printf '  %-16s %s\n' "gdbus" "$(dep_status gdbus)"
    printf '  %-16s %s\n' "kpackagetool6" "$(kpackage_status)"
}

check_install_deps() {
    local missing=()
    local name

    have_command python3 || missing+=("python3")
    have_python_module gi || missing+=("gi")
    have_python_module dbus || missing+=("dbus")
    have_command systemd-inhibit || missing+=("systemd-inhibit")
    have_command gdbus || missing+=("gdbus")

    if ((${#missing[@]})); then
        for name in "${missing[@]}"; do
            warn "dependência ausente: $name"
        done
        die "dependência obrigatória ausente; rode ./install.sh --install-deps"
    fi

    if ((WANT_GTK)) && ! have_gtk; then
        die "dependência ausente: Gtk 3.0; rode ./install.sh --install-deps"
    fi

    if ((WANT_KDE)) && ! have_kpackage_tool; then
        if [[ "$TARGET" == "kde" ]]; then
            printf '%s\n' "alvo KDE indisponível: kpackagetool6 ausente" >&2
            exit 1
        fi
        KPKG_AVAILABLE=0
        printf '%s\n' "KDE indisponível: kpackagetool6 ausente"
    fi
}

escape_sed() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//&/\\&}"
    value="${value//|/\\|}"
    printf '%s' "$value"
}

exec_value() {
    if [[ "$SHARE/bin/deskawake" == *" "* ]]; then
        printf '"%s"' "$SHARE/bin/deskawake"
    else
        printf '%s' "$SHARE/bin/deskawake"
    fi
}

render_template() {
    local source_file="$1"
    local target_file="$2"
    local value
    local tmp

    value="$(escape_sed "$(exec_value)")"
    mkdir -p -- "$(dirname -- "$target_file")"
    tmp="$(mktemp "${target_file}.XXXXXX")"
    TEMP_FILES+=("$tmp")
    sed "s|@EXEC@|${value}|g" "$source_file" >"$tmp"
    if grep -q '@EXEC@' "$tmp"; then
        rm -f -- "$tmp"
        die "template não renderizado: $target_file"
    fi
    chmod 644 "$tmp"
    mv -- "$tmp" "$target_file"
}

write_launcher() {
    local target="$BIN_DIR/deskawake"
    local tmp
    local launcher_path
    local escaped

    mkdir -p -- "$BIN_DIR"
    tmp="$(mktemp "${target}.XXXXXX")"
    TEMP_FILES+=("$tmp")
    launcher_path="$SHARE/bin/deskawake"
    escaped=${launcher_path//\'/\'\\\'\'}
    {
        printf '#!/bin/sh\n'
        printf "exec '%s' \"\$@\"\n" "$escaped"
    } >"$tmp"
    chmod 755 "$tmp"
    mv -- "$tmp" "$target"
}

stage_share() {
    STAGE="$SHARE.new.$$"
    rm -rf -- "$STAGE"
    mkdir -p -- "$STAGE"

    cp -a -- "$REPO_DIR/core" "$STAGE/core"
    mkdir -p -- "$STAGE/bin"
    cp -a -- "$REPO_DIR/bin/deskawake" "$STAGE/bin/deskawake"
    chmod 755 "$STAGE/bin/deskawake"

    if ((WANT_GTK)); then
        cp -a -- "$REPO_DIR/ui_gtk" "$STAGE/ui_gtk"
        cp -a -- "$REPO_DIR/assets" "$STAGE/assets"
        mkdir -p -- "$STAGE/data"
        cp -a -- "$REPO_DIR/data/deskawake-widget.desktop" \
            "$STAGE/data/deskawake-widget.desktop"
    fi

    find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    find "$STAGE" \
        \( -name '*.pyc' -o -name '*.pyo' -o -name '*.pyd' \) \
        -delete 2>/dev/null || true

    rm -rf -- "$SHARE"
    mv -- "$STAGE" "$SHARE"
    STAGE=""
}

install_plasmoid() {
    local mode="-i"

    if [[ -d "$PLASMOID_DIR" ]]; then
        mode="-u"
    fi

    if "$KPKG_TOOL" -t Plasma/Applet "$mode" "$REPO_DIR/plasmoid"; then
        return 0
    fi

    if [[ "$mode" == "-u" ]]; then
        warn "atualização do Plasmoid falhou; tentando instalação limpa"
        "$KPKG_TOOL" -t Plasma/Applet -i "$REPO_DIR/plasmoid" || return 1
        return 0
    fi

    return 1
}

if ((INSTALL_DEPS)); then
    print_deps
fi

if [[ -z "$TARGET" ]]; then
    if universal_deps_ok; then
        exit 0
    fi
    exit 1
fi

check_install_deps

stage_share

write_launcher
render_template \
    "$REPO_DIR/data/org.local.DeskAwake.service" \
    "$SERVICE_DIR/org.local.DeskAwake.service"
render_template \
    "$REPO_DIR/data/deskawake-daemon.desktop" \
    "$AUTOSTART_DIR/deskawake-daemon.desktop"

if ((WANT_GTK)); then
    # O autostart do widget preserva OnlyShowIn=MATE; vindo do template.
    render_template \
        "$REPO_DIR/data/deskawake-widget.desktop" \
        "$AUTOSTART_DIR/deskawake-widget.desktop"
fi

if ((WANT_KDE && KPKG_AVAILABLE)); then
    if ! install_plasmoid; then
        die "falha ao instalar o Plasmoid: $KPKG_TOOL"
    fi
fi

if ((WANT_GTK)) && [[ "${XDG_SESSION_TYPE:-}" == "wayland" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    warn "sessão Wayland detectada: o widget GTK exige X11; no KDE use o Plasmoid"
fi

log "instalação concluída (alvo: $TARGET)"
log "código: \"$SHARE\""
log "launcher: \"$BIN_DIR/deskawake\""
log "serviço D-Bus: \"$SERVICE_DIR/org.local.DeskAwake.service\""
log "autostart do daemon: \"$AUTOSTART_DIR/deskawake-daemon.desktop\""

if ((WANT_GTK)); then
    log "autostart do widget: \"$AUTOSTART_DIR/deskawake-widget.desktop\""
fi

if ((WANT_KDE && KPKG_AVAILABLE)); then
    log "Plasmoid: \"$PLASMOID_DIR\""
fi

if ((WANT_KDE && !KPKG_AVAILABLE)); then
    log "daemon+GTK instalados; o Plasmoid não foi instalado (KDE indisponível)"
fi

if ((WANT_GTK)); then
    log "próximo passo: execute \"deskawake ui\" ou saia e entre na sessão para o autostart"
fi

if ((WANT_KDE && KPKG_AVAILABLE)); then
    log "próximo passo: adicione o DeskAwake em \"Adicionar widgets\" do Plasma"
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        warn "\"$BIN_DIR\" não está no PATH; adicione ao seu shell para usar o comando deskawake"
        ;;
esac

log "se o daemon já estiver em execução, ele continua com a versão anterior até o próximo login ou reinício"
