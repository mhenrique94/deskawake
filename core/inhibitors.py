from __future__ import annotations

import ctypes
import logging
import os
import signal
import subprocess
import time

import dbus

from core.environment import BACKEND_BUS_NAMES

logger = logging.getLogger(__name__)

BACKENDS = ("fdo", "mate", "gsm")

POLICYAGENT_NAME = BACKEND_BUS_NAMES["policyagent"]
POLICYAGENT_PATH = "/org/kde/Solid/PowerManagement/PolicyAgent"
POLICYAGENT_IFACE = "org.kde.Solid.PowerManagement.PolicyAgent"
GSM_IDLE_FLAG = 8
POLICYAGENT_CHANGE_SCREEN_SETTINGS = 4
POLICYAGENT_ACTIVE_MASK = 3

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

# Erros que significam "o mecanismo não existe", não falha de transporte.
_UNKNOWN_ERRORS = frozenset(
    {
        "org.freedesktop.DBus.Error.UnknownMethod",
        "org.freedesktop.DBus.Error.UnknownInterface",
        "org.freedesktop.DBus.Error.UnknownProperty",
        "org.freedesktop.DBus.Error.InvalidArgs",
    }
)


class InhibitError(RuntimeError):
    """Falha ao iniciar ou manter um inibidor."""


