from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import pytest

from core.config import PILL_HEIGHT, PILL_WIDTH


@pytest.fixture(autouse=True, scope="module")
def _isolate_ui_gtk_modules():
    yield
    for name in [
        module
        for module in sys.modules
        if module == "ui_gtk" or module.startswith("ui_gtk.")
    ]:
        del sys.modules[name]


class _ThemeProxy:
    __test__ = False

    def __getattr__(self, name):
        # Importa ui_gtk só na execução para não poluir sys.modules na coleta.
        if name.startswith("_") or name.startswith("__"):
            raise AttributeError(name)
        from ui_gtk import theme

        return getattr(theme, name)


theme = _ThemeProxy()


def test_theme_constants():
    assert theme.PILL_WIDTH == PILL_WIDTH
    assert theme.PILL_HEIGHT == PILL_HEIGHT
    assert theme.SYMBOL_SIZE == 22
    assert theme.TOGGLE_WIDTH == 32
    assert theme.TOGGLE_HEIGHT == 18
    assert theme.NAME_SLOT_WIDTH == 58
    assert theme.BOX_SPACING == 4
    assert theme.SIDE_MARGIN == 1
    assert theme.BORDER_WIDTH == 1
    assert theme.CORNER_RADIUS == 12
    assert theme.NAME_FONT_SIZE == 10
    assert theme.NAME_FONT_WEIGHT == 600
    assert theme.FONT_STACK == (
        '"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif'
    )
    assert theme.STATE_COLORS == {
        "on": "#80D9A4",
        "off": "#929DA5",
        "error": "#E47F7F",
    }
    assert theme.SURFACE == {"light": "#F0F3F5", "dark": "#20252B"}
    assert theme.TEXT == {"light": "#20252B", "dark": "#F0F3F5"}
    assert theme.BORDER_SOLID == {"light": "#C9CED3", "dark": "#3A4148"}
    assert theme.BORDER_COMPOSITED == {
        "light": "rgba(32, 37, 43, 0.16)",
        "dark": "rgba(240, 243, 245, 0.18)",
    }
    assert theme.BORDER_HOVER_SOLID == {"light": "#AEB6BD", "dark": "#4A525A"}
    assert theme.BORDER_HOVER_COMPOSITED == {
        "light": "rgba(32, 37, 43, 0.28)",
        "dark": "rgba(240, 243, 245, 0.30)",
    }
    assert theme.OPACITY == 0.88
    assert theme.KNOB_COLOR == "#20252B"
    assert theme.KNOB_BORDER == "rgba(255, 255, 255, 0.14)"
    assert theme.SWITCH_HOVER_ALPHA == 0.28
    assert theme.SWITCH_ACTIVE_ALPHA == 0.34


def test_resolve_variant_dark_name():
    assert theme.resolve_variant("auto", "Mint-Y-Dark", False) == "dark"


def test_resolve_variant_dark_case_insensitive():
    assert theme.resolve_variant("auto", "my-darkish", False) == "dark"


def test_resolve_variant_prefer_dark():
    assert theme.resolve_variant("auto", "Mint-Y", True) == "dark"


def test_resolve_variant_forced_light():
    assert theme.resolve_variant("light", "Mint-Y-Dark", True) == "light"


def test_resolve_variant_forced_dark():
    assert theme.resolve_variant("dark", "Mint-Y", False) == "dark"


def test_resolve_variant_auto_light():
    assert theme.resolve_variant("auto", "Mint-Y", False) == "light"
    assert theme.resolve_variant("auto", None, False) == "light"
    assert theme.resolve_variant("auto", "", False) == "light"


def test_resolve_variant_invalid_theme_falls_back_to_auto():
    assert theme.resolve_variant("sepia", "Mint-Y-Dark", False) == "dark"
    assert theme.resolve_variant("sepia", "Mint-Y", False) == "light"


@pytest.mark.parametrize("variant", ["light", "dark"])
@pytest.mark.parametrize("composited", [True, False])
def test_css_has_no_font_face(variant, composited):
    assert "@font-face" not in theme.build_css(variant, composited)


