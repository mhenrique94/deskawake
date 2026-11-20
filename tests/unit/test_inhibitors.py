from __future__ import annotations

import logging
import signal
import subprocess

import dbus
import pytest

import core.inhibitors
from core.environment import BACKEND_BUS_NAMES
from core.inhibitors import (
    GSM_IDLE_FLAG,
    POLICYAGENT_CHANGE_SCREEN_SETTINGS,
    InhibitError,
    ScreenSaverInhibit,
    SystemdInhibit,
)

FDO_NAME = BACKEND_BUS_NAMES["fdo"]
MATE_NAME = BACKEND_BUS_NAMES["mate"]
GSM_NAME = BACKEND_BUS_NAMES["gsm"]
PA_NAME = BACKEND_BUS_NAMES["policyagent"]

FDO_PATH = "/org/freedesktop/ScreenSaver"
MATE_PATH = "/org/mate/ScreenSaver"
GSM_PATH = "/org/gnome/SessionManager"
PA_PATH = "/org/kde/Solid/PowerManagement/PolicyAgent"
PA_IFACE = "org.kde.Solid.PowerManagement.PolicyAgent"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

MATE_APP = "Application=deskawake; Reason=DeskAwake active;"


def _unknown(name="org.freedesktop.DBus.Error.UnknownMethod"):
    return dbus.exceptions.DBusException("mecanismo ausente", name=name)


def _make_screen(bus, **kwargs):
    kwargs.setdefault("debounce", 0.0)
    kwargs.setdefault("verify_delay", 0.0)
    return ScreenSaverInhibit(bus, **kwargs)


def _acquire_fdo(bus):
    bus.add_method((FDO_NAME, FDO_PATH, "Inhibit"), 11)
    screen = _make_screen(bus)
    screen.acquire()
    return screen


def _calls_to(bus, name, member):
    return [call for call in bus.calls if call[0] == name and call[2] == member]


def _call_index(bus, name, member):
    for index, call in enumerate(bus.calls):
        if call[0] == name and call[2] == member:
            return index
    return -1


# --- SystemdInhibit -----------------------------------------------------------


def test_systemd_command_has_exact_args(fake_process, fake_popen):
    process = fake_process(pid=1234)
    calls = fake_popen(process)

    inhibitor = SystemdInhibit(confirm_delay=0)
    inhibitor.start()

    args, kwargs = calls[0]
    assert args == [
        "systemd-inhibit",
        "--what=idle",
        "--mode=block",
        "--who=DeskAwake",
        "--why=DeskAwake active",
        "sleep",
        "infinity",
    ]
    assert "--what=sleep" not in args
    assert "--what=idle" in args
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.PIPE
    assert callable(kwargs["preexec_fn"])


def test_start_raises_with_stderr_when_child_dies(fake_process, fake_popen):
    process = fake_process(
        poll_return=1, communicate_result=(b"", b"falha do logind")
    )
    fake_popen(process)

    inhibitor = SystemdInhibit(confirm_delay=0)

    with pytest.raises(InhibitError, match="falha do logind"):
        inhibitor.start()
    assert process.stderr.closed is True
    assert inhibitor.alive is False


def test_start_missing_binary_raises_inhibit_error(fake_popen):
    fake_popen(None, raises=FileNotFoundError("systemd-inhibit"))

    with pytest.raises(InhibitError):
        SystemdInhibit(confirm_delay=0).start()


def test_start_raises_with_exit_code_when_stderr_empty(fake_process, fake_popen):
    process = fake_process(poll_return=1, communicate_result=(b"", b""))
    fake_popen(process)

    with pytest.raises(InhibitError) as excinfo:
        SystemdInhibit(confirm_delay=0).start()

    assert "1" in str(excinfo.value)


def test_alive_and_pid_reflect_process(fake_process, fake_popen):
    process = fake_process(pid=7777, poll_return=None)
    fake_popen(process)

    inhibitor = SystemdInhibit(confirm_delay=0)
    inhibitor.start()

    assert inhibitor.alive is True
    assert inhibitor.pid == 7777

    process.set_poll(0)

    assert inhibitor.alive is False


