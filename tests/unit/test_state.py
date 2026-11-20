from __future__ import annotations

import logging

import pytest

from core.state import State, StateMachine


def _machine(
    *,
    systemd=None,
    screen=None,
    scheduler=None,
    verify_delay=6.0,
    on_change=None,
):
    events = [] if on_change is None else None
    callback = on_change if on_change is not None else events.append
    if isinstance(scheduler, type):
        scheduler = scheduler()
    machine = StateMachine(
        callback,
        verify_delay,
        systemd=systemd,
        screen=screen,
        schedule=scheduler.schedule if scheduler is not None else None,
        cancel=scheduler.cancel if scheduler is not None else None,
    )
    return machine, events, scheduler


def _activated(fake_systemd, fake_screen, fake_scheduler, **screen_kwargs):
    systemd = fake_systemd()
    screen = fake_screen(**screen_kwargs)
    machine, events, scheduler = _machine(
        systemd=systemd, screen=screen, scheduler=fake_scheduler
    )
    machine.activate()
    return machine, events, systemd, screen, scheduler


# --- identidade, estados e dependências --------------------------------------


def test_initial_state_off_and_last_error_empty(fake_systemd, fake_screen):
    machine, events, _ = _machine(
        systemd=fake_systemd(), screen=fake_screen(), scheduler=None
    )

    assert machine.state == "off"
    assert machine.public_state == "off"
    assert machine.last_error == ""
    assert events == []


def test_public_state_mapping(fake_systemd, fake_screen):
    machine, _events, _ = _machine(
        systemd=fake_systemd(), screen=fake_screen(), scheduler=None
    )

    for state, expected in (
        (State.OFF, "off"),
        (State.ON, "on"),
        (State.ERROR, "error"),
        (State.ACTIVATING, "off"),
        (State.DEACTIVATING, "on"),
    ):
        machine._state = state
        assert machine.public_state == expected


def test_invalid_dependencies_raise_runtime_error():
    machine = StateMachine(lambda state: None)

    assert machine.deactivate() == "off"
    with pytest.raises(RuntimeError, match="inibidores"):
        machine.activate()


# --- ativação ----------------------------------------------------------------


def test_activate_emits_only_public_states(fake_systemd, fake_screen):
    machine, events, _ = _machine(
        systemd=fake_systemd(), screen=fake_screen(), scheduler=None
    )

    machine.activate()

    assert events == ["on"]
    assert "activating" not in events


def test_activate_marks_activating_internally(fake_systemd, fake_screen):
    captured = {}
    screen = fake_screen(
        on_acquire=lambda: captured.setdefault("state", machine.state)
    )
    machine, _events, _ = _machine(
        systemd=fake_systemd(), screen=screen, scheduler=None
    )

    machine.activate()

    assert captured["state"] == "activating"


def test_activate_starts_systemd_before_acquiring_screen(fake_systemd, fake_screen):
    order = []

    class Systemd:
        alive = False

        def start(self):
            order.append("systemd.start")
            self.alive = True

        def stop(self):
            order.append("systemd.stop")
            self.alive = False

    screen = fake_screen(on_acquire=lambda: order.append("screen.acquire"))
    machine, _events, _ = _machine(systemd=Systemd(), screen=screen, scheduler=None)

    machine.activate()

    assert order.index("systemd.start") < order.index("screen.acquire")


def test_activation_idempotent_when_on(fake_systemd, fake_screen):
    systemd = fake_systemd()
    screen = fake_screen()
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)
    machine.activate()

    machine.activate()

    assert systemd.calls == ["start"]
    assert screen.calls.count("acquire") == 1
    assert events == ["on"]


def test_activate_returns_public_state(fake_systemd, fake_screen):
    machine, _events, _ = _machine(
        systemd=fake_systemd(), screen=fake_screen(), scheduler=None
    )

    assert machine.activate() == "on"


# --- falha de ativação e error -----------------------------------------------


def test_activation_failure_cleans_up(fake_systemd, fake_screen):
    systemd = fake_systemd()
    screen = fake_screen(acquire_raises=RuntimeError("tela falhou"))
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)

    result = machine.activate()

    assert result == "error"
    assert "tela falhou" in machine.last_error
    assert machine.state == "error"
    assert "release" in screen.calls
    assert systemd.calls == ["start", "stop"]
    assert events == ["error"]