def test_css_font_stack():
    css = theme.build_css("light", True)
    assert theme.FONT_STACK in css
    assert theme.FONT_STACK.rstrip().endswith("sans-serif")


@pytest.mark.parametrize("variant", ["light", "dark"])
@pytest.mark.parametrize("composited", [True, False])
def test_css_does_not_touch_prefer_dark(variant, composited):
    assert (
        "gtk-application-prefer-dark-theme"
        not in theme.build_css(variant, composited)
    )


def test_css_state_colors():
    css = theme.build_css("dark", True)
    assert "#80D9A4" in css
    assert "#929DA5" in css
    assert "#E47F7F" in css


def test_css_variants():
    light = theme.build_css("light", False)
    dark = theme.build_css("dark", False)
    assert "#F0F3F5" in light
    assert "#20252B" in light
    assert "#20252B" in dark
    assert "#F0F3F5" in dark
    for css in (light, dark):
        assert "10px" in css
        assert "600" in css
        assert "32px" in css
        assert "18px" in css
        assert "14px" in css
        assert "12px" in css


def test_css_non_composited_is_opaque():
    for variant in ("light", "dark"):
        css = theme.build_css(variant, False)
        assert "background-color: rgba(" not in css
        assert theme.SURFACE[variant] in css
        assert theme.BORDER_SOLID[variant] in css


def test_css_composited_is_translucent():
    light = theme.build_css("light", True)
    dark = theme.build_css("dark", True)
    assert "rgba(240, 243, 245, 0.88)" in light
    assert "rgba(32, 37, 43, 0.88)" in dark
    assert theme.BORDER_COMPOSITED["light"] in light
    assert theme.BORDER_COMPOSITED["dark"] in dark


def test_css_invalid_variant_raises():
    with pytest.raises(ValueError):
        theme.build_css("sepia", True)


def _css_block(css: str, selector: str) -> str:
    start = css.index(f"{selector} {{")
    return css[start : css.index("}", start) + 1]


def test_css_switch_knob_does_not_depend_on_variant():
    light = _css_block(
        theme.build_css("light", False), "switch.deskawake-switch slider"
    )
    dark = _css_block(
        theme.build_css("dark", False), "switch.deskawake-switch slider"
    )
    assert light == dark
    assert f"background-color: {theme.KNOB_COLOR};" in light
    assert theme.KNOB_BORDER in light
    # A borda do knob não pode alterar a métrica do switch (32 px): o realce
    # usa box-shadow e o conteúdo permanece com 14 px.
    assert "border: none;" in light
    assert "min-width: 14px;" in light


def test_css_switch_hover_and_pressed():
    css = theme.build_css("light", False)
    hover = _css_block(css, "switch.deskawake-switch:hover")
    active = _css_block(css, "switch.deskawake-switch:active")
    assert f"rgba(255, 255, 255, {theme.SWITCH_HOVER_ALPHA})" in hover
    assert f"rgba(255, 255, 255, {theme.SWITCH_ACTIVE_ALPHA})" in active


def test_format_error_tooltip_empty():
    assert theme.format_error_tooltip("") == ""
    assert theme.format_error_tooltip("   ") == ""


def test_format_error_tooltip_strips_reason():
    assert theme.format_error_tooltip("  motivo  ") == "<b>DeskAwake</b>\nmotivo"


def test_format_error_tooltip_escapes_reason():
    markup = theme.format_error_tooltip('falha <backend> & "tela"')
    assert markup.startswith("<b>DeskAwake</b>\n")
    assert "<backend>" not in markup
    assert "&lt;backend&gt;" in markup
    assert "&amp;" in markup
    assert "&quot;" in markup


def test_css_menu_uses_font_stack():
    css = theme.build_css("light", True)
    start = css.index(".deskawake-menu")
    block = css[start : css.index("}", start) + 1]
    assert theme.FONT_STACK in block
    assert "font-size" not in block


