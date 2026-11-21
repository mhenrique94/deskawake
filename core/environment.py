from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import dbus

BACKEND_BUS_NAMES: dict[str, str] = {
    "fdo": "org.freedesktop.ScreenSaver",
    "mate": "org.mate.ScreenSaver",
    "gsm": "org.gnome.SessionManager",
    "policyagent": "org.kde.Solid.PowerManagement",
}

TOOL_NAMES: tuple[str, ...] = ("kpackagetool6", "gdbus", "systemd-inhibit")


@dataclass(frozen=True)
class Environment:
    desktop: str
    session_type: str
    wayland_display: str | None
    backends: dict[str, bool]
    tools: dict[str, bool]


def detect_environment(
    env: Mapping[str, str] | None = None,
    bus: "dbus.Connection" | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> Environment:
    source = os.environ if env is None else env
    desktop = source.get("XDG_CURRENT_DESKTOP", "")
    session_type = source.get("XDG_SESSION_TYPE", "").lower()
    wayland_display = source.get("WAYLAND_DISPLAY") or None
    backends = {name: False for name in BACKEND_BUS_NAMES}

    if bus is None:
        try:
            bus = dbus.SessionBus()
        except (dbus.DBusException, OSError, KeyError):
            bus = None

    if bus is not None:
        for name, bus_name in BACKEND_BUS_NAMES.items():
            try:
                backends[name] = bool(bus.name_has_owner(bus_name))
            except Exception:
                # Um backend indisponível não pode derrubar a detecção inteira.
                backends[name] = False

    tools = {name: which(name) is not None for name in TOOL_NAMES}
    return Environment(
        desktop=desktop,
        session_type=session_type,
        wayland_display=wayland_display,
        backends=backends,
        tools=tools,
    )


def is_wayland(env: Environment) -> bool:
    return env.session_type.lower() == "wayland"