def test_start_is_idempotent_when_alive(fake_process, fake_popen):
    process = fake_process(pid=1234, poll_return=None)
    calls = fake_popen(process)

    inhibitor = SystemdInhibit(confirm_delay=0)
    inhibitor.start()
    inhibitor.start()

    assert len(calls) == 1


def test_stop_kills_process_group_in_order(fake_process, fake_popen, monkeypatch):
    process = fake_process(pid=4321, poll_return=None)
    fake_popen(process)
    inhibitor = SystemdInhibit(confirm_delay=0)
    inhibitor.start()

    kills = []
    monkeypatch.setattr(
        core.inhibitors.os, "killpg", lambda pid, sig: kills.append((pid, sig))
    )

    inhibitor.stop()

    assert kills == [(4321, signal.SIGTERM)]
    assert process.waits == [2]
    assert process.stderr.closed is True
    assert inhibitor.pid is None


def test_stop_escalates_after_timeout(fake_process, fake_popen, monkeypatch):
    process = fake_process(
        pid=4321,
        poll_return=None,
        wait_results=[subprocess.TimeoutExpired("systemd-inhibit", 2), 0],
    )
    fake_popen(process)
    inhibitor = SystemdInhibit(confirm_delay=0)
    inhibitor.start()

    kills = []
    monkeypatch.setattr(
        core.inhibitors.os, "killpg", lambda pid, sig: kills.append((pid, sig))
    )

    inhibitor.stop()

    assert kills == [(4321, signal.SIGTERM), (4321, signal.SIGKILL)]
    assert process.waits == [2, 2]


def test_stop_is_idempotent_when_dead(fake_process, fake_popen, monkeypatch):
    process = fake_process(pid=4321, poll_return=None)
    fake_popen(process)
    inhibitor = SystemdInhibit(confirm_delay=0)
    inhibitor.start()
    process.set_poll(0)

    kills = []
    monkeypatch.setattr(
        core.inhibitors.os, "killpg", lambda pid, sig: kills.append((pid, sig))
    )

    inhibitor.stop()
    inhibitor.stop()

    assert kills == []
    assert process.waits == [2]


# --- ScreenSaverInhibit.acquire ----------------------------------------------


def test_backend_chain_fdo(fake_bus):
    bus = fake_bus(
        owners={FDO_NAME},
        methods={(FDO_NAME, FDO_PATH, "Inhibit"): 42},
    )

    screen = _make_screen(bus)
    screen.acquire()

    assert screen.backend == "fdo"
    assert screen.path == FDO_PATH
    assert screen.cookie == 42
    call = _calls_to(bus, FDO_NAME, "Inhibit")[0]
    assert call[3] == ("deskawake", "DeskAwake active")


def test_backend_chain_mate(fake_bus):
    bus = fake_bus(
        owners={MATE_NAME, GSM_NAME},
        methods={
            (MATE_NAME, MATE_PATH, "Inhibit"): 77,
            (MATE_NAME, MATE_PATH, "GetInhibitors"): [MATE_APP],
            (GSM_NAME, GSM_PATH, "IsInhibited"): True,
        },
    )

    screen = _make_screen(bus)
    screen.acquire()

    assert screen.backend == "mate"
    assert screen.path == MATE_PATH
    assert screen.cookie == 77
    assert _calls_to(bus, MATE_NAME, "GetInhibitors")
    assert _calls_to(bus, GSM_NAME, "Inhibit") == []


def test_backend_chain_gsm(fake_bus):
    bus = fake_bus(
        owners={GSM_NAME},
        methods={
            (GSM_NAME, GSM_PATH, "Inhibit"): 88,
            (GSM_NAME, GSM_PATH, "IsInhibited"): True,
        },
    )

    screen = _make_screen(bus)
    screen.acquire()

    assert screen.backend == "gsm"
    assert screen.path == GSM_PATH
    assert screen.cookie == 88