def test_activation_failure_on_systemd_start_does_not_acquire_screen(
    fake_systemd, fake_screen
):
    systemd = fake_systemd(start_raises=RuntimeError("logind falhou"))
    screen = fake_screen()
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)

    assert machine.activate() == "error"

    assert "acquire" not in screen.calls
    assert events == ["error"]
    assert "logind falhou" in machine.last_error


def test_activate_from_error_keeps_live_child(fake_systemd, fake_screen):
    systemd = fake_systemd(alive=True)
    screen = fake_screen(acquire_raises=RuntimeError("primeira falha"))
    machine, _events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)
    machine.activate()
    screen.acquire_raises = None

    machine.activate()

    assert machine.state == "on"
    assert systemd.calls == []


def test_activate_from_error_starts_child_if_dead(fake_systemd, fake_screen):
    systemd = fake_systemd(alive=True)
    screen = fake_screen(acquire_raises=RuntimeError("primeira falha"))
    machine, _events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)
    machine.activate()
    screen.acquire_raises = None
    systemd.alive = False

    machine.activate()

    assert systemd.calls == ["start"]


def test_repeated_failure_updates_reason_without_signal(fake_systemd, fake_screen):
    screen = fake_screen(acquire_raises=RuntimeError("primeiro motivo"))
    machine, events, _ = _machine(
        systemd=fake_systemd(), screen=screen, scheduler=None
    )
    machine.activate()

    screen.acquire_raises = RuntimeError("segundo motivo")
    machine.activate()

    assert machine.last_error == "segundo motivo"
    assert events == ["error"]


def test_last_error_cleared_on_off_and_on(fake_systemd, fake_screen):
    screen = fake_screen(acquire_raises=RuntimeError("falha"))
    machine, _events, _ = _machine(
        systemd=fake_systemd(), screen=screen, scheduler=None
    )
    machine.activate()

    machine.deactivate()
    assert machine.last_error == ""

    screen.acquire_raises = None
    machine.activate()
    assert machine.last_error == ""
    assert machine.state == "on"


# --- desativação e toggle ----------------------------------------------------


def test_deactivate_releases_and_stops_in_order(fake_systemd, fake_screen):
    order = []

    class Systemd:
        alive = True

        def start(self):
            self.alive = True

        def stop(self):
            order.append("systemd.stop")
            self.alive = False

    screen = fake_screen()
    screen.release = lambda: order.append("screen.release")
    machine, events, _ = _machine(systemd=Systemd(), screen=screen, scheduler=None)
    machine.activate()
    events.clear()

    machine.deactivate()

    assert order == ["screen.release", "systemd.stop"]
    assert machine.state == "off"
    assert events == ["off"]
    assert machine.last_error == ""


def test_deactivation_idempotent_when_off(fake_systemd, fake_screen):
    systemd = fake_systemd()
    screen = fake_screen()
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)

    machine.deactivate()

    assert systemd.calls == []
    assert screen.calls == []
    assert events == []


def test_error_deactivate_goes_off(fake_systemd, fake_screen):
    systemd = fake_systemd()
    screen = fake_screen(acquire_raises=RuntimeError("falha"))
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)
    machine.activate()

    assert machine.deactivate() == "off"

    assert machine.state == "off"
    assert machine.last_error == ""
    assert "release" in screen.calls
    assert "stop" in systemd.calls
    assert events == ["error", "off"]


@pytest.mark.parametrize(
    ("start_state", "expected", "expected_events"),
    [
        ("on", "off", ["off"]),
        ("off", "on", ["on"]),
        ("error", "on", ["on"]),
    ],
)
def test_toggle_matrix(fake_systemd, fake_screen, start_state, expected, expected_events):
    screen = fake_screen()
    machine, events, _ = _machine(
        systemd=fake_systemd(), screen=screen, scheduler=None
    )
    if start_state == "on":
        machine.activate()
    elif start_state == "error":
        screen.acquire_raises = RuntimeError("falha")
        machine.activate()
        screen.acquire_raises = None
    events.clear()

    result = machine.toggle()

    assert result == expected
    assert machine.public_state == expected
    assert events == expected_events


def test_deactivate_clears_awaiting_dependency_return(fake_systemd, fake_screen, fake_scheduler):
    machine, _events, _systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("serviço caiu")
    assert machine._awaiting_dependency_return is True

    machine.deactivate()

    assert machine._awaiting_dependency_return is False


