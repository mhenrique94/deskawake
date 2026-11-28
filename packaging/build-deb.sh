#!/usr/bin/env bash
set -euo pipefail
umask 022

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$REPO_ROOT"

PKG_NAME="deskawake"
ARCH="all"
EXEC_PATH="/usr/bin/deskawake"
PLASMOID_DIR="org.local.deskawake"

OUTPUT_DIR="dist"
ALLOW_DIRTY=0
STAGE=""

usage() {
    cat <<'EOF'
Uso: packaging/build-deb.sh [--output DIR] [--allow-dirty]

Gera o pacote .deb system-wide, o tarball do código-fonte e o SHA256SUMS.

  --output DIR   diretório de saída (padrão: dist/)
  --allow-dirty  permite árvore com alterações não commitadas; o tarball
                 continua sendo do commit HEAD
  --help         mostra esta ajuda

A versão vem de core.__version__ e não pode ser sobrescrita.
EOF
}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'aviso: %s\n' "$*" >&2
}

die() {
    printf 'build-deb.sh: %s\n' "$*" >&2
    exit 1
}

die_usage() {
    printf 'build-deb.sh: %s\n' "$*" >&2
    exit 2
}

cleanup() {
    if [[ -n "$STAGE" && -d "$STAGE" ]]; then
        rm -rf -- "$STAGE"
    fi
}

trap cleanup EXIT

