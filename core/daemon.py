from __future__ import annotations

import logging
import logging.handlers
import os
import signal
import sys
from pathlib import Path

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

try:
    from gi.repository import GLib, GLibUnix
except ImportError:  # pragma: no cover - ambiente sem PyGObject
    from gi.repository import GLib

    GLibUnix = None

from core.environment import BACKEND_BUS_NAMES, detect_environment
from core.inhibitors import (
    POLICYAGENT_NAME,
    ScreenSaverInhibit,
    SystemdInhibit,
)
from core.state import StateMachine

DBUS_NAME = "org.local.DeskAwake"
OBJECT_PATH = "/org/local/DeskAwake"
INTERFACE = "org.local.DeskAwake"
LOG_PATH = Path("~/.local/state/deskawake/daemon.log").expanduser()
LOG_MAX_BYTES = 256 * 1024
LOG_BACKUP_COUNT = 1
VERIFY_DELAY = 6.0
DEBOUNCE = 5.0
CONFIRM_DELAY = 0.2

WATCHED_NAMES = (
    BACKEND_BUS_NAMES["fdo"],
    BACKEND_BUS_NAMES["mate"],
    BACKEND_BUS_NAMES["gsm"],
    POLICYAGENT_NAME,
)

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("deskawake.daemon")


def _setup_logging(log_path: str | Path) -> None:
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    try:
        path = Path(log_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError as exc:
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
            stream=sys.stderr,
            force=True,
        )
        logger.warning(
            "não foi possível abrir o log em %s; usando stderr: %s", log_path, exc
        )
        return
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


class _Service(dbus.service.Object):
    def __init__(self, bus, path, machine, quit_callback) -> None:
        super().__init__(bus, path)
        self._machine = machine
        self._quit_callback = quit_callback

    def _log_repeated_error(self, operation, previous_public, result):
        if result == "error" and previous_public == "error":
            logger.error(
                "%s permaneceu em error: %s",
                operation,
                self._machine.last_error,
            )

    @dbus.service.method(INTERFACE, in_signature="b", out_signature="s")
    def SetActive(self, active):
        active = bool(active)
        logger.info("SetActive(%s) solicitado", active)
        previous_public = self._machine.public_state
        if active:
            result = self._machine.activate()
        else:
            result = self._machine.deactivate()
        self._log_repeated_error(
            f"SetActive({active})", previous_public, result
        )
        logger.info("SetActive(%s) resultou em %s", active, result)
        return result

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def Toggle(self):
        previous_public = self._machine.public_state
        result = self._machine.toggle()
        self._log_repeated_error("Toggle()", previous_public, result)
        logger.info("Toggle() resultou em %s", result)
        return result

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetState(self):
        return self._machine.public_state

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetLastError(self):
        return self._machine.last_error

    @dbus.service.method(INTERFACE, in_signature="", out_signature="")
    def Quit(self):
        logger.info("Quit() solicitado")
        self._quit_callback()

    @dbus.service.signal(INTERFACE, signature="s")
    def StateChanged(self, state):
        return None


def _install_signal_handlers(handler) -> None:
    def install(signum):
        def on_signal():
            return handler(signum)

        if GLibUnix is not None:
            try:
                GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signum, on_signal)
                return
            except (AttributeError, TypeError):
                pass
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signum, on_signal)

    install(signal.SIGTERM)
    install(signal.SIGINT)