def test_icon_color():
    assert theme.icon_color("light") == theme.TEXT["light"]
    assert theme.icon_color("dark") == theme.TEXT["dark"]
    for variant in ("light", "dark"):
        assert theme.icon_color(variant) not in theme.STATE_COLORS.values()
    with pytest.raises(ValueError):
        theme.icon_color("sepia")


def test_svg_with_color():
    svg = (
        '<svg><g stroke="currentColor"><path fill="currentColor"/></g>'
        '<circle cx="11" cy="11" r="1.45" fill="#123456"/></svg>'
    )
    colored = theme.svg_with_color(svg, "#ABCDEF")
    assert colored.count("#ABCDEF") == 2
    assert "currentColor" not in colored
    assert "#123456" in colored
    assert theme.svg_with_color("sem cor", "#ABCDEF") == "sem cor"


def test_svg_with_color_uses_state_neutral_color():
    svg = '<svg><path stroke="currentColor"/></svg>'
    for variant in ("light", "dark"):
        colored = theme.svg_with_color(svg, theme.icon_color(variant))
        for state_color in theme.STATE_COLORS.values():
            assert state_color not in colored


SPINNER_SAMPLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" '
    'viewBox="0 0 22 22">\n'
    '  <g fill="none" stroke="currentColor" stroke-width="2.2">\n'
    '    <path d="M 15.2394,17.7844 A 8.0 8.0 0 0 1 3.1960,9.2399"/>\n'
    '    <path d="M 6.7606,4.2156 A 8.0 8.0 0 0 1 18.8040,12.7601"/>\n'
    "  </g>\n"
    '  <path d="M 1.3426,8.8218 L 3.8121,6.5085 L 5.0495,9.6579 Z" '
    'fill="currentColor"/>\n'
    '  <path d="M 20.6574,13.1782 L 18.1879,15.4915 L 16.9505,12.3421 Z" '
    'fill="currentColor"/>\n'
    '  <circle cx="11" cy="11" r="1.45" fill="currentColor"/>\n'
    "</svg>"
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _rotation_group(root):
    for child in root:
        if _local_name(child.tag) == "g" and child.get("transform"):
            return child
    raise AssertionError("grupo rotacionado não encontrado")


def test_spinner_animation_contract():
    assert theme.SPINNER_FRAME_COUNT == 24
    assert theme.SPINNER_STEP_DEGREES == 15
    assert theme.SPINNER_INTERVAL_MS == 40
    assert theme.SPINNER_PERIOD_MS == 960
    assert theme.SPINNER_ANGLES == tuple(range(0, 360, 15))


def test_spinner_frame_rotation():
    for angle in theme.SPINNER_ANGLES:
        colored = theme.spinner_frame(SPINNER_SAMPLE, angle, "#20252B")
        root = ET.fromstring(colored)
        assert root.get("viewBox") == "0 0 22 22"
        transform = _rotation_group(root).get("transform")
        assert transform.startswith(f"rotate({angle}")
        assert transform.endswith(" 11 11)")


def test_spinner_frame_keeps_dot_static():
    for angle in theme.SPINNER_ANGLES:
        colored = theme.spinner_frame(SPINNER_SAMPLE, angle, "#20252B")
        root = ET.fromstring(colored)
        group = _rotation_group(root)
        assert [
            element
            for element in group.iter()
            if _local_name(element.tag) == "circle"
        ] == []
        circles = [
            element
            for element in root
            if _local_name(element.tag) == "circle"
        ]
        assert len(circles) == 1
        circle = circles[0]
        assert circle.get("cx") == "11"
        assert circle.get("cy") == "11"
        assert circle.get("r") == "1.45"


def test_spinner_frame_applies_variant_color():
    for angle in theme.SPINNER_ANGLES:
        colored = theme.spinner_frame(SPINNER_SAMPLE, angle, "#F0F3F5")
        assert "currentColor" not in colored
        assert "#F0F3F5" in colored
        for state_color in theme.STATE_COLORS.values():
            assert state_color not in colored


def test_spinner_frame_does_not_mutate_source():
    source = SPINNER_SAMPLE
    theme.spinner_frame(source, 90, "#20252B")
    assert source == SPINNER_SAMPLE
