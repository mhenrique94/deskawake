"""Testes estáticos do Plasmoid do Plasma 6.

A suíte é headless: lê ``metadata.json``, ``main.qml``, ``preview.png`` e os
SVGs como texto/bytes. Nenhum teste executa QML, abre display ou fala com o
barramento D-Bus; o comportamento real é validado na checklist manual no Plasma.
"""

import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PLASMOID = REPO_ROOT / "plasmoid"
METADATA = PLASMOID / "metadata.json"
MAIN_QML = PLASMOID / "contents/ui/main.qml"
ASSETS = PLASMOID / "contents/ui/assets"
PREVIEW = PLASMOID / "preview.png"

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


def _normalized() -> str:
    return re.sub(r"\s+", " ", _qml())


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


def test_main_qml_exposes_resizable_geometry():
    source = _qml()

    for prop, values in (("Width", (168, 184, 300)), ("Height", (44, 48, 84))):
        minimum, preferred, maximum = values
        for mode, value in (
            ("minimum", minimum),
            ("preferred", preferred),
            ("maximum", maximum),
        ):
            pattern = rf"Layout\.{mode}{prop}:\s*{value}\b"
            assert re.search(pattern, source), pattern

    assert "Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground" in source
    assert re.search(r"switchWidth:\s*184\b", source)
    assert re.search(r"switchHeight:\s*48\b", source)
    assert re.search(r"(?m)^\s*width:\s*124\b", source) is None
    assert re.search(r"(?m)^\s*height:\s*42\b", source) is None
    assert "pillWidth: 124" not in source
    assert "pillHeight: 42" not in source


def test_main_qml_uses_continuous_scale():
    normalized = _normalized()

    assert "function clamp(" in _qml()
    assert "Math.max(minimum, Math.min(maximum, value))" in normalized
    assert "clamp(Math.min((width - 168) / 132, (height - 44) / 40), 0, 1)" in normalized


def test_main_qml_exposes_scaled_tokens():
    normalized = _normalized()

    for token in (
        "logoSize: 22 + 12 * s",
        "namePixelSize: 10 + 4 * s",
        "toggleWidth: 32 + 8 * s",
        "toggleHeight: 18 + 4 * s",
        "knobSize: 14 + 4 * s",
        "hamburgerWidth: 14 + 2 * s",
        "hamburgerHeight: 10 + 2 * s",
        "pillPadding: 6 + 6 * s",
        "logoGap: 6 + 22 * s",
        "menuGap: 6 + 4 * s",
        "pillRadius: 12 + 6 * s",
    ):
        assert token in normalized, token


def test_main_qml_corner_mode():
    source = _qml()
    normalized = _normalized()

    for token in (
        "cornerMode: height > cornerModeHeight",
        "cornerModeHeight: 74",
        "cornerLineOffset: 10",
        "cornerMenuTopInset: 2",
        "cornerMenuRightInset: 4",
        "hitTargetSize: 24",
        "activeHamburgerWidth: cornerMode ? 16 : hamburgerWidth",
        "activeHamburgerHeight: cornerMode ? 12 : hamburgerHeight",
    ):
        assert token in normalized, token

    assert "y: root.cornerMode ? root.cornerLineOffset : 0" in normalized
    assert (
        "x: root.cornerMode ? pill.width - root.pillPadding - root.cornerMenuRightInset"
        in normalized
    )
    assert (
        "y: root.cornerMode ? root.pillPadding + root.cornerMenuTopInset" in normalized
    )
    assert "Behavior on x" in source
    assert "Behavior on y" in source