def main(
    *,
    verify_delay: float = VERIFY_DELAY,
    debounce: float = DEBOUNCE,
    confirm_delay: float = CONFIRM_DELAY,
    log_path: str | Path = LOG_PATH,
) -> int:
    _setup_logging(log_path)
    logger.info("DeskAwake daemon iniciado (pid=%s, home=%s)", os.getpid(), Path.home())

    DBusGMainLoop(set_as_default=True)
    try:
        bus = dbus.SessionBus()
    except (dbus.DBusException, OSError) as exc:
        logger.error("não foi possível conectar ao barramento de sessão: %s", exc)
        return 1
    bus.set_exit_on_disconnect(False)

    loop = GLib.MainLoop()
    systemd = SystemdInhibit(confirm_delay=confirm_delay)
    screen = ScreenSaverInhibit(
        bus, debounce=debounce, verify_delay=verify_delay
    )
    missing_services: set[str] = set()
    bus_dead = False
    service = None

    def on_state_changed(new_state: str) -> None:
        if new_state in ("on", "off"):
            missing_services.clear()
        logger.info("estado público: %s", new_state)
        if new_state == "error":
            logger.error("motivo do erro: %s", machine.last_error)
        if service is None:
            return
        try:
            service.StateChanged(new_state)
        except Exception as exc:
            logger.warning("falha ao emitir StateChanged(%s): %s", new_state, exc)

    machine = StateMachine(
        on_state_changed,
        verify_delay,
        systemd=systemd,
        screen=screen,
    )

    def finish_without_bus(reason: str) -> None:
        logger.info("%s; encerrando sem chamadas D-Bus", reason)
        machine.handle_session_end()
        GLib.idle_add(loop.quit)

    def request_quit() -> None:
        if bus_dead:
            finish_without_bus("barramento de sessão já encerrado")
            return
        try:
            machine.deactivate()
        except Exception as exc:
            logger.warning("falha ao desativar durante o encerramento: %s", exc)
        GLib.idle_add(loop.quit)

    service = _Service(bus, OBJECT_PATH, machine, request_quit)

    result = bus.request_name(DBUS_NAME, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
    if result not in (
        dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER,
        dbus.bus.REQUEST_NAME_REPLY_ALREADY_OWNER,
    ):
        logger.info("instância já ativa no barramento; encerrando esta instância")
        return 0

    def on_name_owner_changed(name, old_owner, new_owner):
        if name not in WATCHED_NAMES:
            return
        relevant = screen.relevant_names()
        if new_owner == "" and old_owner != "":
            if name not in relevant:
                logger.info("serviço não relevante desapareceu: %s", name)
                return
            missing_services.add(name)
            logger.info("serviço relevante desapareceu: %s", name)
            if (
                screen.backend == "gsm"
                and name == BACKEND_BUS_NAMES["gsm"]
                and machine.public_state == "on"
            ):
                finish_without_bus(f"sessão encerrada ({name} desapareceu)")
                return
            machine.handle_dependency_lost(f"serviço {name} desapareceu")
        elif old_owner == "" and new_owner != "":
            if name not in relevant:
                logger.info("serviço não relevante reapareceu: %s", name)
                return
            missing_services.discard(name)
            logger.info("serviço relevante reapareceu: %s", name)
            if not missing_services:
                machine.handle_dependency_returned()

    for name in WATCHED_NAMES:
        bus.add_signal_receiver(
            on_name_owner_changed,
            signal_name="NameOwnerChanged",
            dbus_interface="org.freedesktop.DBus",
            bus_name="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            arg0=name,
        )

    def on_disconnected(*_args):
        nonlocal bus_dead
        if bus_dead:
            return
        bus_dead = True
        finish_without_bus("barramento de sessão desconectado")

    bus.add_signal_receiver(
        on_disconnected,
        signal_name="Disconnected",
        dbus_interface=dbus.LOCAL_IFACE,
        path=dbus.LOCAL_PATH,
    )

    def on_signal(signum):
        logger.info("encerrando por sinal %s", signum)
        if bus_dead:
            finish_without_bus(f"sinal {signum}")
            return GLib.SOURCE_REMOVE
        try:
            machine.deactivate()
        finally:
            loop.quit()
        return GLib.SOURCE_REMOVE

    _install_signal_handlers(on_signal)

    try:
        environment = detect_environment(bus=bus)
        logger.info(
            "ambiente: desktop=%s sessão=%s backends=%s",
            environment.desktop,
            environment.session_type,
            environment.backends,
        )
    except Exception as exc:
        logger.warning("falha ao detectar o ambiente: %s", exc)

    try:
        loop.run()
    finally:
        if bus_dead:
            machine.handle_session_end()
        elif machine.public_state != "off":
            try:
                machine.deactivate()
            except Exception as exc:
                logger.warning("falha na desativação final: %s", exc)
        logger.info("DeskAwake daemon encerrado (pid=%s)", os.getpid())

    return 0
