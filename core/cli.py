from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence

import dbus
from dbus.mainloop.glib import DBusGMainLoop

from core import daemon
from core.daemon import DBUS_NAME, INTERFACE, OBJECT_PATH
from core.environment import Environment, detect_environment, is_wayland

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_UNREACHABLE = 3

PUBLIC_STATES = frozenset({"on", "off", "error"})
UI_NAME = "org.local.DeskAwake.Ui"
FORCE_UI_ENV = "DESKAWAKE_FORCE_UI"

BUS_ERRORS = (dbus.DBusException, OSError, KeyError)
CALL_ERRORS = (dbus.DBusException, OSError)

MSG_DAEMON_UNREACHABLE = "deskawake: daemon inacessível"
MSG_SESSION_BUS = "deskawake: barramento de sessão indisponível"
MSG_UI_FAILED = "deskawake: falha ao iniciar a UI"
MSG_INVALID_STATE = "deskawake: resposta inválida do daemon"
MSG_WAYLAND = (
    "deskawake: a UI GTK não é suportada em Wayland; "
    "use o Plasmoid do KDE ou repita com --force (ou DESKAWAKE_FORCE_UI=1) "
    "para depuração"
)

EPILOG = (
    "Códigos de saída:\n"
    "  status         0 = on, 1 = off ou error, 3 = daemon inacessível\n"
    "  on|off|toggle  0 = sucesso (on/off), 1 = resultado error, 3 = daemon inacessível\n"
    "  ui             0 = executou ou já havia instância, 1 = recusada ou falhou\n"
    "  daemon         código de saída do daemon (0 = saída limpa)"
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "status":
        return _run_status()
    if args.command in ("on", "off", "toggle"):
        return _run_action(args.command)
    if args.command == "daemon":
        return _daemon_main()
    if args.command == "ui":
        DBusGMainLoop(set_as_default=True)
        environment = _detect_environment()
        force = args.force or os.environ.get(FORCE_UI_ENV) == "1"
        if _wayland_blocked(environment) and not force:
            print(MSG_WAYLAND, file=sys.stderr)
            return EXIT_ERROR
        return _run_ui(ui_loader=_load_ui_main)
    raise RuntimeError(f"subcomando desconhecido: {args.command}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deskawake",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("on", "off", "toggle", "status", "daemon"):
        subparsers.add_parser(name)
    ui_parser = subparsers.add_parser("ui")
    ui_parser.add_argument("--force", action="store_true")
    return parser


def _session_bus() -> "dbus.Connection":
    return dbus.SessionBus()


def _detect_environment() -> Environment:
    return detect_environment()


def _wayland_blocked(environment: Environment) -> bool:
    return is_wayland(environment) or environment.wayland_display is not None


def _load_ui_main() -> Callable[[], object]:
    from ui_gtk.widget import main as ui_main

    return ui_main


def _daemon_main() -> int:
    return daemon.main()


def _run_status() -> int:
    try:
        bus = _session_bus()
        has_owner = bus.name_has_owner(DBUS_NAME)
    except BUS_ERRORS:
        return _status_unreachable()

    if not has_owner:
        return _status_unreachable()

    try:
        proxy = bus.get_object(DBUS_NAME, OBJECT_PATH)
        state = str(proxy.get_dbus_method("GetState", INTERFACE)())
    except CALL_ERRORS:
        return _status_unreachable()

    if state not in PUBLIC_STATES:
        print(MSG_INVALID_STATE, file=sys.stderr)
        print("off")
        return EXIT_UNREACHABLE

    print(state)
    return EXIT_OK if state == "on" else EXIT_ERROR


def _status_unreachable() -> int:
    print("off")
    print(MSG_DAEMON_UNREACHABLE, file=sys.stderr)
    return EXIT_UNREACHABLE


def _action_unreachable() -> int:
    print(MSG_DAEMON_UNREACHABLE, file=sys.stderr)
    return EXIT_UNREACHABLE


def _run_action(action: str) -> int:
    try:
        bus = _session_bus()
    except BUS_ERRORS:
        return _action_unreachable()

    try:
        proxy = bus.get_object(DBUS_NAME, OBJECT_PATH)
        if action == "toggle":
            state = str(proxy.get_dbus_method("Toggle", INTERFACE)())
        else:
            state = str(
                proxy.get_dbus_method("SetActive", INTERFACE)(
                    dbus.Boolean(action == "on")
                )
            )
    except CALL_ERRORS:
        return _action_unreachable()

    if state not in PUBLIC_STATES:
        print(MSG_INVALID_STATE, file=sys.stderr)
        return EXIT_ERROR

    print(state)
    return EXIT_ERROR if state == "error" else EXIT_OK


def _run_ui(*, ui_loader: Callable[[], Callable[[], object]]) -> int:
    try:
        bus = _session_bus()
    except BUS_ERRORS:
        print(MSG_SESSION_BUS, file=sys.stderr)
        return EXIT_ERROR

    try:
        reply = bus.request_name(UI_NAME, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
    except BUS_ERRORS as exc:
        print(f"{MSG_UI_FAILED}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if reply in (
        dbus.bus.REQUEST_NAME_REPLY_EXISTS,
        dbus.bus.REQUEST_NAME_REPLY_IN_QUEUE,
    ):
        return EXIT_OK

    if reply not in (
        dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER,
        dbus.bus.REQUEST_NAME_REPLY_ALREADY_OWNER,
    ):
        print(MSG_UI_FAILED, file=sys.stderr)
        return EXIT_ERROR

    try:
        ui_main = ui_loader()
        ui_main()
    except Exception as exc:
        print(f"{MSG_UI_FAILED}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    return EXIT_OK
