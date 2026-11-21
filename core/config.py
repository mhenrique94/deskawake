from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

CONFIG_PATH = Path("~/.config/deskawake/config.json").expanduser()
CONFIG_VERSION = 1
DEFAULT_THEME = "auto"
MARGIN = 24
PILL_WIDTH = 124
PILL_HEIGHT = 42

VALID_THEMES = frozenset({"auto", "light", "dark"})

Position = tuple[int, int]
WorkArea = tuple[int, int, int, int]


def load_config() -> dict:
    path = CONFIG_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _defaults()
    except UnicodeDecodeError:
        return _quarantine(path)
    except OSError:
        return _defaults()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _quarantine(path)

    if not isinstance(data, dict) or not _has_valid_schema(data):
        return _quarantine(path)

    normalized = _normalize(data)
    if normalized != data:
        try:
            _atomic_write(path, normalized)
        except OSError:
            pass
    return normalized


def save_config(cfg: dict) -> None:
    theme = cfg.get("theme", DEFAULT_THEME)
    if not _is_valid_theme(theme):
        theme = DEFAULT_THEME

    position = _coerce_position(cfg.get("position"))
    _atomic_write(CONFIG_PATH, _config_document(theme, position))


def default_position(workareas: list[WorkArea]) -> Position:
    if not workareas:
        return MARGIN, MARGIN
    wx, wy, ww, _ = workareas[0]
    return max(wx + MARGIN, wx + ww - PILL_WIDTH - MARGIN), wy + MARGIN


def validate_position(pos: object, workareas: list[WorkArea]) -> Position:
    position = _coerce_position(pos)
    if position is None:
        return default_position(workareas)
    x, y = position
    for wx, wy, ww, wh in workareas:
        if wx <= x < wx + ww and wy <= y < wy + wh:
            return position
    return default_position(workareas)


def _defaults() -> dict:
    return _config_document(DEFAULT_THEME)


def _has_valid_schema(data: dict) -> bool:
    version = data.get("version")
    return (
        _is_int(version)
        and version == CONFIG_VERSION
        and _is_valid_theme(data.get("theme"))
    )


def _normalize(data: dict) -> dict:
    return _config_document(data["theme"], _position_from_mapping(data.get("position")))


def _config_document(theme: str, position: Position | None = None) -> dict:
    data: dict = {"version": CONFIG_VERSION, "theme": theme}
    if position is not None:
        data["position"] = {"x": position[0], "y": position[1]}
    return data


def _is_valid_theme(value: object) -> bool:
    return isinstance(value, str) and value in VALID_THEMES


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _position_from_mapping(value: object) -> tuple[int, int] | None:
    if not isinstance(value, Mapping):
        return None
    return _coerce_position(value)


def _coerce_position(value: object) -> tuple[int, int] | None:
    if isinstance(value, Mapping):
        x, y = value.get("x"), value.get("y")
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        x, y = value
    else:
        return None

    if _is_int(x) and _is_int(y):
        return x, y
    return None


def _quarantine(path: Path) -> dict:
    defaults = _defaults()
    try:
        os.replace(path, path.with_name(path.name + ".bak"))
    except OSError:
        pass
    try:
        _atomic_write(path, defaults)
    except OSError:
        pass
    return defaults


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
