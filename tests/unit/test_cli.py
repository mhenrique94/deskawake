from __future__ import annotations

import os
import subprocess
import sys

import dbus
import pytest

import core.cli as cli
import core.daemon
from conftest import FakeBus, FakeMethod, REPO_ROOT
from core.daemon import DBUS_NAME, INTERFACE, OBJECT_PATH
from core.environment import Environment, is_wayland


class TrackingStatusBus(FakeBus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_service_by_name_calls = []

    def start_service_by_name(self, name, flags=0):
        self.start_service_by_name_calls.append((name, flags))


def _environment(
    *, session_type: str = "", wayland_display: str | None = None
) -> Environment:
    return Environment(
        desktop="",
        session_type=session_type,
        wayland_display=wayland_display,
        backends={},
        tools={},
    )


def test_help_documents_exit_codes(capsys, monkeypatch):
    def fail_bus():
        raise AssertionError("_session_bus não deve ser chamado em --help")

    monkeypatch.setattr(cli, "_session_bus", fail_bus)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 0
    assert "deskawake" in captured.out
    for subcommand in ("on", "off", "toggle", "status", "daemon", "ui"):
        assert subcommand in captured.out
    assert (
        "Códigos de saída:\n"
        "  status         0 = on, 1 = off ou error, 3 = daemon inacessível\n"
        "  on|off|toggle  0 = sucesso (on/off), 1 = resultado error, 3 = daemon inacessível\n"
        "  ui             0 = executou ou já havia instância, 1 = recusada ou falhou\n"
        "  daemon         código de saída do daemon (0 = saída limpa)"
    ) in captured.out


def test_usage_without_subcommand_exits_two():
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code == 2


def test_usage_rejects_force_outside_ui():
    for argv in (["status", "--force"], ["on", "--force"]):
        with pytest.raises(SystemExit) as excinfo:
            cli.main(argv)
        assert excinfo.value.code == 2


def test_main_returns_int_and_never_calls_sys_exit(fake_bus, monkeypatch):
    monkeypatch.setattr(cli, "_session_bus", lambda: fake_bus())

    result = cli.main(["status"])

    assert isinstance(result, int)


@pytest.mark.parametrize("session_type", ["wayland", "x11", ""])
@pytest.mark.parametrize("wayland_display", ["wayland-0", None])
def test_wayland_blocked_matrix(session_type, wayland_display):
    environment = _environment(
        session_type=session_type, wayland_display=wayland_display
    )

    expected = session_type == "wayland" or wayland_display is not None
    assert cli._wayland_blocked(environment) is expected


def test_is_wayland_keeps_session_type_only():
    assert is_wayland(_environment(session_type="wayland")) is True
    assert (
        is_wayland(
            _environment(session_type="x11", wayland_display="wayland-0")
        )
        is False
    )


def test_status_without_owner_is_unreachable_without_getstate(monkeypatch, capsys):
    bus = TrackingStatusBus()
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == "off\n"
    assert captured.err == "deskawake: daemon inacessível\n"
    assert bus.get_object_calls == []
    assert bus.calls == []
    assert bus.start_service_by_name_calls == []


def test_status_on(fake_bus, monkeypatch, capsys):
    bus = fake_bus(owners=[DBUS_NAME], methods={"GetState": "on"})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "on\n"
    assert captured.err == ""
    assert bus.get_object_calls == [(DBUS_NAME, OBJECT_PATH)]
    assert bus.get_dbus_method_calls == [
        (DBUS_NAME, OBJECT_PATH, "GetState", INTERFACE)
    ]


def test_status_off(fake_bus, monkeypatch, capsys):
    bus = fake_bus(owners=[DBUS_NAME], methods={"GetState": "off"})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == "off\n"
    assert captured.err == ""


def test_status_error(fake_bus, monkeypatch, capsys):
    bus = fake_bus(owners=[DBUS_NAME], methods={"GetState": "error"})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == "error\n"
    assert captured.err == ""


def test_status_getstate_failure_is_unreachable(fake_bus, monkeypatch, capsys):
    bus = fake_bus(
        owners=[DBUS_NAME], methods={"GetState": dbus.DBusException("sem resposta")}
    )
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == "off\n"
    assert captured.err == "deskawake: daemon inacessível\n"


@pytest.mark.parametrize("exc_type", [dbus.DBusException, OSError, KeyError])
def test_status_bus_failure_is_unreachable(exc_type, monkeypatch, capsys):
    def failing_bus():
        raise exc_type()

    monkeypatch.setattr(cli, "_session_bus", failing_bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == "off\n"
    assert captured.err == "deskawake: daemon inacessível\n"


def test_status_never_calls_start_service_by_name(monkeypatch):
    with_owner = TrackingStatusBus(owners=[DBUS_NAME], methods={"GetState": "on"})
    without_owner = TrackingStatusBus()

    monkeypatch.setattr(cli, "_session_bus", lambda: with_owner)
    assert cli.main(["status"]) == 0

    monkeypatch.setattr(cli, "_session_bus", lambda: without_owner)
    assert cli.main(["status"]) == 3

    assert with_owner.start_service_by_name_calls == []
    assert without_owner.start_service_by_name_calls == []


def test_status_invalid_state_is_unreachable(fake_bus, monkeypatch, capsys):
    bus = fake_bus(owners=[DBUS_NAME], methods={"GetState": "ligado"})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["status"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == "off\n"
    assert captured.err == "deskawake: resposta inválida do daemon\n"


def test_on_calls_set_active_true(fake_bus, monkeypatch, capsys):
    set_active = FakeMethod(return_value="on")
    bus = fake_bus(methods={"SetActive": set_active})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["on"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "on\n"
    assert captured.err == ""
    assert set_active.calls == [((dbus.Boolean(True),), {})]


def test_off_calls_set_active_false(fake_bus, monkeypatch, capsys):
    set_active = FakeMethod(return_value="off")
    bus = fake_bus(methods={"SetActive": set_active})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["off"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "off\n"
    assert captured.err == ""
    assert set_active.calls == [((dbus.Boolean(False),), {})]


def test_toggle_calls_toggle(fake_bus, monkeypatch, capsys):
    toggle = FakeMethod(return_value="on")
    bus = fake_bus(methods={"Toggle": toggle})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["toggle"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "on\n"
    assert captured.err == ""
    assert toggle.calls == [((), {})]


def test_action_error_state_exits_one(fake_bus, monkeypatch, capsys):
    bus = fake_bus(methods={"SetActive": "error"})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["on"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == "error\n"
    assert captured.err == ""


def test_action_bus_failure_exits_unreachable(fake_bus, monkeypatch, capsys):
    bus = fake_bus(methods={"SetActive": dbus.DBusException("sem daemon")})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["on"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == ""
    assert captured.err == "deskawake: daemon inacessível\n"


def test_action_invalid_state_exits_one(fake_bus, monkeypatch, capsys):
    bus = fake_bus(methods={"Toggle": "ligado"})
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    code = cli.main(["toggle"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == "deskawake: resposta inválida do daemon\n"


def test_actions_never_check_name_has_owner(fake_bus, monkeypatch):
    for command in ("on", "off", "toggle"):
        bus = fake_bus(methods={"SetActive": "on", "Toggle": "on"})
        monkeypatch.setattr(cli, "_session_bus", lambda: bus)

        cli.main([command])

        assert bus.name_has_owner_calls == []


def test_session_bus_failure_is_unreachable_without_stdout(monkeypatch, capsys):
    def failing_bus():
        raise KeyError()

    monkeypatch.setattr(cli, "_session_bus", failing_bus)

    code = cli.main(["off"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == ""
    assert captured.err == "deskawake: daemon inacessível\n"


def test_daemon_delegates_to_core_daemon(monkeypatch):
    monkeypatch.setattr(core.daemon, "main", lambda: 42)

    def fail_bus():
        raise AssertionError("_session_bus não deve ser chamado no daemon")

    monkeypatch.setattr(cli, "_session_bus", fail_bus)

    assert cli.main(["daemon"]) == 42

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["daemon", "--force"])
    assert excinfo.value.code == 2


def test_ui_refuses_wayland(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "_detect_environment", lambda: _environment(session_type="wayland")
    )
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    loader_calls = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: loader_calls.append(1))

    def fail_bus():
        raise AssertionError("barramento não deve ser aberto na recusa")

    monkeypatch.setattr(cli, "_session_bus", fail_bus)

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == (
        "deskawake: a UI GTK não é suportada em Wayland; "
        "use o Plasmoid do KDE ou repita com --force (ou DESKAWAKE_FORCE_UI=1) "
        "para depuração\n"
    )
    assert loader_calls == []


def test_ui_refuses_wayland_display(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_detect_environment",
        lambda: _environment(session_type="x11", wayland_display="wayland-0"),
    )
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    loader_calls = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: loader_calls.append(1))

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == cli.MSG_WAYLAND + "\n"
    assert loader_calls == []


def test_ui_registers_glib_loop_before_detection(monkeypatch):
    order = []

    def record_loop(*args, **kwargs):
        order.append("glib")

    def record_detect():
        order.append("detect")
        return _environment(session_type="wayland")

    monkeypatch.setattr(cli, "DBusGMainLoop", record_loop)
    monkeypatch.setattr(cli, "_detect_environment", record_detect)
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    code = cli.main(["ui"])

    assert order == ["glib", "detect"]
    assert code == 1


def test_ui_blocked_does_not_import_ui_gtk(monkeypatch):
    monkeypatch.setattr(
        cli, "_detect_environment", lambda: _environment(session_type="wayland")
    )
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    called = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: called.append("loader"))

    code = cli.main(["ui"])

    assert code == 1
    assert called == []
    assert "ui_gtk" not in sys.modules


class FakeUiBus:
    def __init__(self, request_name_result):
        self.request_name_result = request_name_result
        self.request_name_calls = []

    def request_name(self, name, flags):
        self.request_name_calls.append((name, flags))
        return self.request_name_result


def _fake_loader(loader_calls, ui_main_calls):
    def fake_loader():
        loader_calls.append(1)

        def fake_ui_main():
            ui_main_calls.append(1)

        return fake_ui_main

    return fake_loader


def test_ui_force_calls_main(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "_detect_environment", lambda: _environment(session_type="wayland")
    )
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    bus = FakeUiBus(dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    loader_calls = []
    ui_main_calls = []
    monkeypatch.setattr(
        cli, "_load_ui_main", _fake_loader(loader_calls, ui_main_calls)
    )

    code = cli.main(["ui", "--force"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert loader_calls == [1]
    assert ui_main_calls == [1]


def test_ui_force_env_calls_main(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "_detect_environment", lambda: _environment(session_type="wayland")
    )
    monkeypatch.setenv(cli.FORCE_UI_ENV, "1")

    bus = FakeUiBus(dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    loader_calls = []
    ui_main_calls = []
    monkeypatch.setattr(
        cli, "_load_ui_main", _fake_loader(loader_calls, ui_main_calls)
    )

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert loader_calls == [1]
    assert ui_main_calls == [1]


@pytest.mark.parametrize("value", ["0", "", "true"])
def test_ui_force_env_requires_exact_one(value, monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "_detect_environment", lambda: _environment(session_type="wayland")
    )
    monkeypatch.setenv(cli.FORCE_UI_ENV, value)

    loader_calls = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: loader_calls.append(1))

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == cli.MSG_WAYLAND + "\n"
    assert loader_calls == []


def test_ui_second_instance_exits_zero(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_detect_environment", lambda: _environment())
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    bus = FakeUiBus(dbus.bus.REQUEST_NAME_REPLY_EXISTS)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    loader_calls = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: loader_calls.append(1))

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert loader_calls == []


def test_ui_request_name_uses_do_not_queue(monkeypatch):
    monkeypatch.setattr(cli, "_detect_environment", lambda: _environment())
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    bus = FakeUiBus(dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)
    monkeypatch.setattr(cli, "_load_ui_main", lambda: lambda: None)

    cli.main(["ui"])

    assert bus.request_name_calls == [
        (cli.UI_NAME, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
    ]


@pytest.mark.parametrize("exc_type", [KeyError, dbus.DBusException])
def test_ui_bus_failure_exits_one(exc_type, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_detect_environment", lambda: _environment())
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    def failing_bus():
        raise exc_type()

    monkeypatch.setattr(cli, "_session_bus", failing_bus)

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == "deskawake: barramento de sessão indisponível\n"


def test_ui_loader_failure_exits_one(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_detect_environment", lambda: _environment())
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    bus = FakeUiBus(dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    def failing_loader():
        raise ImportError("ui_gtk não existe")

    monkeypatch.setattr(cli, "_load_ui_main", failing_loader)

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == "deskawake: falha ao iniciar a UI: ui_gtk não existe\n"


def test_ui_unexpected_request_name_result_exits_one(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_detect_environment", lambda: _environment())
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    bus = FakeUiBus(99)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    loader_calls = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: loader_calls.append(1))

    code = cli.main(["ui"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err == "deskawake: falha ao iniciar a UI\n"
    assert loader_calls == []


def test_ui_loader_not_called_before_request_name(monkeypatch, capsys):
    bus = FakeUiBus(dbus.bus.REQUEST_NAME_REPLY_EXISTS)
    monkeypatch.setattr(cli, "_session_bus", lambda: bus)

    loader_calls = []
    monkeypatch.setattr(cli, "_load_ui_main", lambda: loader_calls.append(1))
    monkeypatch.delenv(cli.FORCE_UI_ENV, raising=False)

    monkeypatch.setattr(
        cli, "_detect_environment", lambda: _environment(session_type="wayland")
    )
    assert cli.main(["ui"]) == 1
    assert bus.request_name_calls == []
    assert loader_calls == []
    capsys.readouterr()

    monkeypatch.setattr(cli, "_detect_environment", lambda: _environment())
    assert cli.main(["ui"]) == 0
    assert loader_calls == []


LAUNCHER = REPO_ROOT / "bin" / "deskawake"


def test_launcher_is_executable():
    assert LAUNCHER.is_file()
    assert os.access(LAUNCHER, os.X_OK)
    first_line = LAUNCHER.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "#!/usr/bin/env python3"


def test_launcher_help_from_repo_root():
    result = subprocess.run(
        [sys.executable, "bin/deskawake", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "deskawake" in result.stdout
    assert "Códigos de saída:" in result.stdout


def test_launcher_help_from_tmp_without_pythonpath(tmp_path):
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "deskawake" in result.stdout
    for subcommand in ("on", "off", "toggle", "status", "daemon", "ui"):
        assert subcommand in result.stdout