def test_gsm_uses_xid_zero_and_flags_eight(fake_bus):
    bus = fake_bus(
        owners={GSM_NAME},
        methods={
            (GSM_NAME, GSM_PATH, "Inhibit"): 88,
            (GSM_NAME, GSM_PATH, "IsInhibited"): True,
        },
    )

    _make_screen(bus).acquire()

    args = _calls_to(bus, GSM_NAME, "Inhibit")[0][3]
    assert args[0] == "deskawake"
    assert isinstance(args[1], dbus.UInt32) and int(args[1]) == 0
    assert args[2] == "DeskAwake active"
    assert isinstance(args[3], dbus.UInt32)
    assert int(args[3]) == GSM_IDLE_FLAG == 8


def test_fdo_inhibit_failure_falls_through_to_mate(fake_bus):
    bus = fake_bus(
        owners={FDO_NAME, MATE_NAME},
        methods={
            (FDO_NAME, FDO_PATH, "Inhibit"): dbus.DBusException("fdo quebrado"),
            (MATE_NAME, MATE_PATH, "Inhibit"): 21,
            (MATE_NAME, MATE_PATH, "GetInhibitors"): [MATE_APP],
        },
    )

    screen = _make_screen(bus)
    screen.acquire()

    assert screen.backend == "mate"
    assert screen.cookie == 21
    assert _calls_to(bus, FDO_NAME, "UnInhibit") == []


def test_no_backend_raises_inhibit_error_with_reasons(fake_bus):
    screen = _make_screen(fake_bus())

    with pytest.raises(InhibitError) as excinfo:
        screen.acquire()

    message = str(excinfo.value)
    assert "fdo" in message
    assert "mate" in message
    assert "gsm" in message
    assert screen.cookie is None


def test_mate_confirmed_does_not_inhibit_gsm(fake_bus):
    bus = fake_bus(
        owners={MATE_NAME, GSM_NAME},
        methods={
            (MATE_NAME, MATE_PATH, "Inhibit"): 77,
            (MATE_NAME, MATE_PATH, "GetInhibitors"): [MATE_APP],
            (GSM_NAME, GSM_PATH, "IsInhibited"): True,
        },
    )

    _make_screen(bus).acquire()

    assert _calls_to(bus, GSM_NAME, "Inhibit") == []


def test_mate_proxy_failure_falls_back_to_gsm(fake_bus, fake_method):
    bus = fake_bus(
        owners={MATE_NAME, GSM_NAME},
        methods={
            (MATE_NAME, MATE_PATH, "Inhibit"): 31,
            (MATE_NAME, MATE_PATH, "GetInhibitors"): [MATE_APP],
            (GSM_NAME, GSM_PATH, "IsInhibited"): fake_method(side_effect=[False, True]),
            (GSM_NAME, GSM_PATH, "Inhibit"): 32,
        },
    )

    screen = _make_screen(bus)
    screen.acquire()

    assert screen.backend == "gsm"
    assert screen.cookie == 32
    mate_uninhibit = _calls_to(bus, MATE_NAME, "UnInhibit")
    assert len(mate_uninhibit) == 1
    assert int(mate_uninhibit[0][3][0]) == 31
    gsm_inhibit = _calls_to(bus, GSM_NAME, "Inhibit")
    assert len(gsm_inhibit) == 1


def test_acquire_releases_partial_mate_cookie_before_gsm(fake_bus, fake_method):
    bus = fake_bus(
        owners={MATE_NAME, GSM_NAME},
        methods={
            (MATE_NAME, MATE_PATH, "Inhibit"): 31,
            (MATE_NAME, MATE_PATH, "GetInhibitors"): [MATE_APP],
            (GSM_NAME, GSM_PATH, "IsInhibited"): fake_method(side_effect=[False, True]),
            (GSM_NAME, GSM_PATH, "Inhibit"): 32,
        },
    )

    _make_screen(bus).acquire()

    assert _call_index(bus, MATE_NAME, "UnInhibit") < _call_index(bus, GSM_NAME, "Inhibit")


