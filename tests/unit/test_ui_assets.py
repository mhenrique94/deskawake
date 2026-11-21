from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "assets"


@pytest.fixture(autouse=True, scope="module")
def _isolate_ui_gtk_modules():
    yield
    for name in [
        module
        for module in sys.modules
        if module == "ui_gtk" or module.startswith("ui_gtk.")
    ]:
        del sys.modules[name]


def _state_colors():
    from ui_gtk.theme import STATE_COLORS

    return tuple(STATE_COLORS.values())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(root, name):
    return [element for element in root if _local_name(element.tag) == name]


def _parse(name: str):
    path = ASSETS / name
    assert path.is_file()
    return ET.fromstring(path.read_text(encoding="utf-8"))


def test_symbol_svg():
    path = ASSETS / "deskawake.svg"
    text = path.read_text(encoding="utf-8")
    root = _parse("deskawake.svg")
    assert root.get("width") == "22"
    assert root.get("height") == "22"
    assert root.get("viewBox") == "0 0 22 22"
    assert "currentColor" in text

    groups = _children(root, "g")
    assert len(groups) == 1
    group = groups[0]
    assert group.get("stroke") == "currentColor"
    assert group.get("stroke-linecap") == "round"
    assert len(_children(group, "path")) == 2

    circles = _children(root, "circle")
    assert len(circles) == 1
    assert circles[0].get("cx") == "11"
    assert circles[0].get("cy") == "11"
    assert circles[0].get("r") == "1.45"

    for color in _state_colors():
        assert color not in text


def test_spinner_svg():
    path = ASSETS / "spinner.svg"
    text = path.read_text(encoding="utf-8")
    root = _parse("spinner.svg")
    assert root.get("width") == "22"
    assert root.get("height") == "22"
    assert root.get("viewBox") == "0 0 22 22"
    assert "currentColor" in text

    groups = _children(root, "g")
    assert len(groups) == 1
    group = groups[0]
    assert group.get("stroke") == "currentColor"
    assert group.get("stroke-linecap") == "round"
    arcs = _children(group, "path")
    assert len(arcs) == 2
    for arc in arcs:
        assert "A" in arc.get("d", "")

    tips = _children(root, "path")
    assert len(tips) == 2
    for tip in tips:
        assert tip.get("fill") == "currentColor"
        assert tip.get("stroke") is None

    circles = _children(root, "circle")
    assert len(circles) == 1
    assert circles[0].get("cx") == "11"
    assert circles[0].get("cy") == "11"
    assert circles[0].get("r") == "1.45"

    for color in _state_colors():
        assert color not in text


@pytest.mark.parametrize("name", ["deskawake.svg", "spinner.svg"])
def test_assets_have_no_effects(name):
    text = (ASSETS / name).read_text(encoding="utf-8").lower()
    for token in (
        "filter",
        "mask",
        "lineargradient",
        "radialgradient",
        "drop-shadow",
        "font-family",
    ):
        assert token not in text


@pytest.mark.parametrize("name", ["deskawake.svg", "spinner.svg"])
def test_assets_are_verbatim(name):
    visual = REPO_ROOT / "docs" / "implementation" / "visual" / "assets"
    if not visual.is_dir():
        pytest.skip("pacote visual ausente")
    assert (ASSETS / name).read_bytes() == (visual / name).read_bytes()


@pytest.mark.parametrize("name", ["deskawake.svg", "spinner.svg"])
def test_parsed_assets_are_valid_xml(name):
    _parse(name)


def test_modules_import_headless():
    env = {**os.environ, "GDK_BACKEND": "dummy"}
    result = subprocess.run(
        [sys.executable, "-c", "import ui_gtk.widget, ui_gtk.theme"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_core_has_no_gdk():
    offenders = []
    for path in (REPO_ROOT / "core").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "Gdk" in text:
            offenders.append(path)
        for line in text.splitlines():
            if "gi.repository" in line and "Gtk" in line:
                offenders.append(path)
    assert offenders == []


WIDGET = REPO_ROOT / "ui_gtk" / "widget.py"
THEME = REPO_ROOT / "ui_gtk" / "theme.py"


def test_widget_menu_has_about_before_quit():
    source = WIDGET.read_text(encoding="utf-8")
    entries = (
        'Gtk.MenuItem(label="Ativar")',
        'Gtk.MenuItem(label="Tema")',
        'Gtk.CheckMenuItem(label="Iniciar com o sistema")',
        'Gtk.MenuItem(label="Sobre o DeskAwake…")',
        'Gtk.MenuItem(label="Sair")',
    )
    positions = [source.index(entry) for entry in entries]
    assert positions == sorted(positions)
    assert "Gtk.AboutDialog" in source
    assert "core.__version__" in source


def test_about_puts_author_in_body_and_links_repository_and_site():
    source = WIDGET.read_text(encoding="utf-8")
    assert "https://github.com/mhenrique94/deskawake" in source
    assert "Repositório no GitHub" in source
    assert "https://manivasoftware.com.br" in source
    assert "manivasoftware.com.br" in source
    assert "Gtk.LinkButton" in source
    assert "Marcelo Silva" in source
    assert "Maniva Software" in source
    assert "Licença MIT" in source
    # O nome no corpo não deve recriar o botão "Créditos" do GTK.
    assert "set_authors" not in source
    assert "set_license_type" not in source


def test_widget_does_not_use_desktop_hint():
    source = WIDGET.read_text(encoding="utf-8")
    assert "WindowTypeHint.DESKTOP" not in source
    assert "WindowTypeHint.UTILITY" in source


def test_widget_uses_documented_show_desktop_fallback():
    source = WIDGET.read_text(encoding="utf-8")
    assert "WindowTypeHint.DESKTOP" not in source
    assert "WindowTypeHint.UTILITY" in source
    # O observador de _NET_SHOWING_DESKTOP foi removido no fallback da E6.
    assert "property-notify-event" not in source
    assert "_read_showing_desktop" not in source
    assert "_desktop_gave_up" not in source


def test_widget_has_pointer_and_accessible_names():
    source = WIDGET.read_text(encoding="utf-8")
    assert "Gdk.Cursor.new_from_name" in source
    assert '"pointer"' in source
    assert "get_accessible().set_name" in source
    assert "DeskAwake: ativar/desativar" in source


def test_tooltip_and_error_helpers_use_markup():
    widget = WIDGET.read_text(encoding="utf-8")
    theme = THEME.read_text(encoding="utf-8")
    assert "set_tooltip_markup" in widget
    assert "set_tooltip_text" not in widget
    assert "format_error_tooltip" in widget
    assert "markup_escape_text" in theme
    assert "erro sem detalhes" in widget