def test_main_qml_tooltip_wraps_the_pill():
    source = _qml()

    tooltip = re.search(
        r"PlasmaCore\.ToolTipArea \{\s*id: pillToolTip(.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert tooltip is not None
    body = tooltip.group(1)
    assert "anchors.fill: parent" in body
    assert "id: pill" in body
    assert "pillToolTip.containsMouse" in _qml()


def test_main_qml_tooltip_contract():
    source = _qml()

    for token in (
        "PlasmaCore.ToolTipArea",
        'mainText: "DeskAwake"',
        'subText: root.state === "error" ? root.lastError : ""',
        "textFormat: Text.PlainText",
        'active: root.state === "error"',
        "pillToolTip.containsMouse",
    ):
        assert token in source

    assert re.search(r"Plasmoid\.toolTip", source) is None


def test_main_qml_uses_theme_font():
    source = _qml()

    for token in (
        "Kirigami.Theme.defaultFont",
        "font.pixelSize: root.namePixelSize",
        "Font.DemiBold",
        "elide: Text.ElideRight",
        "color: root.inkColor",
    ):
        assert token in source

    assert re.search(r"Layout\.(?:minimum|preferred|maximum)Width:\s*58\b", source) is None


def test_main_qml_state_colors():
    found = set(re.findall(r"#[0-9A-Fa-f]{6}\b", _qml()))

    assert found == {"#80D9A4", "#929DA5", "#E47F7F", "#20252B", "#F0F3F5"}


def test_main_qml_toggle_contract():
    source = _qml()

    for token in (
        "acceptedButtons: Qt.LeftButton",
        "enabled: !root.callPending",
        "cursorShape: Qt.PointingHandCursor",
        'requestActive(root.state !== "on")',
        "root.knobSize",
        "root.toggleWidth",
        "root.toggleHeight",
        "opacity: root.callPending ? 0.6 : 1",
    ):
        assert token in source


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


def test_main_qml_hamburger_contract():
    source = _qml()

    for token in (
        "preventStealing: true",
        "hoverEnabled: true",
        'PlasmaComponents.ToolTip.text: "Opções"',
        "PlasmaComponents.ToolTip.visible: hamburgerMouse.containsMouse",
        "activeHamburgerWidth",
        "activeHamburgerHeight",
        "radius: 1",
    ):
        assert token in source

    assert source.count("height: 2") >= 3


def test_main_qml_menu_contract():
    normalized = _normalized()
    source = _qml()

    for token in (
        "PlasmaComponents.Menu",
        "PlasmaComponents.MenuItem",
        "PlasmaComponents.MenuSeparator",
        "PlasmaCore.Action",
        'Plasmoid.internalAction("configure")',
        'Plasmoid.internalAction("remove")',
        "optionsMenu.popup()",
        "text: toggleAction.text",
        "onTriggered: toggleAction.trigger()",
        "text: quitAction.text",
        "onTriggered: quitAction.trigger()",
        "enabled: !root.callPending",
    ):
        assert token in source, token

    assert "Plasmoid.contextualActions: [ toggleAction, quitAction ]" in normalized
    assert 'text: root.state === "on" ? "Desativar" : "Ativar"' in source
    assert '"Ativar"' in source
    assert '"Desativar"' in source
    assert "removeInternalAction" not in source
    assert '"Tema"' not in source
    assert '"Iniciar com o sistema"' not in source


def test_main_qml_has_no_static_toggle_label():
    source = _qml()

    assert "Ativar/Desativar" not in source


def test_main_qml_adaptive_chip_samples_wallpaper():
    source = _qml()

    for token in (
        "wallpaperGraphicsObject",
        "onWallpaperGraphicsObjectChanged",
        "sampleToken",
        "grabToImage",
        "grabSnapshot.source = result.url",
        "relativeLuminance",
        "0.2126",
        "0.7152",
        "0.0722",
        "0.42",
        "0.58",
        "Kirigami.Theme.backgroundColor",
        "Kirigami.Theme.textColor",
        "PlasmaCore.Types.Panel",
        "context.getImageData",
        "interval: 200",
    ):
        assert token in source, token

    assert "pill.mapToItem(wallpaperItem, 0, 0)" in source
    assert "grabSnapshot.wallpaperWidth" in source
    assert "const margin = 8" in source
    assert re.search(r"wallpaperGraphicsObjectChanged", source, re.IGNORECASE)


def test_main_qml_chip_contrast_guarantee():
    normalized = _normalized()

    for token in (
        "0.88",
        "0.97",
        "0.03",
        "4.5",
        "contrastRatio",
        "adjustedOpacity",
        "resolveChip",
        'candidate = candidate === "dark" ? "light" : "dark"',
        "if (luminance < 0.42)",
        "else if (luminance > 0.58)",
        "themeChipVariant",
    ):
        assert token in normalized, token


def test_main_qml_has_no_polling():
    source = _qml()

    assert "setInterval" not in source
    assert "repeat: true" not in source
    assert "Timer {" in source


def _function_body(source: str, name: str) -> str:
    start = source.index(f"function {name}")
    following = re.search(r"\n    function ", source[start + 1 :])
    end = start + 1 + following.start() if following else len(source)
    return source[start:end]


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
    assert "const newState = String(reply.value)" in body
    assert "applyState(newState)" in body
    assert 'if (newState === "error")' in body
    assert "requestLastError()" in body
    assert body.index("applyState(newState)") < body.index("requestLastError()")
    assert body.index("requestLastError()") < body.index("sendQuit()")
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
        "scheduleWallpaperSample",
        "sampleWallpaper",
        "applySample",
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


def test_main_qml_sync_does_not_cancel_pending_call():
    """A ativação D-Bus registra o serviço antes da resposta do SetActive.

    O sync disparado por ``registeredChanged`` não pode invalidar a chamada em
    voo: incrementar ``callToken`` faria o callback do SetActive ser descartado
    e ``callPending`` ficaria preso no spinner do primeiro toggle.
    """
    body = _function_body(_qml(), "syncFromDaemon")

    assert "root.callPending" in body
    assert "callToken += 1" not in body


def test_preview_png_is_valid():
    data = PREVIEW.read_bytes()

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1800, 2400)

    bit_depth = data[24]
    color_type = data[25]
    assert bit_depth == 8
    assert color_type in (2, 6)


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
        "preview.png",
        "contents/ui/main.qml",
        "contents/ui/assets/deskawake.svg",
        "contents/ui/assets/spinner.svg",
    }