def test_gsm_confirmation_failure_releases_and_raises(fake_bus):
    bus = fake_bus(
        owners={GSM_NAME},
        methods={
            (GSM_NAME, GSM_PATH, "Inhibit"): 55,
            (GSM_NAME, GSM_PATH, "IsInhibited"): False,
        },
    )

    screen = _make_screen(bus)
    with pytest.raises(InhibitError):
        screen.acquire()

    uninhibit = _calls_to(bus, GSM_NAME, "Uninhibit")
    assert len(uninhibit) == 1
    assert int(uninhibit[0][3][0]) == 55
    assert screen.cookie is None


def test_acquire_failure_does_not_hold_partial_cookie(fake_bus):
    screen = _make_screen(fake_bus())

    with pytest.raises(InhibitError):
        screen.acquire()

    assert screen.cookie is None
    assert screen.backend is None


# --- ScreenSaverInhibit.release ----------------------------------------------


def _screen_for_backend(bus, backend):
    if backend == "fdo":
        bus.owners.add(FDO_NAME)
        bus.add_method((FDO_NAME, FDO_PATH, "Inhibit"), 1)
    elif backend == "mate":
        bus.owners.add(MATE_NAME)
        bus.add_method((MATE_NAME, MATE_PATH, "Inhibit"), 2)
        bus.add_method(
            (MATE_NAME, MATE_PATH, "GetInhibitors"),
            [MATE_APP],
        )
    else:
        bus.owners.add(GSM_NAME)
        bus.add_method((GSM_NAME, GSM_PATH, "Inhibit"), 3)
        bus.add_method(
            (GSM_NAME, GSM_PATH, "IsInhibited"), True
        )
    screen = _make_screen(bus)
    screen.acquire()
    return screen


@pytest.mark.parametrize(
    ("backend", "name", "method_name"),
    [
        ("fdo", FDO_NAME, "UnInhibit"),
        ("mate", MATE_NAME, "UnInhibit"),
        ("gsm", GSM_NAME, "Uninhibit"),
    ],
)
def test_release_uses_correct_method_names(fake_bus, backend, name, method_name):
    bus = fake_bus()
    screen = _screen_for_backend(bus, backend)
    cookie = screen.cookie

    screen.release()

    calls = _calls_to(bus, name, method_name)
    assert len(calls) == 1
    assert int(calls[0][3][0]) == cookie
    assert screen.cookie is None


def test_release_keeps_last_backend_and_clears_cookie(fake_bus):
    bus = fake_bus()
    screen = _screen_for_backend(bus, "fdo")

    screen.release()

    assert screen.backend == "fdo"
    assert screen.path == FDO_PATH
    assert screen.cookie is None


def test_release_is_idempotent(fake_bus):
    bus = fake_bus()
    screen = _screen_for_backend(bus, "fdo")
    screen.release()
    calls_after_first = len(bus.calls)

    screen.release()

    assert len(bus.calls) == calls_after_first


def test_release_absorbs_dbus_exception(fake_bus):
    bus = fake_bus()
    screen = _screen_for_backend(bus, "fdo")
    bus.add_method(
        (FDO_NAME, FDO_PATH, "UnInhibit"),
        dbus.DBusException("barramento caiu"),
    )

    screen.release()

    assert screen.cookie is None


# --- ScreenSaverInhibit.confirm / needs_verification -------------------------


def _kde_screen(fake_bus, *, get_value=None, get_raises=None, has_value=None, has_raises=None):
    bus = fake_bus(owners={FDO_NAME})
    screen = _screen_for_backend(bus, "fdo")
    bus.owners.add(PA_NAME)
    if get_raises is not None:
        bus.add_method((PA_NAME, PROPERTIES_IFACE, "Get"), get_raises)
    elif get_value is not None:
        bus.add_method((PA_NAME, PROPERTIES_IFACE, "Get"), get_value)
    if has_raises is not None:
        bus.add_method((PA_NAME, "HasInhibition"), has_raises)
    elif has_value is not None:
        bus.add_method((PA_NAME, "HasInhibition"), has_value)
    return bus, screen


