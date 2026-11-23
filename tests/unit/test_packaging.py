"""Testes estáticos do empacotamento (.deb, artefatos e distribuição).

A suíte é headless e estática: lê arquivos como texto, usa ``bash -n`` e
``subprocess`` apenas para validar sintaxe. O build real e o container são
verificados por comandos explícitos fora do pytest.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

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


# --- Smoke test em container --------------------------------------------------


def test_test_deb_contract():
    result = _bash_syntax(PACKAGING / "test-deb.sh")

    assert result.returncode == 0, result.stderr

    source = _text(PACKAGING / "test-deb.sh")
    for token in (
        "ubuntu:24.04",
        "/pkg",
        "apt-get install",
        "--no-install-recommends",
        "procps",
        "deskawake status",
        "apt-get remove",
        "__pycache__",
        "tests/",
        "docs",
        "docker",
        "podman",
    ):
        assert token in source

    # Sem engine, o script deve sair 2 mesmo quando o pacote ainda não existe.
    assert source.index("command -v docker") < source.index('DEB="dist/deskawake_')


# --- Coexistência com a instalação per-user -----------------------------------


def _assert_system_package_detection(source: str) -> None:
    assert "system_package_installed()" in source
    assert "dpkg-query -W -f='${Status}'" in source
    assert "install ok installed" in source
    assert "/usr/lib/deskawake" in source
    assert "apt remove deskawake" in source


def test_install_script_refuses_system_package():
    source = _repo_text("install.sh")

    _assert_system_package_detection(source)
    assert "/usr/bin/deskawake" in source

    calls = [
        match.start()
        for match in re.finditer(r"(?m)^\s*refuse_system_package\s*$", source)
    ]
    assert calls, "a checagem do pacote system-wide não é chamada"
    assert calls[0] < source.index('desktop="${XDG_CURRENT_DESKTOP:-}"')
    assert re.search(r"\b(sudo|pkexec|su)\b", source) is None


def test_uninstall_script_warns_system_package():
    source = _repo_text("uninstall.sh")

    _assert_system_package_detection(source)
    assert "não é removido por este script" in source
    assert "rm -rf -- /usr" not in source
    assert "rm -rf /usr" not in source
    assert "apt-get" not in source
    assert re.search(r"\b(sudo|pkexec|su)\b", source) is None


def test_verify_script_system_fallback():
    source = _repo_text("verify.sh")

    assert "/usr/bin/deskawake" in source
    assert "/usr/share/dbus-1/services/org.local.DeskAwake.service" in source

    launcher = source.index('"$LAUNCHER"')
    share = source.index('"$SHARE/bin/deskawake"')
    system = source.index('"/usr/bin/deskawake"')
    assert launcher < share < system

    user_service = source.index('"$SERVICE"')
    system_service = source.index(
        '"/usr/share/dbus-1/services/org.local.DeskAwake.service"'
    )
    assert user_service < system_service

    assert "instalações per-user e system-wide" in source

    message = next(line for line in source.splitlines() if "não instalado" in line)
    assert "./install.sh" in message
    assert ".deb" in message


# --- Workflow de release ------------------------------------------------------


def test_workflow_contract():
    source = _text(REPO_ROOT / ".github" / "workflows" / "release.yml")

    for token in (
        'tags: ["v*"]',
        "workflow_dispatch",
        "permissions:",
        "contents: write",
        "ubuntu-latest",
        "fetch-depth: 0",
        "packaging/build-deb.sh",
        "packaging/test-deb.sh",
        "sha256sum -c SHA256SUMS",
        "gh release",
        "upload-artifact",
        "SHA256SUMS",
        "RUNNER_TEMP",
        "--notes-file",
        "GITHUB_REF_NAME",
        'test "$GITHUB_REF_NAME" = "v$VERSION"',
        "dist/deskawake_${VERSION}_all.deb",
        "dist/deskawake-${VERSION}.tar.gz",
        "dist/SHA256SUMS",
    ):
        assert token in source

    assert "gpg" not in source.lower()


# --- READMEs ------------------------------------------------------------------


@pytest.mark.parametrize("name", ("README.md", "README.en.md"))
def test_readmes_document_deb(name):
    source = _repo_text(name)

    for token in (
        ".deb",
        "deskawake_0.1.0_all.deb",
        "deskawake-0.1.0.tar.gz",
        "SHA256SUMS",
        "sha256sum -c",
        "apt install",
        "apt remove",
    ):
        assert token in source

    if name == "README.md":
        for token in (
            "atualização é manual",
            "coexist",
            "remov",
            "Rode `./uninstall.sh` antes de instalar o `.deb`",
        ):
            assert token in source
    else:
        for token in (
            "Updating is manual",
            "coexist",
            "remove",
            "run `./uninstall.sh` before installing the `.deb`",
        ):
            assert token in source
