from __future__ import annotations

import logging
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class State(Enum):
    OFF = "off"
    ACTIVATING = "activating"
    ON = "on"
    DEACTIVATING = "deactivating"
    ERROR = "error"


class StateMachine:
    """Máquina all-or-nothing entre os inibidores e o estado público."""

    def __init__(
        self,
        on_change: Callable[[str], None],
        verify_delay: float = 6.0,
        *,
        systemd=None,
        screen=None,
        schedule: Callable[[float, Callable[[], bool]], int] | None = None,
        cancel: Callable[[int], None] | None = None,
    ) -> None:
        self._on_change = on_change
        self._verify_delay = verify_delay
        self._systemd = systemd
        self._screen = screen
        self._schedule = schedule or self._default_schedule
        self._cancel = cancel or self._default_cancel
        self._state = State.OFF
        self._last_error = ""
        self._verify_source: int | None = None
        self._recovering = False

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def public_state(self) -> str:
        if self._state is State.ACTIVATING:
            return "off"
        if self._state is State.DEACTIVATING:
            return "on"
        return self._state.value

    @property
    def last_error(self) -> str:
        return self._last_error if self._state is State.ERROR else ""

    def activate(self) -> str:
        if self._state is State.ON:
            return "on"
        if self._state in (State.ACTIVATING, State.DEACTIVATING):
            return self.public_state
        if self._systemd is None or self._screen is None:
            raise RuntimeError(
                "StateMachine.activate() requer os inibidores injetados "
                "(systemd e screen)"
            )

        previous_public = self.public_state
        was_error = self._state is State.ERROR
        self._recovering = False
        self._state = State.ACTIVATING
        started_child = False

        try:
            if was_error:
                self.cancel_pending_verification()
                self._safe_release()
            if not self._systemd.alive:
                self._systemd.start()
                started_child = True
            self._screen.acquire()
        except Exception as exc:
            self._safe_release()
            if started_child:
                self._safe_stop_child()
            self._last_error = str(exc) or "falha ao ativar o DeskAwake"
            self._state = State.ERROR
            self._recovering = False
            if previous_public != "error":
                self._on_change("error")
            return "error"

        self._state = State.ON
        self._last_error = ""
        self._recovering = False
        self.cancel_pending_verification()
        if self._screen.needs_verification:
            self._schedule_verification()
        self._on_change("on")
        return "on"

    def deactivate(self) -> str:
        if self._state is State.OFF:
            return "off"
        if self._state in (State.ACTIVATING, State.DEACTIVATING):
            return self.public_state

        self._state = State.DEACTIVATING
        self.cancel_pending_verification()
        self._safe_release()
        self._safe_stop_child()
        self._state = State.OFF
        self._last_error = ""
        self._recovering = False
        self._on_change("off")
        return "off"

    def toggle(self) -> str:
        if self._state is State.ON:
            return self.deactivate()
        if self._state in (State.OFF, State.ERROR):
            return self.activate()
        return self.public_state

    def cancel_pending_verification(self) -> None:
        source_id = self._verify_source
        self._verify_source = None
        if source_id is None:
            return
        try:
            self._cancel(source_id)
        except Exception as exc:
            logger.warning("falha ao cancelar a verificação pendente: %s", exc)

    def handle_screen_lost(self, reason: str) -> None:
        if self._state is not State.ON:
            return
        self.cancel_pending_verification()
        self._safe_release()
        self._state = State.ERROR
        self._last_error = reason
        self._recovering = True
        self._on_change("error")

    def handle_screen_returned(self) -> None:
        if self._state is not State.ERROR or not self._recovering:
            return

        started_child = False
        try:
            self._safe_release()
            if not self._systemd.alive:
                self._systemd.start()
                started_child = True
            self._screen.acquire()
        except Exception as exc:
            self._safe_release()
            if started_child:
                self._safe_stop_child()
            self._last_error = str(exc) or "falha ao recuperar a inibição de tela"
            return

        self._state = State.ON
        self._last_error = ""
        self._recovering = False
        self.cancel_pending_verification()
        if self._screen.needs_verification:
            self._schedule_verification()
        self._on_change("on")

    def handle_session_end(self) -> None:
        self.cancel_pending_verification()
        self._safe_stop_child()
        self._state = State.OFF
        self._last_error = ""
        self._recovering = False

    # --- internos ---------------------------------------------------------

    def _safe_release(self) -> None:
        if self._screen is None:
            return
        try:
            self._screen.release()
        except Exception as exc:
            logger.warning("falha ao liberar a inibição de tela: %s", exc)

    def _safe_stop_child(self) -> None:
        if self._systemd is None:
            return
        try:
            self._systemd.stop()
        except Exception as exc:
            logger.warning("falha ao encerrar o systemd-inhibit: %s", exc)

    def _schedule_verification(self) -> None:
        self.cancel_pending_verification()
        try:
            self._verify_source = self._schedule(
                self._verify_delay, self._on_verify
            )
        except Exception as exc:
            self._verify_source = None
            logger.warning("falha ao agendar a verificação da inibição: %s", exc)

    def _on_verify(self) -> bool:
        self._verify_source = None
        if self._state is not State.ON:
            return False
        try:
            confirmed = bool(self._screen.confirm())
        except Exception as exc:
            logger.warning("falha ao confirmar a inibição de tela: %s", exc)
            confirmed = False
        if confirmed:
            return False

        self._safe_release()
        self._safe_stop_child()
        self._last_error = "a inibição de tela não foi confirmada"
        self._state = State.ERROR
        self._recovering = False
        self._on_change("error")
        return False

    @staticmethod
    def _default_schedule(delay: float, callback: Callable[[], bool]) -> int:
        from gi.repository import GLib

        return GLib.timeout_add(max(1, int(delay * 1000)), callback)

    @staticmethod
    def _default_cancel(source_id: int) -> None:
        from gi.repository import GLib

        GLib.source_remove(source_id)
