"""Testes estáticos dos scripts de instalação, templates e READMEs.

A suíte é headless: lê os arquivos como texto, usa ``configparser`` para os
templates e ``bash -n`` para sintaxe. Nenhum teste executa o instalador, o
daemon, a GUI ou o ``verify.sh``.
"""

from __future__ import annotations

import configparser
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data"
README_FILES = ("README.md", "README.en.md")
TEMPLATES = {
    "org.local.DeskAwake.service",
    "deskawake-daemon.desktop",
    "deskawake-widget.desktop",
}
LEGAL_LINE = (
    "Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79"
)


def _text(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _desktop(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def _script(name: str) -> str:
    return _text(name)


def _bash_syntax(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-n", str(REPO_ROOT / name)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


# --- Templates em data/ -------------------------------------------------------


def test_data_contains_only_templates():
    assert DATA.is_dir()
    names = {path.name for path in DATA.iterdir() if path.is_file()}
    assert names == TEMPLATES


def test_service_template_contract():
    parser = _desktop(DATA / "org.local.DeskAwake.service")

    assert parser.sections() == ["D-BUS Service"]
    section = parser["D-BUS Service"]
    assert section["Name"] == "org.local.DeskAwake"
    assert section["Exec"] == "@EXEC@ daemon"


def test_daemon_autostart_template_contract():
    parser = _desktop(DATA / "deskawake-daemon.desktop")

    assert parser.sections() == ["Desktop Entry"]
    entry = parser["Desktop Entry"]
    assert entry["Type"] == "Application"
    assert entry["Name"] == "DeskAwake Daemon"
    assert entry["Exec"] == "@EXEC@ daemon"
    assert entry["Terminal"] == "false"
    assert entry["NoDisplay"] == "true"
    assert entry["X-GNOME-Autostart-enabled"] == "true"


def test_widget_autostart_template_contract():
    parser = _desktop(DATA / "deskawake-widget.desktop")

    assert parser.sections() == ["Desktop Entry"]
    entry = parser["Desktop Entry"]
    assert entry["Type"] == "Application"
    assert entry["Name"] == "DeskAwake"
    assert entry["Exec"] == "@EXEC@ ui"
    assert entry["Terminal"] == "false"
    assert entry["NoDisplay"] == "true"
    assert entry["OnlyShowIn"] == "MATE;"
    assert entry["X-GNOME-Autostart-enabled"] == "true"


def test_templates_have_no_hardcoded_home():
    for name in TEMPLATES:
        assert "/home/" not in _text(f"data/{name}")


def test_desktop_templates_validate():
    tool = shutil.which("desktop-file-validate")
    if tool is None:
        pytest.skip("desktop-file-validate ausente")

    result = subprocess.run(
        [
            tool,
            str(DATA / "deskawake-daemon.desktop"),
            str(DATA / "deskawake-widget.desktop"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- install.sh: contrato estático -------------------------------------------


def test_install_script_exists_and_is_executable():
    path = REPO_ROOT / "install.sh"
    assert path.is_file()
    assert path.stat().st_mode & 0o111


def test_install_script_bash_syntax():
    assert _bash_syntax("install.sh").returncode == 0


def test_install_script_header():
    source = _script("install.sh")
    assert source.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in source
    assert "umask 022" in source


def test_install_script_has_no_privilege_escalation():
    assert re.search(r"\b(sudo|pkexec|su)\b", _script("install.sh")) is None


def test_install_script_flags_and_detection():
    source = _script("install.sh")
    for token in (
        "--all",
        "--only-mate",
        "--only-kde",
        "--install-deps",
        "--help",
        "XDG_CURRENT_DESKTOP",
        "MATE",
        "KDE",
        "PLASMA",
        "KPKG_TOOL=${KPKG_TOOL:-kpackagetool6}",
        'command -v "$KPKG_TOOL"',
    ):
        assert token in source


def test_install_script_plasmoid_contract():
    source = _script("install.sh")
    assert "-t Plasma/Applet" in source
    assert "-i" in source
    assert "-u" in source
    assert 'mode="-u"' in source
    assert re.search(r'"\$KPKG_TOOL"\s+-t\s+Plasma/Applet\s+"\$mode"', source)
    assert re.search(r'"\$KPKG_TOOL"\s+-t\s+Plasma/Applet\s+-i', source)


def test_install_script_renders_templates():
    source = _script("install.sh")
    for token in (
        "@EXEC@",
        "org.local.DeskAwake.service",
        "deskawake-daemon.desktop",
        "deskawake-widget.desktop",
        "OnlyShowIn",
        "sed",
    ):
        assert token in source


def test_install_script_exact_messages():
    source = _script("install.sh")
    assert "KDE indisponível: kpackagetool6 ausente" in source
    assert "alvo KDE indisponível: kpackagetool6 ausente" in source


def test_install_script_deps_contract():
    source = _script("install.sh")
    for token in (
        "python3-gi",
        "python3-dbus",
        "systemd",
        "libglib2.0-bin",
        "kpackagetool6",
        "fonts-inter",
        "apt install",
        "Verificação:",
    ):
        assert token in source


# --- uninstall.sh: contrato estático -----------------------------------------


def test_uninstall_script_exists_and_is_executable():
    path = REPO_ROOT / "uninstall.sh"
    assert path.is_file()
    assert path.stat().st_mode & 0o111


def test_uninstall_script_bash_syntax():
    assert _bash_syntax("uninstall.sh").returncode == 0


def test_uninstall_script_header():
    source = _script("uninstall.sh")
    assert source.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in source
    assert "umask 022" in source


def test_uninstall_script_has_no_privilege_escalation():
    assert re.search(r"\b(sudo|pkexec|su)\b", _script("uninstall.sh")) is None


def test_uninstall_script_contract():
    source = _script("uninstall.sh")
    for token in (
        "--purge",
        "--help",
        "Quit",
        "GetConnectionUnixProcessID",
        "org.local.DeskAwake.Ui",
        "-t Plasma/Applet",
        "-r",
        "org.local.deskawake",
    ):
        assert token in source
    assert (
        "$HOME/.local/state/deskawake" in source
        or "~/.local/state/deskawake" in source
    )


def test_uninstall_script_never_uses_pkill():
    assert "pkill -f" not in _script("uninstall.sh")


# --- verify.sh: contrato estático --------------------------------------------


def test_verify_script_exists_and_is_executable():
    path = REPO_ROOT / "verify.sh"
    assert path.is_file()
    assert path.stat().st_mode & 0o111


def test_verify_script_bash_syntax():
    assert _bash_syntax("verify.sh").returncode == 0


def test_verify_script_header():
    source = _script("verify.sh")
    assert source.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in source
    assert "umask 022" in source
    assert "LC_ALL=C" in source


def test_verify_script_has_no_privilege_escalation():
    assert re.search(r"\b(sudo|pkexec|su)\b", _script("verify.sh")) is None


def test_verify_script_preconditions():
    source = _script("verify.sh")
    assert "DeskAwake não instalado" in source
    assert "./install.sh" in source
    assert ".deb" in source
    assert "dependência de diagnóstico ausente:" in source
    assert "trap" in source


def test_verify_script_generic_checks():
    source = _script("verify.sh")
    for token in (
        "systemd-inhibit --list",
        "verify: OK",
        "verify: FALHOU",
        "[ok]",
        "[falha]",
    ):
        assert token in source


def test_verify_script_mate_tokens():
    source = _script("verify.sh")
    assert "GetInhibitors" in source
    assert "mate-screensaver-command" in source


def test_verify_script_kde_tokens():
    source = _script("verify.sh")
    assert "ActiveInhibitions" in source
    assert "HasInhibition" in source
    assert "KDE_POLL_SECONDS=8" in source


def test_verify_script_kde_reads_active_inhibitions_property():
    source = _script("verify.sh")
    assert "org.freedesktop.DBus.Properties.Get" in source
    assert re.search(
        r"--method org\.kde\.Solid\.PowerManagement\.PolicyAgent\.ActiveInhibitions",
        source,
    ) is None


def test_scripts_require_absolute_home_and_xdg_data_home():
    for script in ("install.sh", "uninstall.sh", "verify.sh"):
        source = _script(script)
        assert "caminho absoluto obrigatório" in source
        assert '"$HOME" != /*' in source
        assert '"$XDG_DATA_HOME" != /*' in source


def test_verify_script_never_uses_forbidden():
    source = _script("verify.sh")
    assert "CanSuspend" not in source
    assert re.search(r"IsInhibited\s*\(", source) is None


# --- READMEs, LICENSE e metadados --------------------------------------------


def test_readmes_exist_and_crosslink():
    pt = _text("README.md")
    en = _text("README.en.md")

    assert pt.startswith("# DeskAwake")
    assert en.startswith("# DeskAwake")
    assert "README.en.md" in pt
    assert "README.md" in en


@pytest.mark.parametrize("name", README_FILES)
def test_readmes_have_normative_commands(name):
    source = _text(name)
    for token in (
        "./install.sh --all",
        "./install.sh --only-mate",
        "./install.sh --only-kde",
        "./install.sh --install-deps",
        "./uninstall.sh",
        "--purge",
        "./verify.sh",
        "systemd-inhibit --list",
        "daemon.log",
        "--force",
    ):
        assert token in source


@pytest.mark.parametrize("name", README_FILES)
def test_readmes_document_limitations(name):
    source = _text(name)
    for token in (
        "kpackagetool6",
        "Wayland",
        "systemctl suspend",
        "Mint 22.3",
        "Kubuntu 26.04",
    ):
        assert token in source

    if name == "README.md":
        assert "tampa" in source
        assert "Adicionar widgets" in source
        assert "Configurar" in source
    else:
        assert "lid" in source
        assert "Add Widgets" in source
        assert "Configure" in source


@pytest.mark.parametrize("name", README_FILES)
def test_readmes_credits_and_version(name):
    source = _text(name)
    for token in (
        "Marcelo Silva",
        "Maniva Software",
        "0.1.0",
        "MIT",
        "https://manivasoftware.com.br",
        LEGAL_LINE,
    ):
        assert token in source


def test_license_has_company_and_cnpj():
    source = _text("LICENSE")
    assert "MIT" in source
    assert f"Copyright (c) 2026 {LEGAL_LINE}" in source


def test_metadata_credits():
    source = _text("plasmoid/metadata.json")
    plugin = json.loads(source)["KPlugin"]

    assert plugin["Authors"] == [{"Name": "Marcelo Silva"}]
    assert plugin["Website"] == "https://manivasoftware.com.br"
    assert plugin["BugReportUrl"] == "https://github.com/mhenrique94/deskawake/issues"
    assert LEGAL_LINE in plugin["Copyright"]
    assert "©" not in source

    for field in ("Id", "Name", "License", "Version"):
        assert field in plugin
