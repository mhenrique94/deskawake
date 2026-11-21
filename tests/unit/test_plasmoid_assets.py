"""Testes estáticos do Plasmoid do Plasma 6.

A suíte é headless: lê ``metadata.json``, ``main.qml`` e os SVGs como texto,
JSON ou XML. Nenhum teste executa QML, abre display ou fala com o barramento
D-Bus; o comportamento real é validado na checklist manual no Plasma.
"""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PLASMOID = REPO_ROOT / "plasmoid"
METADATA = PLASMOID / "metadata.json"
MAIN_QML = PLASMOID / "contents/ui/main.qml"
ASSETS = PLASMOID / "contents/ui/assets"

DESKAWAKE_SHA256 = "2c35dd2469253e0ebac24ff25f5bdd08fb0d17508c10ac98c80a09ee09fbc7d1"
SPINNER_SHA256 = "fc7746a98c78983b17cace66a975428b4febc08986168516cc6d592d53b8eb64"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def test_metadata_is_valid_json():
    assert METADATA.is_file()
    assert isinstance(_json(METADATA), dict)


def test_metadata_structure():
    metadata = _json(METADATA)

    assert metadata["KPackageStructure"] == "Plasma/Applet"
    assert metadata["KPlugin"]["Id"] == "org.local.deskawake"

    minimum = tuple(
        int(part) for part in metadata["X-Plasma-API-Minimum-Version"].split(".")
    )
    assert minimum >= (6, 4)

    assert "X-Plasma-API" not in metadata
    assert not (PLASMOID / "package").exists()


def test_metadata_required_fields():
    plugin = _json(METADATA)["KPlugin"]

    assert plugin["Name"] == "DeskAwake"
    assert plugin["License"] == "MIT"
    for field in ("Description", "Icon", "Category", "License", "Version"):
        assert plugin[field].strip()


def _qml() -> str:
    return _text(MAIN_QML)


def test_main_qml_has_no_forbidden_dependencies():
    source = _qml()

    for forbidden in (
        "Plasma5Support",
        "gdbus",
        "DataSource",
        "callBlocking",
        "setInterval",
        "config.json",
        "StartServiceByName",
        "startServiceByName",
        "Gtk",
        "GTK",
    ):
        assert forbidden not in source


def test_main_qml_uses_native_transport():
    source = _qml()

    assert "import org.kde.plasma.workspace.dbus as DBus" in source
    assert "SessionBus.asyncCall" in source
    assert "SignalWatcher {" in source
    assert "DBusServiceWatcher {" in source
    assert source.count("busType: DBus.BusType.Session") >= 2
    assert re.search(r"busType:\s*Session\b", source) is None


def test_main_qml_fixes_plasmoid_size():
    source = _qml()

    for prop, value in (("Width", 124), ("Height", 42)):
        for mode in ("minimum", "preferred", "maximum"):
            pattern = rf"Layout\.{mode}{prop}:\s*{value}\b"
            assert re.search(pattern, source), pattern

    assert "Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground" in source
    assert re.search(r"(?m)^\s*width:\s*124\b", source) is None


def test_main_qml_fixes_inner_slots():
    source = _qml()

    def count(pattern: str) -> int:
        return len(re.findall(pattern, source))

    for mode in ("minimum", "preferred", "maximum"):
        assert count(rf"Layout\.{mode}Width:\s*22\b") >= 1
        assert count(rf"Layout\.{mode}Height:\s*22\b") >= 1
        assert count(rf"Layout\.{mode}Width:\s*58\b") >= 1
        assert count(rf"Layout\.{mode}Width:\s*32\b") >= 1
        assert count(rf"Layout\.{mode}Height:\s*18\b") >= 1


def test_main_qml_keeps_pill_compact_inside_containment_cell():
    source = _qml()
    tooltip = re.search(r"PlasmaCore\.ToolTipArea \{(.*?)\n    \}", source, re.DOTALL)

    assert tooltip is not None
    body = tooltip.group(1)
    assert "anchors.centerIn: parent" in body
    assert "width: root.pillWidth" in body
    assert "height: root.pillHeight" in body
    assert "readonly property int pillWidth: 124" in source
    assert "readonly property int pillHeight: 42" in source


def _function_body(source: str, name: str) -> str:
    start = source.index(f"function {name}")
    following = re.search(r"\n    function ", source[start + 1 :])
    end = start + 1 + following.start() if following else len(source)
    return source[start:end]


def test_main_qml_uses_theme_surface():
    source = _qml()

    for token in (
        "Kirigami.Theme.backgroundColor",
        "Kirigami.Theme.textColor",
        "0.88",
        "0.18",
        "0.28",
        "pillToolTip.containsMouse",
        "radius: 12",
        "border.width: 1",
    ):
        assert token in source

    assert "#20252B" not in source
    assert "#F0F3F5" not in source


def test_main_qml_uses_theme_font():
    source = _qml()

    for token in (
        "Kirigami.Theme.defaultFont",
        "pixelSize: 10",
        "Font.DemiBold",
        "elide: Text.ElideRight",
    ):
        assert token in source


def test_main_qml_state_colors():
    found = set(re.findall(r"#[0-9A-Fa-f]{6}\b", _qml()))

    assert found == {"#80D9A4", "#929DA5", "#E47F7F"}


def test_main_qml_toggle_contract():
    source = _qml()

    for token in (
        "acceptedButtons: Qt.LeftButton",
        "enabled: !root.callPending",
        "cursorShape: Qt.PointingHandCursor",
        'requestActive(root.state !== "on")',
    ):
        assert token in source

    assert re.search(r"width:\s*14\b", source)
    assert re.search(r"height:\s*14\b", source)
    assert re.search(r"radius:\s*7\b", source)