# --- verificação assíncrona --------------------------------------------------


def test_activate_schedules_verification_when_needed(fake_systemd, fake_screen, fake_scheduler):
    machine, _events, _systemd, _screen, scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
    )

    assert scheduler.delays == [6.0]
    assert len(scheduler.scheduled) == 1


def test_activate_schedules_configured_delay(fake_systemd, fake_screen, fake_scheduler):
    systemd = fake_systemd()
    screen = fake_screen(needs_verification=True)
    machine, _events, scheduler = _machine(
        systemd=systemd,
        screen=screen,
        scheduler=fake_scheduler,
        verify_delay=2.5,
    )

    machine.activate()

    assert scheduler.delays == [2.5]


def test_activate_does_not_schedule_without_needs_verification(
    fake_systemd, fake_screen, fake_scheduler
):
    _machine, _events, _systemd, _screen, scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler, needs_verification=False
    )

    assert scheduler.delays == []
    assert scheduler.scheduled == {}


def test_verification_success_keeps_on_without_signal(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, events, _systemd, _screen, scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
        confirm_value=True,
    )

    scheduler.fire()

    assert machine.state == "on"
    assert events == ["on"]
    assert scheduler.scheduled == {}


def test_verification_failure_while_on(fake_systemd, fake_screen, fake_scheduler):
    machine, events, systemd, screen, scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
        confirm_value=False,
    )

    scheduler.fire()

    assert machine.state == "error"
    assert machine.last_error != ""
    assert "release" in screen.calls
    assert "stop" in systemd.calls
    assert events == ["on", "error"]


def test_verification_failure_while_off_is_silent(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, events, _systemd, _screen, scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
        confirm_value=False,
    )
    source_id = next(iter(scheduler.scheduled))
    callback = scheduler.scheduled[source_id][1]
    machine.deactivate()
    events_before = list(events)

    callback()

    assert machine.state == "off"
    assert events == events_before


def test_cancel_verification_is_idempotent(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, _events, _systemd, _screen, _scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
    )

    machine.cancel_pending_verification()
    machine.cancel_pending_verification()

    assert machine._verify_source is None


def test_deactivate_cancels_pending_verification(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, _events, _systemd, _screen, scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
    )
    source_id = next(iter(scheduler.scheduled))

    machine.deactivate()

    assert source_id in scheduler.cancelled


# --- liveness ----------------------------------------------------------------


def test_liveness_loss_preserves_child(fake_systemd, fake_screen, fake_scheduler):
    machine, events, systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )

    machine.handle_dependency_lost("serviço sumiu")

    assert "release" in screen.calls
    assert "stop" not in systemd.calls
    assert machine.state == "error"
    assert machine._awaiting_dependency_return is True
    assert machine.last_error == "serviço sumiu"
    assert events == ["on", "error"]


def test_liveness_loss_ignored_when_not_on(fake_systemd, fake_screen, fake_scheduler):
    machine, events, _systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.deactivate()
    events.clear()
    calls_before = list(screen.calls)

    machine.handle_dependency_lost("sumiu")

    assert machine.state == "off"
    assert events == []
    assert screen.calls == calls_before