while (($#)); do
    case "$1" in
        --output)
            [[ $# -ge 2 ]] || die_usage "--output exige um diretório"
            OUTPUT_DIR="$2"
            shift
            ;;
        --allow-dirty)
            ALLOW_DIRTY=1
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

for tool in dpkg-deb git gzip sha256sum md5sum python3; do
    command -v "$tool" >/dev/null 2>&1 || die "ferramenta ausente: $tool"
done

VERSION="$(python3 -c 'import core; print(core.__version__)')"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    die "versão inválida em core.__version__: $VERSION"
fi

PYPROJECT_VERSION="$(sed -n 's/^[[:space:]]*version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml | head -n1)"
if [[ "$PYPROJECT_VERSION" != "$VERSION" ]]; then
    die "versão divergente em pyproject.toml: $PYPROJECT_VERSION (core: $VERSION)"
fi

METADATA_VERSION="$(python3 -c 'import json, pathlib; print(json.loads(pathlib.Path("plasmoid/metadata.json").read_text(encoding="utf-8"))["KPlugin"]["Version"])')"
if [[ "$METADATA_VERSION" != "$VERSION" ]]; then
    die "versão divergente em plasmoid/metadata.json: $METADATA_VERSION (core: $VERSION)"
fi

CHANGELOG_VERSION="$(sed -n '1s/^deskawake (\([^)]*\)).*/\1/p' packaging/debian/changelog)"
if [[ "$CHANGELOG_VERSION" != "$VERSION" ]]; then
    die "versão divergente em packaging/debian/changelog: $CHANGELOG_VERSION (core: $VERSION)"
fi

if [[ -n "$(git status --porcelain)" ]]; then
    if ((ALLOW_DIRTY)); then
        warn "árvore suja: o .deb usa a árvore atual e o tarball usa o commit HEAD"
    else
        die "árvore de trabalho com alterações; faça commit ou use --allow-dirty"
    fi
fi

mkdir -p -- "$OUTPUT_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd -P)"
DEB_FILE="$OUTPUT_DIR/deskawake_${VERSION}_all.deb"
TARBALL="$OUTPUT_DIR/deskawake-${VERSION}.tar.gz"
SUMS="$OUTPUT_DIR/SHA256SUMS"

STAGE="$(mktemp -d)"
LIB_DIR="$STAGE/usr/lib/deskawake"
mkdir -p -- \
    "$STAGE/DEBIAN" \
    "$STAGE/usr/bin" \
    "$LIB_DIR/bin" \
    "$LIB_DIR/core" \
    "$LIB_DIR/ui_gtk" \
    "$LIB_DIR/assets" \
    "$STAGE/usr/share/dbus-1/services" \
    "$STAGE/etc/xdg/autostart" \
    "$STAGE/usr/share/plasma/plasmoids/$PLASMOID_DIR" \
    "$STAGE/usr/share/doc/$PKG_NAME"

cp -a -- core/. "$LIB_DIR/core/"
cp -a -- ui_gtk/. "$LIB_DIR/ui_gtk/"
cp -a -- assets/. "$LIB_DIR/assets/"
cp -a -- bin/deskawake "$LIB_DIR/bin/deskawake"
cp -a -- plasmoid/. "$STAGE/usr/share/plasma/plasmoids/$PLASMOID_DIR/"

find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" \
    \( -name '*.pyc' -o -name '*.pyo' -o -name '*.pyd' \) \
    -delete 2>/dev/null || true

find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
chmod 755 "$LIB_DIR/bin/deskawake"

ln -sfn ../lib/deskawake/bin/deskawake "$STAGE/usr/bin/deskawake"

render_template() {
    local source_file="$1"
    local target_file="$2"

    sed "s|@EXEC@|${EXEC_PATH}|g" "$source_file" >"$target_file"
    if grep -q '@EXEC@' "$target_file"; then
        die "template não renderizado: $source_file"
    fi
    chmod 644 "$target_file"
}

render_template \
    data/org.local.DeskAwake.service \
    "$STAGE/usr/share/dbus-1/services/org.local.DeskAwake.service"
render_template \
    data/deskawake-daemon.desktop \
    "$STAGE/etc/xdg/autostart/deskawake-daemon.desktop"
render_template \
    data/deskawake-widget.desktop \
    "$STAGE/etc/xdg/autostart/deskawake-widget.desktop"

install -m 644 packaging/debian/copyright \
    "$STAGE/usr/share/doc/$PKG_NAME/copyright"
gzip -9n -c packaging/debian/changelog \
    >"$STAGE/usr/share/doc/$PKG_NAME/changelog.Debian.gz"
chmod 644 "$STAGE/usr/share/doc/$PKG_NAME/changelog.Debian.gz"

INSTALLED_SIZE="$(du -sk --exclude=DEBIAN "$STAGE" | cut -f1)"
sed \
    -e "s|@VERSION@|${VERSION}|g" \
    -e "s|@INSTALLED_SIZE@|${INSTALLED_SIZE}|g" \
    packaging/debian/control.in >"$STAGE/DEBIAN/control"
chmod 644 "$STAGE/DEBIAN/control"
if grep -Eq '@[A-Z_]+@' "$STAGE/DEBIAN/control"; then
    die "placeholder não substituído em DEBIAN/control"
fi

(
    cd -- "$STAGE"
    find . -type f ! -path './DEBIAN/*' -printf '%P\n' \
        | LC_ALL=C sort \
        | while IFS= read -r file; do
            md5sum -- "$file"
        done >DEBIAN/md5sums
)
chmod 644 "$STAGE/DEBIAN/md5sums"

if [[ -z "${SOURCE_DATE_EPOCH:-}" ]]; then
    SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
fi
if [[ ! "$SOURCE_DATE_EPOCH" =~ ^[0-9]+$ ]]; then
    die "SOURCE_DATE_EPOCH inválido: $SOURCE_DATE_EPOCH"
fi
export SOURCE_DATE_EPOCH

find "$STAGE" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

dpkg-deb --build --root-owner-group -Zxz "$STAGE" "$DEB_FILE" >/dev/null
dpkg-deb --info "$DEB_FILE" >/dev/null

git archive HEAD --prefix="deskawake-${VERSION}/" | gzip -9n >"$TARBALL"

(
    cd -- "$OUTPUT_DIR"
    sha256sum "deskawake_${VERSION}_all.deb" "deskawake-${VERSION}.tar.gz" \
        >SHA256SUMS
    sha256sum -c SHA256SUMS
)

for field in Package Version Architecture Maintainer Depends Suggests; do
    field_value="$(dpkg-deb --field "$DEB_FILE" "$field")"
    [[ -n "$field_value" ]] || die "campo ausente no .deb: $field"
done

[[ "$(dpkg-deb --field "$DEB_FILE" Package)" == "$PKG_NAME" ]] \
    || die "Package inesperado no .deb"
[[ "$(dpkg-deb --field "$DEB_FILE" Version)" == "$VERSION" ]] \
    || die "Version inesperada no .deb"
[[ "$(dpkg-deb --field "$DEB_FILE" Architecture)" == "$ARCH" ]] \
    || die "Architecture inesperada no .deb"

CONTENTS="$(dpkg-deb --contents "$DEB_FILE")"
if printf '%s\n' "$CONTENTS" | grep -Eq '__pycache__|\.py[co]|tests/|data/|docs'; then
    die "artefato contém arquivos indevidos"
fi
printf '%s\n' "$CONTENTS" \
    | grep -q 'usr/bin/deskawake -> ../lib/deskawake/bin/deskawake' \
    || die "symlink /usr/bin/deskawake ausente"

for path in \
    "usr/lib/deskawake/bin/deskawake" \
    "usr/lib/deskawake/core/__init__.py" \
    "usr/lib/deskawake/ui_gtk/widget.py" \
    "usr/lib/deskawake/assets/deskawake.svg" \
    "usr/share/dbus-1/services/org.local.DeskAwake.service" \
    "etc/xdg/autostart/deskawake-daemon.desktop" \
    "etc/xdg/autostart/deskawake-widget.desktop" \
    "usr/share/plasma/plasmoids/$PLASMOID_DIR/metadata.json" \
    "usr/share/plasma/plasmoids/$PLASMOID_DIR/preview.png" \
    "usr/share/plasma/plasmoids/$PLASMOID_DIR/contents/ui/main.qml" \
    "usr/share/plasma/plasmoids/$PLASMOID_DIR/contents/ui/assets/deskawake.svg" \
    "usr/share/doc/$PKG_NAME/copyright" \
    "usr/share/doc/$PKG_NAME/changelog.Debian.gz"; do
    printf '%s\n' "$CONTENTS" | grep -q "$path" \
        || die "caminho ausente no .deb: $path"
done

log "artefatos gerados em \"$OUTPUT_DIR\":"
for file in "$DEB_FILE" "$TARBALL" "$SUMS"; do
    log "  $(basename -- "$file") ($(du -h -- "$file" | cut -f1))"
done
