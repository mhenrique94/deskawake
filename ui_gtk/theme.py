from __future__ import annotations

import xml.etree.ElementTree as ET

from core.config import PILL_HEIGHT, PILL_WIDTH

SYMBOL_SIZE = 22
TOGGLE_WIDTH = 32
TOGGLE_HEIGHT = 18
NAME_SLOT_WIDTH = 58
BOX_SPACING = 4
SIDE_MARGIN = 1
BORDER_WIDTH = 1
CORNER_RADIUS = 12
NAME_FONT_SIZE = 10
NAME_FONT_WEIGHT = 600

FONT_STACK = (
    '"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif'
)

STATE_COLORS = {
    "on": "#80D9A4",
    "off": "#929DA5",
    "error": "#E47F7F",
}

SURFACE = {"light": "#F0F3F5", "dark": "#20252B"}
TEXT = {"light": "#20252B", "dark": "#F0F3F5"}
BORDER_SOLID = {"light": "#C9CED3", "dark": "#3A4148"}
BORDER_COMPOSITED = {
    "light": "rgba(32, 37, 43, 0.16)",
    "dark": "rgba(240, 243, 245, 0.18)",
}
BORDER_HOVER_SOLID = {"light": "#AEB6BD", "dark": "#4A525A"}
BORDER_HOVER_COMPOSITED = {
    "light": "rgba(32, 37, 43, 0.28)",
    "dark": "rgba(240, 243, 245, 0.30)",
}
OPACITY = 0.88

SPINNER_FRAME_COUNT = 24
SPINNER_STEP_DEGREES = 15
SPINNER_INTERVAL_MS = 40
SPINNER_PERIOD_MS = SPINNER_FRAME_COUNT * SPINNER_INTERVAL_MS
SPINNER_ANGLES = tuple(
    index * SPINNER_STEP_DEGREES for index in range(SPINNER_FRAME_COUNT)
)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)


def resolve_variant(
    theme: str, gtk_theme_name: str | None, prefer_dark: bool
) -> str:
    if theme == "light":
        return "light"
    if theme == "dark":
        return "dark"
    if prefer_dark:
        return "dark"
    if gtk_theme_name and "dark" in gtk_theme_name.lower():
        return "dark"
    return "light"


def _rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_css(variant: str, composited: bool) -> str:
    if variant not in ("light", "dark"):
        raise ValueError(f"variante de tema inválida: {variant!r}")

    surface = SURFACE[variant]
    text = TEXT[variant]
    border = BORDER_SOLID[variant]
    hover = BORDER_HOVER_SOLID[variant]
    if composited:
        surface = _rgba(SURFACE[variant], OPACITY)
        border = BORDER_COMPOSITED[variant]
        hover = BORDER_HOVER_COMPOSITED[variant]
        window_background = "transparent"
    else:
        window_background = SURFACE[variant]

    return f"""
window.deskawake-window {{
    background-color: {window_background};
}}

.deskawake-pill {{
    background-color: {surface};
    border: {BORDER_WIDTH}px solid {border};
    border-radius: {CORNER_RADIUS}px;
}}

.deskawake-pill:hover {{
    border-color: {hover};
}}

.deskawake-name {{
    font-family: {FONT_STACK};
    font-size: {NAME_FONT_SIZE}px;
    font-weight: {NAME_FONT_WEIGHT};
    color: {text};
}}

switch.deskawake-switch {{
    min-width: {TOGGLE_WIDTH}px;
    min-height: {TOGGLE_HEIGHT}px;
    padding: 0;
    margin: 0;
    background-image: none;
    box-shadow: none;
    border: none;
    border-radius: 9px;
    background-color: {STATE_COLORS["off"]};
}}

switch.deskawake-switch slider {{
    min-width: 14px;
    min-height: 14px;
    padding: 0;
    margin: 1px;
    border: none;
    border-radius: 7px;
    background-image: none;
    box-shadow: none;
    background-color: {SURFACE[variant]};
}}

.deskawake-pill.state-on switch.deskawake-switch {{
    background-color: {STATE_COLORS["on"]};
}}

.deskawake-pill.state-off switch.deskawake-switch {{
    background-color: {STATE_COLORS["off"]};
}}

.deskawake-pill.state-error switch.deskawake-switch {{
    background-color: {STATE_COLORS["error"]};
}}

switch.deskawake-switch:disabled {{
    opacity: 0.6;
}}

menu.deskawake-menu {{
    font-family: {FONT_STACK};
}}
"""


def icon_color(variant: str) -> str:
    try:
        return TEXT[variant]
    except KeyError as exc:
        raise ValueError(f"variante de tema inválida: {variant!r}") from exc


def svg_with_color(svg: str, color: str) -> str:
    return svg.replace("currentColor", color)


def _is_center_dot(element: ET.Element) -> bool:
    return (
        element.tag.rsplit("}", 1)[-1] == "circle"
        and element.get("cx") == "11"
        and element.get("cy") == "11"
        and element.get("r") == "1.45"
    )


def spinner_frame(svg: str, angle: float, color: str) -> str:
    root = ET.fromstring(svg)
    dot = None
    moving = []
    for child in list(root):
        if _is_center_dot(child):
            dot = child
        else:
            moving.append(child)
        root.remove(child)

    group = ET.Element(
        f"{{{SVG_NAMESPACE}}}g",
        {"transform": f"rotate({angle:g} 11 11)"},
    )
    for child in moving:
        group.append(child)
    root.append(group)
    if dot is not None:
        root.append(dot)
    return svg_with_color(ET.tostring(root, encoding="unicode"), color)
