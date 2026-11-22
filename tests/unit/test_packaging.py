"""Testes estáticos do empacotamento (.deb, artefatos e distribuição).

A suíte é headless e estática: lê arquivos como texto, usa ``bash -n`` e
``subprocess`` apenas para validar sintaxe. O build real e o container são
verificados por comandos explícitos fora do pytest.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import core

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGING = REPO_ROOT / "packaging"
DEBIAN = PACKAGING / "debian"
MAINTAINER = "Marcelo Silva <contato@manivasoftware.com.br>"
LEGAL_LINE = (
    "Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79"
)
SPEC_MARKERS = re.compile(
    r"docs/|design_e|tasks_e|spec\.md|DELIVERY_MAP|AC-|(?<![A-Za-z0-9])T-\d"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _repo_text(name: str) -> str:
    return _text(REPO_ROOT / name)


def _bash_syntax(path: Path) -> subprocess.CompletedProcess[str]:
    _text(path)  # arquivo ausente deve falhar como FileNotFoundError
    return subprocess.run(
        ["bash", "-n", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


# --- Metadados do pacote ------------------------------------------------------


def test_control_template_contract():
    source = _text(DEBIAN / "control.in")

    assert "Package: deskawake" in source
    assert "Version: @VERSION@" in source
    assert "Architecture: all" in source
    assert f"Maintainer: {MAINTAINER}" in source
    assert "Installed-Size: @INSTALLED_SIZE@" in source

    depends = next(
        line for line in source.splitlines() if line.startswith("Depends:")
    )
    for dependency in (
        "python3 (>= 3.10)",
        "python3-gi",
        "python3-dbus",
        "gir1.2-gtk-3.0",
        "systemd",
        "libglib2.0-bin",
    ):
        assert dependency in depends

    assert "Suggests: fonts-inter" in source
    assert re.search(r"(?m)^Recommends:", source) is None
    assert "Section: utils" in source
    assert "Priority: optional" in source
    assert "Homepage: https://github.com/mhenrique94/deskawake" in source
    assert "Bugs: https://github.com/mhenrique94/deskawake/issues" in source


def test_changelog_top_version():
    lines = _text(DEBIAN / "changelog").splitlines()

    assert lines, "changelog vazio"
    assert lines[0].startswith(f"deskawake ({core.__version__}) unstable;")
    assert any(line.startswith(" -- ") and MAINTAINER in line for line in lines)


def _license_body() -> list[str]:
    lines = [line.strip() for line in _repo_text("LICENSE").splitlines() if line.strip()]
    # Remove "MIT License" e a linha de copyright.
    return lines[2:]


def _copyright_license_body(source: str) -> list[str]:
    lines = source.splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "License: MIT"
    )
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith(" "):
            content = line.strip()
            if content != ".":
                body.append(content)
        elif line.strip():
            break
    return [line for line in body if line]


def test_copyright_contract():
    source = _text(DEBIAN / "copyright")

    assert (
        "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
        in source
    )
    assert "Upstream-Name: deskawake" in source
    assert "Source: https://github.com/mhenrique94/deskawake" in source
    assert "Files: *" in source
    assert LEGAL_LINE in source
    assert "License: MIT" in source
    assert "©" not in source

    body = _copyright_license_body(source)
    assert body, "bloco MIT ausente"
    assert body[0].startswith("Permission is hereby granted")
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in source
    assert body == _license_body()


def test_no_maintainer_scripts():
    for name in ("postinst", "prerm", "postrm"):
        assert not (DEBIAN / name).exists()

    source = _text(PACKAGING / "build-deb.sh")
    for token in ("DEBIAN/postinst", "DEBIAN/prerm", "DEBIAN/postrm"):
        assert token not in source


def test_gitignore_excludes_dist():
    lines = {line.strip() for line in _repo_text(".gitignore").splitlines()}
    assert "dist/" in lines


def test_packaging_has_no_spec_paths():
    assert PACKAGING.is_dir()

    files = [path for path in PACKAGING.rglob("*") if path.is_file()]
    assert files, "packaging/ vazio"

    for path in files:
        assert SPEC_MARKERS.search(_text(path)) is None, path


# --- Build do .deb ------------------------------------------------------------


def test_build_script_syntax():
    result = _bash_syntax(PACKAGING / "build-deb.sh")

    assert result.returncode == 0, result.stderr


def test_build_script_contract():
    source = _text(PACKAGING / "build-deb.sh")

    for token in (
        "dpkg-deb --build",
        "--root-owner-group",
        "-Zxz",
        "SOURCE_DATE_EPOCH",
        "git archive",
        "gzip -9n",
        "sha256sum",
        "__pycache__",
        "@EXEC@",
        "pyproject.toml",
        "plasmoid/metadata.json",
        "packaging/debian/changelog",
    ):
        assert token in source

    for forbidden in ("sudo", "debhelper", "fpm"):
        assert forbidden not in source


def test_build_artifacts_names():
    source = _text(PACKAGING / "build-deb.sh")

    assert "deskawake_${VERSION}_all.deb" in source
    assert "deskawake-${VERSION}.tar.gz" in source
    assert "SHA256SUMS" in source

