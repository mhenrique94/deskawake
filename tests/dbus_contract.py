"""Contrato D-Bus compartilhado entre testes e fakes de integração."""

from __future__ import annotations

DAEMON_NAME = "org.local.DeskAwake"
DAEMON_PATH = "/org/local/DeskAwake"
DAEMON_IFACE = "org.local.DeskAwake"

BACKEND_NAMES = {
    "fdo": "org.freedesktop.ScreenSaver",
    "mate": "org.mate.ScreenSaver",
    "gsm": "org.gnome.SessionManager",
}
BACKEND_PATHS = {
    "fdo": "/org/freedesktop/ScreenSaver",
    "mate": "/org/mate/ScreenSaver",
    "gsm": "/org/gnome/SessionManager",
}
BACKEND_IFACES = {
    "fdo": "org.freedesktop.ScreenSaver",
    "mate": "org.mate.ScreenSaver",
    "gsm": "org.gnome.SessionManager",
}

POLICYAGENT_NAME = "org.kde.Solid.PowerManagement"
POLICYAGENT_PATH = "/org/kde/Solid/PowerManagement/PolicyAgent"
POLICYAGENT_IFACE = "org.kde.Solid.PowerManagement.PolicyAgent"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

GSM_IDLE_FLAG = 8
POLICYAGENT_CHANGE_SCREEN_SETTINGS = 4