def test_confirm_without_cookie_is_false(fake_bus):
    screen = _make_screen(fake_bus())

    assert screen.confirm() is False


def test_confirm_fdo_non_kde_is_true(fake_bus):
    bus = fake_bus()
    screen = _screen_for_backend(bus, "fdo")

    assert screen.confirm() is True


def test_confirm_kde_active_inhibitions(fake_bus):
    _bus, screen = _kde_screen(
        fake_bus,
        get_value=[(4, "deskawake", "DeskAwake active", 0, 3)],
    )

    assert screen.confirm() is True


def test_confirm_kde_has_inhibition_fallback(fake_bus):
    _bus, screen = _kde_screen(
        fake_bus,
        get_raises=_unknown(),
        has_value=True,
    )

    assert screen.confirm() is True
    assert int(_bus.calls[-1][3][0]) == POLICYAGENT_CHANGE_SCREEN_SETTINGS


def test_confirm_kde_cookie_fallback_with_warning(fake_bus, caplog):
    _bus, screen = _kde_screen(
        fake_bus,
        get_raises=_unknown("org.freedesktop.DBus.Error.UnknownProperty"),
        has_raises=_unknown("org.freedesktop.DBus.Error.UnknownMethod"),
    )

    with caplog.at_level(logging.WARNING):
        assert screen.confirm() is True

    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_confirm_kde_available_negative_is_false(fake_bus):
    _bus, screen = _kde_screen(
        fake_bus,
        get_value=[],
        has_raises=_unknown("org.freedesktop.DBus.Error.UnknownMethod"),
    )

    assert screen.confirm() is False


def test_confirm_kde_has_inhibition_false_is_false(fake_bus):
    _bus, screen = _kde_screen(
        fake_bus,
        get_raises=_unknown("org.freedesktop.DBus.Error.UnknownProperty"),
        has_value=False,
    )

    assert screen.confirm() is False


def test_confirm_kde_transport_error_with_owner_is_false(fake_bus):
    _bus, screen = _kde_screen(
        fake_bus,
        get_raises=dbus.DBusException("barramento indisponível"),
    )

    assert screen.confirm() is False


def test_confirm_debounce_guard(fake_bus):
    bus = fake_bus(owners={FDO_NAME})
    screen = _screen_for_backend(bus, "fdo")
    bus.owners.add(PA_NAME)
    bus.add_method(
        (PA_NAME, PROPERTIES_IFACE, "Get"),
        [],
    )
    bus.add_method(
        (PA_NAME, "HasInhibition"),
        False,
    )
    screen.debounce = 5.0

    assert screen.confirm() is True

    screen._acquired_at -= 10
    assert screen.confirm() is False


def test_needs_verification_only_for_kde_fdo(fake_bus):
    bus = fake_bus(owners={FDO_NAME})
    screen = _screen_for_backend(bus, "fdo")
    bus.owners.add(PA_NAME)
    assert screen.needs_verification is True

    bus.owners.discard(PA_NAME)
    assert screen.needs_verification is False

    mate_bus = fake_bus(owners={MATE_NAME})
    mate = _screen_for_backend(mate_bus, "mate")
    mate_bus.owners.add(PA_NAME)
    assert mate.needs_verification is False

    gsm_bus = fake_bus(owners={GSM_NAME})
    gsm = _screen_for_backend(gsm_bus, "gsm")
    gsm_bus.owners.add(PA_NAME)
    assert gsm.needs_verification is False


def test_needs_verification_bus_error_is_false(fake_bus):
    bus = fake_bus(fail_owners={PA_NAME})
    screen = _make_screen(bus)
    screen.backend = "fdo"
    screen.cookie = 1

    assert screen.needs_verification is False