def _pdeathsig() -> None:
    """Mata o filho quando o daemon morrer (executado antes do exec)."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    except Exception:
        pass
    if os.getppid() == 1:
        os._exit(1)


def _is_unknown_error(exc: BaseException) -> bool:
    get_name = getattr(exc, "get_dbus_name", None)
    if get_name is None:
        return False
    try:
        return get_name() in _UNKNOWN_ERRORS
    except Exception:
        return False


class SystemdInhibit:
    """Backstop de ociosidade via `systemd-inhibit --what=idle`."""

    def __init__(
        self,
        reason: str = "DeskAwake active",
        who: str = "DeskAwake",
        confirm_delay: float = 0.2,
    ) -> None:
        self.reason = reason
        self.who = who
        self.confirm_delay = confirm_delay
        self._proc: subprocess.Popen | None = None

    def _build_command(self) -> list[str]:
        return [
            "systemd-inhibit",
            "--what=idle",
            "--mode=block",
            f"--who={self.who}",
            f"--why={self.reason}",
            "sleep",
            "infinity",
        ]

    def start(self) -> None:
        if self.alive:
            return
        if self._proc is not None:
            self.stop()

        try:
            proc = subprocess.Popen(
                self._build_command(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,
                preexec_fn=_pdeathsig,
            )
        except (FileNotFoundError, OSError) as exc:
            raise InhibitError(
                f"não foi possível iniciar o systemd-inhibit: {exc}"
            ) from exc

        if self.confirm_delay:
            time.sleep(self.confirm_delay)

        exit_code = proc.poll()
        if exit_code is not None:
            stderr = b""
            try:
                try:
                    _, stderr = proc.communicate(timeout=1)
                except TypeError:
                    _, stderr = proc.communicate()
                except subprocess.TimeoutExpired:
                    pass
            finally:
                self._close_pipe(proc)
            detail = stderr.decode(errors="replace").strip() if stderr else ""
            if detail:
                raise InhibitError(f"systemd-inhibit encerrou: {detail}")
            raise InhibitError(
                f"systemd-inhibit encerrou com código {exit_code} antes de inibir"
            )

        self._proc = proc

    def stop(self) -> None:
        proc = self._proc
        if proc is None:
            return

        try:
            if proc.poll() is None:
                self._killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._killpg(proc.pid, signal.SIGKILL)
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            else:
                try:
                    proc.wait(timeout=2)
                except (subprocess.TimeoutExpired, ChildProcessError):
                    pass
        finally:
            self._close_pipe(proc)
            self._proc = None

    @staticmethod
    def _killpg(pid: int, sig: int) -> None:
        try:
            os.killpg(pid, sig)
        except (ProcessLookupError, PermissionError):
            pass

    @staticmethod
    def _close_pipe(proc) -> None:
        stream = getattr(proc, "stderr", None)
        if stream is None:
            return
        try:
            stream.close()
        except Exception:
            pass

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None


class ScreenSaverInhibit:
    """Inibidor de tela na cadeia FDO -> MATE -> GSM, na conexão recebida."""

    def __init__(
        self,
        bus,
        *,
        who: str = "deskawake",
        why: str = "DeskAwake active",
        debounce: float = 5.0,
        verify_delay: float = 6.0,
    ) -> None:
        self._bus = bus
        self.who = who
        self.why = why
        self.debounce = debounce
        self.verify_delay = verify_delay
        self.backend: str | None = None
        self.path: str | None = None
        self.cookie: int | None = None
        self._acquired_at: float = 0.0

    def acquire(self) -> None:
        if self.cookie is not None:
            self.release()
        self.backend = None
        self.path = None
        self.cookie = None
        self._acquired_at = 0.0
        reasons: list[str] = []

        for backend in BACKENDS:
            name = BACKEND_BUS_NAMES[backend]
            if not self._has_owner(name):
                reasons.append(f"{backend}=sem dono")
                continue

            path = BACKEND_PATHS[backend]
            cookie = None
            try:
                cookie = self._inhibit(backend, path)
                if backend == "mate" and not self._confirm_mate():
                    self._try_release(backend, path, cookie)
                    reasons.append("mate=não confirmou o proxy GSM")
                    continue
                if backend == "gsm" and not self._confirm_gsm():
                    self._try_release(backend, path, cookie)
                    reasons.append("gsm=não confirmou IsInhibited(8)")
                    continue
            except Exception as exc:
                if cookie is not None:
                    self._try_release(backend, path, cookie)
                logger.info("backend %s falhou ao inibir: %s", backend, exc)
                reasons.append(f"{backend}={exc}")
                continue

            self.backend = backend
            self.path = path
            self.cookie = cookie
            self._acquired_at = time.monotonic()
            logger.info("backend de tela adquirido: %s", backend)
            return

        raise InhibitError(
            "nenhum backend de tela disponível: " + "; ".join(reasons)
        )

    def confirm(self) -> bool:
        if self.backend is None or self.cookie is None:
            return False
        try:
            if self.backend == "mate":
                return self._confirm_mate()
            if self.backend == "gsm":
                return self._confirm_gsm()
            return self._confirm_fdo()
        except Exception as exc:
            logger.warning("falha ao confirmar o backend %s: %s", self.backend, exc)
            return False

    def release(self) -> None:
        if self.backend is None or self.cookie is None:
            return
        self._try_release(self.backend, self.path, self.cookie)
        self.cookie = None

    @property
    def needs_verification(self) -> bool:
        try:
            return self.backend == "fdo" and self._has_owner(POLICYAGENT_NAME)
        except Exception:
            return False

    # --- internos ---------------------------------------------------------

    def _has_owner(self, name: str) -> bool:
        try:
            return bool(self._bus.name_has_owner(name))
        except Exception:
            return False

    def _call(self, name: str, path: str, iface: str, member: str, *args):
        interface = dbus.Interface(self._bus.get_object(name, path), iface)
        return getattr(interface, member)(*args)

    def _inhibit(self, backend: str, path: str) -> int:
        name = BACKEND_BUS_NAMES[backend]
        iface = BACKEND_IFACES[backend]
        if backend == "gsm":
            cookie = self._call(
                name,
                path,
                iface,
                "Inhibit",
                self.who,
                dbus.UInt32(0),
                self.why,
                dbus.UInt32(GSM_IDLE_FLAG),
            )
        else:
            cookie = self._call(name, path, iface, "Inhibit", self.who, self.why)
        return int(cookie)

    def _try_release(self, backend: str, path: str | None, cookie: int) -> None:
        if path is None:
            path = BACKEND_PATHS[backend]
        method = "Uninhibit" if backend == "gsm" else "UnInhibit"
        try:
            self._call(
                BACKEND_BUS_NAMES[backend],
                path,
                BACKEND_IFACES[backend],
                method,
                dbus.UInt32(cookie),
            )
        except (dbus.DBusException, OSError) as exc:
            logger.warning("falha ao liberar o cookie %s: %s", cookie, exc)
        except Exception as exc:
            logger.warning("falha inesperada ao liberar o cookie %s: %s", cookie, exc)

    def _confirm_mate(self) -> bool:
        inhibitors = self._call(
            BACKEND_BUS_NAMES["mate"],
            BACKEND_PATHS["mate"],
            BACKEND_IFACES["mate"],
            "GetInhibitors",
        )
        marker = f"Application={self.who}"
        if not any(marker in str(item) for item in inhibitors):
            return False
        if self._has_owner(BACKEND_BUS_NAMES["gsm"]):
            return bool(
                self._call(
                    BACKEND_BUS_NAMES["gsm"],
                    BACKEND_PATHS["gsm"],
                    BACKEND_IFACES["gsm"],
                    "IsInhibited",
                    dbus.UInt32(GSM_IDLE_FLAG),
                )
            )
        return True

    def _confirm_gsm(self) -> bool:
        return bool(
            self._call(
                BACKEND_BUS_NAMES["gsm"],
                BACKEND_PATHS["gsm"],
                BACKEND_IFACES["gsm"],
                "IsInhibited",
                dbus.UInt32(GSM_IDLE_FLAG),
            )
        )

    def _confirm_fdo(self) -> bool:
        if not self._has_owner(POLICYAGENT_NAME):
            return True
        if (
            self._acquired_at
            and time.monotonic() - self._acquired_at < self.debounce
        ):
            return True

        active_available = False
        try:
            props = dbus.Interface(
                self._bus.get_object(POLICYAGENT_NAME, POLICYAGENT_PATH),
                dbus.PROPERTIES_IFACE,
            )
            value = props.Get(POLICYAGENT_IFACE, "ActiveInhibitions")
        except dbus.DBusException as exc:
            if not _is_unknown_error(exc):
                logger.warning("PolicyAgent indisponível para confirmação: %s", exc)
                return False
        except Exception as exc:
            logger.warning("PolicyAgent indisponível para confirmação: %s", exc)
            return False
        else:
            active_available = True
            if self._active_inhibitions_has_us(value):
                return True

        try:
            inhibited = self._call(
                POLICYAGENT_NAME,
                POLICYAGENT_PATH,
                POLICYAGENT_IFACE,
                "HasInhibition",
                dbus.UInt32(POLICYAGENT_CHANGE_SCREEN_SETTINGS),
            )
        except dbus.DBusException as exc:
            if not _is_unknown_error(exc):
                logger.warning("PolicyAgent indisponível para confirmação: %s", exc)
                return False
            if active_available:
                return False
            logger.warning(
                "PowerDevil sem ActiveInhibitions/HasInhibition; "
                "aceitando o cookie do ScreenSaver como confirmação"
            )
            return True
        except Exception as exc:
            logger.warning("PolicyAgent indisponível para confirmação: %s", exc)
            return False

        return bool(inhibited)

    def _active_inhibitions_has_us(self, value) -> bool:
        try:
            entries = list(value)
        except TypeError:
            return False
        for entry in entries:
            try:
                values = list(entry)
            except TypeError:
                continue
            if len(values) < 3:
                continue
            who = str(values[1])
            why = str(values[2])
            try:
                flags = int(values[-1])
            except (TypeError, ValueError):
                continue
            if (
                who == self.who
                and why == self.why
                and (flags & POLICYAGENT_ACTIVE_MASK) == POLICYAGENT_ACTIVE_MASK
            ):
                return True
        return False
