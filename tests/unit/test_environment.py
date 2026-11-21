import pytest

import core.environment
from core.environment import BACKEND_BUS_NAMES, detect_environment, is_wayland

BACKEND_NAMES = ("fdo", "mate", "gsm", "policyagent")
TOOL_NAMES = ("kpackagetool6", "gdbus", "systemd-inhibit")


class FakeBus:
    def __init__(self, owned=()):
        self.owned = set(owned)
        self.name_has_owner_calls = []
        self.blocking_calls = []

    def name_has_owner(self, name):
        self.name_has_owner_calls.append(name)
        return name in self.owned

    def call_blocking(self, *args, **kwargs):
        self.blocking_calls.append((args, kwargs))
        raise AssertionError("call_blocking must not be used during detection")


class FailingBus(FakeBus):
    def __init__(self, failing_name, exception, owned=()):
        super().__init__(owned)
        self.failing_name = failing_name
        self.exception = exception

    def name_has_owner(self, name):
        if name == self.failing_name:
            self.name_has_owner_calls.append(name)
            raise self.exception
        return super().name_has_owner(name)


def _which_marks(*present):
    def which(name):
        return f"/usr/bin/{name}" if name in present else None

    return which


def _detect(env=None, bus=None, which=None):
    return detect_environment(
        env={} if env is None else env,
        bus=FakeBus() if bus is None else bus,
        which=_which_marks() if which is None else which,
    )


def test_empty_env_defaults():
    environment = _detect()

    assert environment.desktop == ""
    assert environment.session_type == ""
    assert environment.wayland_display is None
    assert is_wayland(environment) is False
    assert environment.backends == {name: False for name in BACKEND_NAMES}
    assert environment.tools == {name: False for name in TOOL_NAMES}


def test_injected_env_does_not_mix_os_environ(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")

    environment = _detect(env={})

    assert environment.desktop == ""


def test_desktop_is_raw_value():
    environment = _detect(env={"XDG_CURRENT_DESKTOP": "ubuntu:MATE"})

    assert environment.desktop == "ubuntu:MATE"


def test_session_type_is_lowercased():
    environment = _detect(env={"XDG_SESSION_TYPE": "X11"})

    assert environment.session_type == "x11"


def test_mate_x11_detection():
    environment = _detect(env={"XDG_CURRENT_DESKTOP": "MATE", "XDG_SESSION_TYPE": "x11"})

    assert environment.desktop == "MATE"
    assert environment.session_type == "x11"
    assert is_wayland(environment) is False


def test_wayland_detection():
    environment = _detect(
        env={"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"}
    )

    assert is_wayland(environment) is True


def test_wayland_display_empty_is_none():
    environment = _detect(env={"WAYLAND_DISPLAY": ""})

    assert environment.wayland_display is None


def test_is_wayland_ignores_wayland_display():
    environment = _detect(
        env={"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": "wayland-0"}
    )

    assert is_wayland(environment) is False


def test_tools_detection():
    environment = _detect(which=_which_marks("gdbus", "systemd-inhibit"))

    assert environment.tools == {
        "kpackagetool6": False,
        "gdbus": True,
        "systemd-inhibit": True,
    }


def test_kpackagetool6_absent_is_false_without_exception():
    environment = _detect(which=_which_marks())

    assert environment.tools["kpackagetool6"] is False


def test_backends_by_name_owner():
    bus = FakeBus(owned={"org.mate.ScreenSaver", "org.gnome.SessionManager"})

    environment = _detect(bus=bus)

    assert environment.backends == {
        "fdo": False,
        "mate": True,
        "gsm": True,
        "policyagent": False,
    }
    assert bus.blocking_calls == []


def test_detection_only_uses_name_has_owner():
    bus = FakeBus()

    _detect(bus=bus)

    assert sorted(bus.name_has_owner_calls) == sorted(BACKEND_BUS_NAMES.values())
    assert bus.blocking_calls == []


@pytest.mark.parametrize(
    "exception",
    [
        KeyError("boom"),
        RuntimeError("boom"),
        core.environment.dbus.DBusException("boom"),
    ],
)
def test_backend_failure_does_not_abort_detection(exception):
    bus = FailingBus(
        failing_name="org.mate.ScreenSaver",
        exception=exception,
        owned={"org.gnome.SessionManager"},
    )

    environment = _detect(bus=bus)

    assert environment.backends == {
        "fdo": False,
        "mate": False,
        "gsm": True,
        "policyagent": False,
    }


def test_no_session_bus_marks_all_backends_false(monkeypatch):
    def failing_session_bus():
        raise core.environment.dbus.DBusException("no session bus")

    monkeypatch.setattr(core.environment.dbus, "SessionBus", failing_session_bus)

    environment = detect_environment(env={}, which=_which_marks())

    assert environment.backends == {name: False for name in BACKEND_NAMES}