# --- contrato restante --------------------------------------------------------


def test_acquire_records_acquired_at(fake_bus):
    bus = fake_bus(owners={FDO_NAME})
    bus.add_method((FDO_NAME, FDO_PATH, "Inhibit"), 9)
    screen = _make_screen(bus)

    screen.acquire()

    assert screen._acquired_at > 0


def test_acquire_overwrites_previous_backend(fake_bus):
    bus = fake_bus(owners={FDO_NAME})
    bus.add_method((FDO_NAME, FDO_PATH, "Inhibit"), 9)
    bus.add_method((GSM_NAME, GSM_PATH, "Inhibit"), 19)
    bus.add_method(
        (GSM_NAME, GSM_PATH, "IsInhibited"), True
    )
    screen = _make_screen(bus)
    screen.acquire()

    bus.set_owner(FDO_NAME, False)
    bus.set_owner(GSM_NAME, True)
    screen.acquire()

    assert screen.backend == "gsm"
    assert screen.path == GSM_PATH
    assert screen.cookie == 19


def test_confirm_after_release_is_false(fake_bus):
    bus = fake_bus(owners={FDO_NAME})
    bus.add_method((FDO_NAME, FDO_PATH, "Inhibit"), 9)
    screen = _make_screen(bus)
    screen.acquire()
    screen.release()

    assert screen.confirm() is False


def test_acquire_without_owner_does_not_wake_service(fake_bus):
    bus = fake_bus()

    with pytest.raises(InhibitError):
        _make_screen(bus).acquire()

    assert bus.get_object_calls == []


def test_mate_confirmation_exception_releases_and_falls_back_to_gsm(fake_bus):
    bus = fake_bus(
        owners={MATE_NAME, GSM_NAME},
        methods={
            (MATE_NAME, MATE_PATH, "Inhibit"): 31,
            (MATE_NAME, MATE_PATH, "GetInhibitors"): dbus.DBusException(
                "proxy MATE caiu"
            ),
            (GSM_NAME, GSM_PATH, "Inhibit"): 32,
            (GSM_NAME, GSM_PATH, "IsInhibited"): True,
        },
    )

    screen = _make_screen(bus)
    screen.acquire()

    assert screen.backend == "gsm"
    assert screen.cookie == 32
    mate_uninhibit = _calls_to(bus, MATE_NAME, "UnInhibit")
    assert len(mate_uninhibit) == 1
    assert int(mate_uninhibit[0][3][0]) == 31
    assert _call_index(bus, MATE_NAME, "UnInhibit") < _call_index(bus, GSM_NAME, "Inhibit")


def test_gsm_confirmation_exception_releases_and_raises(fake_bus):
    bus = fake_bus(
        owners={GSM_NAME},
        methods={
            (GSM_NAME, GSM_PATH, "Inhibit"): 55,
            (GSM_NAME, GSM_PATH, "IsInhibited"): dbus.DBusException(
                "proxy GSM caiu"
            ),
        },
    )

    screen = _make_screen(bus)
    with pytest.raises(InhibitError):
        screen.acquire()

    uninhibit = _calls_to(bus, GSM_NAME, "Uninhibit")
    assert len(uninhibit) == 1
    assert int(uninhibit[0][3][0]) == 55
    assert screen.cookie is None


def test_acquire_releases_previous_cookie(fake_bus, fake_method):
    bus = fake_bus(
        owners={FDO_NAME},
        methods={
            (FDO_NAME, FDO_PATH, "Inhibit"): fake_method(side_effect=[9, 10]),
        },
    )
    screen = _make_screen(bus)
    screen.acquire()

    screen.acquire()

    assert screen.cookie == 10
    uninhibit = _calls_to(bus, FDO_NAME, "UnInhibit")
    assert len(uninhibit) == 1
    assert int(uninhibit[0][3][0]) == 9
