#!/usr/bin/env bash
set -euo pipefail
umask 022

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$REPO_ROOT"

IMAGE="ubuntu:24.04"

usage() {
    cat <<'EOF'
Uso: packaging/test-deb.sh [--help]

Instala, valida e remove o .deb gerado em um container Ubuntu 24.04.
O dist/ é montado somente leitura em /pkg e nada é gravado na máquina.

  --help    mostra esta ajuda

Requer docker ou podman com acesso funcional; sem engine, sai com código 2.
O pacote deve existir em dist/ (rode packaging/build-deb.sh antes).
EOF
}

log() {
    printf '%s\n' "$*"
}

die() {
    printf 'test-deb.sh: %s\n' "$*" >&2
    exit 1
}

die_usage() {
    printf 'test-deb.sh: %s\n' "$*" >&2
    exit 2
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

if command -v docker >/dev/null 2>&1; then
    ENGINE=docker
elif command -v podman >/dev/null 2>&1; then
    ENGINE=podman
else
    printf 'test-deb.sh: docker ou podman ausente; o smoke test em container é opcional fora do CI\n' >&2
    exit 2
fi

VERSION="$(python3 -c 'import core; print(core.__version__)')"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    die "versão inválida em core.__version__: $VERSION"
fi

DEB="dist/deskawake_${VERSION}_all.deb"
if [[ ! -f "$DEB" ]]; then
    die "pacote ausente: \"$DEB\"; rode packaging/build-deb.sh antes"
fi

DIST_DIR="$(cd -- "$(dirname -- "$DEB")" && pwd -P)"
PKG="$(basename -- "$DEB")"

CONTAINER_SCRIPT="$(cat <<'CONTAINER'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Como root no container a escrita de .pyc criaria __pycache__ em /usr/lib;
# na sessão real o diretório é somente leitura para o usuário.
export PYTHONDONTWRITEBYTECODE=1

fail() {
    printf 'test-deb.sh: %s\n' "$*" >&2
    exit 1
}

install_package() {
    apt-get install -y --no-install-recommends "/pkg/$PKG" procps >/dev/null
}

assert_installed() {
    local status
    local contents
    local output
    local rc
    local path
    local daemon_exec
    local widget_exec

    # Os padrões usam [d] para o texto do script não casar com o pgrep -f abaixo.
    daemon_exec='^Exec=/usr/bin/[d]eskawake daemon$'
    widget_exec='^Exec=/usr/bin/[d]eskawake ui$'

    status="$(dpkg-query -W -f='${Status}' deskawake)"
    [[ "$status" == *"install ok installed"* ]] || fail "pacote não instalado: $status"

    [[ -L /usr/bin/deskawake ]] || fail "/usr/bin/deskawake não é symlink"
    [[ "$(readlink -f /usr/bin/deskawake)" == "/usr/lib/deskawake/bin/deskawake" ]] \
        || fail "symlink de /usr/bin/deskawake incorreto"

    for path in \
        /usr/lib/deskawake/bin/deskawake \
        /usr/lib/deskawake/core/__init__.py \
        /usr/lib/deskawake/ui_gtk/widget.py \
        /usr/lib/deskawake/assets/deskawake.svg \
        /usr/share/dbus-1/services/org.local.DeskAwake.service \
        /etc/xdg/autostart/deskawake-daemon.desktop \
        /etc/xdg/autostart/deskawake-widget.desktop \
        /usr/share/plasma/plasmoids/org.local.deskawake/metadata.json \
        /usr/share/plasma/plasmoids/org.local.deskawake/preview.png \
        /usr/share/plasma/plasmoids/org.local.deskawake/contents/ui/main.qml \
        /usr/share/doc/deskawake/copyright \
        /usr/share/doc/deskawake/changelog.Debian.gz; do
        [[ -e "$path" ]] || fail "caminho ausente: $path"
    done

    grep -q "$daemon_exec" \
        /usr/share/dbus-1/services/org.local.DeskAwake.service \
        || fail "Exec do .service incorreto"
    grep -q "$daemon_exec" \
        /etc/xdg/autostart/deskawake-daemon.desktop \
        || fail "Exec do autostart do daemon incorreto"
    grep -q "$widget_exec" \
        /etc/xdg/autostart/deskawake-widget.desktop \
        || fail "Exec do autostart do widget incorreto"

    if pgrep -f '[d]eskawake daemon' >/dev/null 2>&1; then
        fail "processo iniciado durante a instalação"
    fi

    deskawake --help >/dev/null || fail "deskawake --help falhou"

    set +e
    output="$(deskawake status 2>/dev/null)"
    rc=$?
    set -e
    [[ "$rc" -eq 3 && "$output" == "off" ]] \
        || fail "status sem sessão: rc=$rc saída=$output"

    contents="$(dpkg-deb --contents "/pkg/$PKG")"
    if printf '%s\n' "$contents" | grep -Eq '__pycache__|\.py[co]|tests/|data/|docs'; then
        fail "artefato contém arquivos indevidos"
    fi
}

assert_removed() {
    local path

    for path in \
        /usr/lib/deskawake \
        /usr/bin/deskawake \
        /usr/share/dbus-1/services/org.local.DeskAwake.service \
        /etc/xdg/autostart/deskawake-daemon.desktop \
        /etc/xdg/autostart/deskawake-widget.desktop \
        /usr/share/plasma/plasmoids/org.local.deskawake; do
        [[ ! -e "$path" && ! -L "$path" ]] || fail "resíduo após a remoção: $path"
    done

    if dpkg-query -W -f='${Status}' deskawake 2>/dev/null | grep -q 'install ok installed'; then
        fail "pacote ainda reportado como instalado"
    fi
}

apt-get update >/dev/null
install_package
assert_installed
apt-get remove -y deskawake >/dev/null
assert_removed
install_package
assert_installed
apt-get remove -y deskawake >/dev/null
assert_removed
printf 'test-deb.sh: instalação e remoção validadas no container\n'
CONTAINER
)"

log "engine: $ENGINE; imagem: $IMAGE; pacote: $PKG"
"$ENGINE" run --rm \
    -e "PKG=$PKG" \
    -v "$DIST_DIR:/pkg:ro" \
    "$IMAGE" bash -c "$CONTAINER_SCRIPT"
log "smoke test concluído"