def test_main_qml_spinner_contract():
    source = _qml()

    for token in (
        "spinner.svg",
        "RotationAnimator",
        "duration: 960",
        "easing.type: Easing.Linear",
        "loops: Animation.Infinite",
        "running: root.callPending || root.verifying",
        "visible: root.callPending || root.verifying",
    ):
        assert token in source


def test_main_qml_tooltip_contract():
    source = _qml()

    for token in (
        "PlasmaCore.ToolTipArea",
        'mainText: "DeskAwake"',
        "textFormat: Text.PlainText",
        'active: root.state === "error"',
        "pillToolTip.containsMouse",
    ):
        assert token in source

    assert re.search(r"Plasmoid\.toolTip", source) is None


def test_main_qml_menu_contract():
    source = _qml()

    for token in (
        "Plasmoid.contextualActions",
        "PlasmaCore.Action",
        '"Ativar"',
        '"Desativar"',
        '"Sair"',
        "enabled: !root.callPending",
    ):
        assert token in source

    assert "removeInternalAction" not in source
    assert '"Tema"' not in source
    assert '"Iniciar com o sistema"' not in source


def test_main_qml_dbus_contract():
    source = _qml()

    for token in (
        'member: "GetState"',
        'member: "GetLastError"',
        "verifyWindowMs: 6000",
    ):
        assert token in source

    for forbidden in ('member: "Toggle"', "Toggle()", "StartServiceByName"):
        assert forbidden not in source


def test_main_qml_set_active_contract():
    source = _qml()

    for token in ('member: "SetActive"', 'signature: "(b)"', "new DBus.bool("):
        assert token in source


def test_main_qml_verification_lifecycle():
    source = _qml()

    for token in (
        "function startVerification",
        "function stopVerification",
        "function invalidateCalls",
        "verifyTimer.restart()",
        "verifyTimer.stop()",
        "running: root.verifying",
        "interval: root.verifyWindowMs",
    ):
        assert token in source


def test_main_qml_quit_contract():
    body = _function_body(_qml(), "quitDaemon")

    assert "daemonWatcher.registered" in body
    assert "!daemonWatcher.registered || root.callPending" in body
    assert body.index("stopVerification()") < body.index('member: "Quit"')
    assert body.index('member: "SetActive"') < body.index('member: "Quit"')
    assert body.index("new DBus.bool(false)") < body.index('member: "Quit"')


def test_main_qml_state_model_contract():
    source = _qml()

    for token in (
        'property string state: "off"',
        "property string lastError",
        "property bool callPending",
        "property bool verifying",
        "property int callToken",
    ):
        assert token in source

    for name in (
        "syncFromDaemon",
        "applyState",
        "requestLastError",
        "requestActive",
        "quitDaemon",
        "startVerification",
        "stopVerification",
        "invalidateCalls",
    ):
        assert f"function {name}" in source

    assert "Component.onCompleted" in source


def test_main_qml_error_state_refreshes_last_error():
    """Heurística textual: exige o motivo ao receber StateChanged("error")."""
    handler = re.search(
        r"function dbusStateChanged\(state\) \{(.*?)\n        \}",
        _qml(),
        re.DOTALL,
    )

    assert handler is not None
    body = handler.group(1)
    assert "String(state)" in body
    assert "applyState(value)" in body
    assert 'value === "error"' in body
    assert "requestLastError()" in body


def test_main_qml_normalizes_signal_payload():
    body = _function_body(_qml(), "applyState")

    assert "String(newState)" in body
    assert 'value !== "on"' in body
    assert "root.state = value" in body


def test_main_qml_watchers_precede_getstate():
    """Heurística textual: verifica a ordem dos tokens, não a execução do QML."""
    source = _qml()

    assert source.index("SignalWatcher") < source.index("GetState")
    assert source.index("DBusServiceWatcher") < source.index("GetState")
    assert source.index("Component.onCompleted") > source.index(
        "function syncFromDaemon"
    )


def test_assets_are_valid_xml():
    for name in ("deskawake.svg", "spinner.svg"):
        path = ASSETS / name
        assert path.is_file()

        svg = ET.parse(path).getroot()
        assert svg.get("width") == "22"
        assert svg.get("height") == "22"
        assert svg.get("viewBox") == "0 0 22 22"


def test_assets_are_verbatim():
    reference = REPO_ROOT / "docs/implementation/visual/assets"
    if not reference.is_dir():
        pytest.skip("assets de referência ausentes")

    for name in ("deskawake.svg", "spinner.svg"):
        assert (ASSETS / name).read_bytes() == (reference / name).read_bytes()


def test_assets_sha256():
    expected = {
        "deskawake.svg": DESKAWAKE_SHA256,
        "spinner.svg": SPINNER_SHA256,
    }

    for name, digest in expected.items():
        assert hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() == digest


def test_package_excludes_config_and_translations():
    assert not (PLASMOID / "contents/config").exists()
    assert not list(PLASMOID.rglob("config.qml"))
    assert not (PLASMOID / "Messages.sh").exists()
    assert not (PLASMOID / "po").exists()

    files = {
        path.relative_to(PLASMOID).as_posix()
        for path in PLASMOID.rglob("*")
        if path.is_file()
    }
    assert files == {
        "metadata.json",
        "contents/ui/main.qml",
        "contents/ui/assets/deskawake.svg",
        "contents/ui/assets/spinner.svg",
    }