def test_liveness_loss_cancels_pending_verification(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, _events, _systemd, _screen, scheduler = _activated(
        fake_systemd,
        fake_screen,
        fake_scheduler,
        needs_verification=True,
    )
    source_id = next(iter(scheduler.scheduled))

    machine.handle_dependency_lost("sumiu")

    assert source_id in scheduler.cancelled


def test_liveness_return_single_attempt(fake_systemd, fake_screen, fake_scheduler):
    machine, events, _systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("sumiu")

    machine.handle_dependency_returned()

    assert machine.state == "on"
    assert machine._awaiting_dependency_return is False
    assert screen.calls.count("acquire") == 2
    assert screen.calls.count("release") >= 2
    assert events == ["on", "error", "on"]


def test_liveness_return_starts_child_if_dead(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, _events, systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("sumiu")
    systemd.alive = False
    screen.calls.clear()

    machine.handle_dependency_returned()

    assert "start" in systemd.calls
    assert screen.calls[0] == "release"
    assert "acquire" in screen.calls


def test_liveness_return_failure_no_signal(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, events, systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("sumiu")
    screen.acquire_raises = RuntimeError("ainda sem tela")

    machine.handle_dependency_returned()

    assert machine.state == "error"
    assert machine.last_error == "ainda sem tela"
    assert events == ["on", "error"]
    assert "stop" not in systemd.calls


def test_liveness_return_failure_logs_reason(
    fake_systemd, fake_screen, fake_scheduler, caplog
):
    machine, _events, _systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("sumiu")
    screen.acquire_raises = RuntimeError("ainda sem tela")

    with caplog.at_level(logging.ERROR, logger="core.state"):
        machine.handle_dependency_returned()

    assert "ainda sem tela" in caplog.text


def test_liveness_return_failure_uses_recovery_fallback(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, _events, _systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("sumiu")
    screen.acquire_raises = RuntimeError()

    machine.handle_dependency_returned()

    assert machine.last_error == "falha ao recuperar a inibição de tela"


def test_liveness_return_ignored_when_not_awaiting_dependency_return(
    fake_systemd, fake_screen, fake_scheduler
):
    screen = fake_screen(acquire_raises=RuntimeError("falha"))
    machine, events, _ = _machine(
        systemd=fake_systemd(), screen=screen, scheduler=fake_scheduler
    )
    machine.activate()
    events.clear()
    calls_before = list(screen.calls)

    machine.handle_dependency_returned()

    assert machine.state == "error"
    assert events == []
    assert screen.calls == calls_before


def test_explicit_activate_clears_awaiting_dependency_return(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, _events, _systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    machine.handle_dependency_lost("sumiu")

    machine.activate()

    assert machine._awaiting_dependency_return is False
    assert machine.state == "on"


# --- fim de sessão -----------------------------------------------------------


def test_session_end_stops_child_without_dbus(
    fake_systemd, fake_screen, fake_scheduler
):
    machine, events, systemd, screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    events.clear()

    machine.handle_session_end()

    assert "stop" in systemd.calls
    assert "release" not in screen.calls
    assert machine.state == "off"
    assert machine.last_error == ""
    assert machine._awaiting_dependency_return is False
    assert events == []


def test_session_end_from_error_is_safe(fake_systemd, fake_screen, fake_scheduler):
    screen = fake_screen(acquire_raises=RuntimeError("falha"))
    systemd = fake_systemd()
    machine, events, _ = _machine(
        systemd=systemd, screen=screen, scheduler=fake_scheduler
    )
    machine.activate()
    events.clear()
    screen.calls.clear()

    machine.handle_session_end()

    assert "stop" in systemd.calls
    assert "release" not in screen.calls
    assert machine.state == "off"
    assert events == []


# --- consistência dos sinais -------------------------------------------------


def test_on_change_called_after_state_is_consistent(fake_systemd, fake_screen):
    snapshots = []

    def on_change(_state):
        snapshots.append(machine.state)

    machine = StateMachine(
        on_change,
        systemd=fake_systemd(),
        screen=fake_screen(),
    )

    machine.activate()

    assert snapshots == ["on"]


def test_activate_while_activating_returns_public_off(fake_systemd, fake_screen):
    systemd = fake_systemd()
    screen = fake_screen()
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)
    machine._state = State.ACTIVATING

    assert machine.activate() == "off"
    assert systemd.calls == []
    assert screen.calls == []
    assert events == []


def test_deactivate_while_deactivating_returns_public_on(
    fake_systemd, fake_screen
):
    systemd = fake_systemd()
    screen = fake_screen()
    machine, events, _ = _machine(systemd=systemd, screen=screen, scheduler=None)
    machine._state = State.DEACTIVATING

    assert machine.deactivate() == "on"
    assert systemd.calls == []
    assert screen.calls == []
    assert events == []


def test_no_signal_on_noop_transitions(fake_systemd, fake_screen, fake_scheduler):
    machine, events, _systemd, _screen, _scheduler = _activated(
        fake_systemd, fake_screen, fake_scheduler
    )
    events.clear()

    assert machine.activate() == "on"
    machine._state = State.OFF
    assert machine.deactivate() == "off"
    machine._state = State.ACTIVATING
    assert machine.toggle() == "off"
    machine._state = State.DEACTIVATING
    assert machine.toggle() == "on"

    assert events == []
