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
    visual = REPO_ROOT / "visual" / "assets"
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
