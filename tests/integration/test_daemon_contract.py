from __future__ import annotations

from conftest import DBUS_NAME, wait_until


def test_daemon_starts_off_and_registers_name(daemon_factory, control_bus):
    daemon = daemon_factory(confirm_delay=0)

    assert control_bus.name_has_owner(DBUS_NAME) is True
    assert daemon.state() == "off"
    assert daemon.last_error() == ""


def test_daemon_writes_log_at_configured_path(daemon_factory):
    daemon = daemon_factory(confirm_delay=0)

    def log_has_start():
        if not daemon.log_path.exists():
            return False
        return f"pid={daemon.pid}" in daemon.log_path.read_text(encoding="utf-8")

    assert wait_until(log_has_start, timeout=3)


def test_log_rotation_creates_backup(daemon_factory):
    daemon = daemon_factory(confirm_delay=0)
    daemon.log_path.write_text("x" * (300 * 1024), encoding="utf-8")
    daemon.quit()
    daemon.wait_exit(timeout=5)

    rotated = daemon.log_path.with_name(daemon.log_path.name + ".1")
    daemon2 = daemon_factory(
        confirm_delay=0,
        log_path=daemon.log_path,
        home=daemon.home,
    )

    assert wait_until(lambda: rotated.exists(), timeout=3)
    assert rotated.stat().st_size > 256 * 1024
    assert daemon2.state() == "off"


def test_daemon_survives_unwritable_log_path(daemon_factory, tmp_path):
    directory = tmp_path / "log-como-diretorio"
    directory.mkdir()

    daemon = daemon_factory(confirm_delay=0, log_path=directory)

    assert daemon.state() == "off"
    stderr = daemon.stderr_path.read_text(encoding="utf-8", errors="replace")
    assert stderr != ""


def test_set_active_true_reports_on_and_creates_lock(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    assert daemon.set_active(True) == "on"
    assert daemon.state() == "on"
    children = helpers.child_pids(daemon.pid)
    assert len(children) == 1
    assert wait_until(
        lambda: children[0] in helpers.inhibit_pids(), timeout=3
    )


def test_set_active_false_reports_off_and_removes_lock(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    child = helpers.child_pids(daemon.pid)[0]

    assert daemon.set_active(False) == "off"

    assert daemon.state() == "off"
    assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
    assert child not in helpers.inhibit_pids()


def test_set_active_true_is_idempotent(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    child = helpers.child_pids(daemon.pid)[0]

    assert daemon.set_active(True) == "on"

    assert helpers.child_pids(daemon.pid) == [child]
    assert daemon.state() == "on"


def test_toggle_matches_set_active_inverse(
    daemon_factory, fake_screensaver_factory
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    assert daemon.toggle() == "on"
    assert daemon.state() == "on"
    assert daemon.toggle() == "off"
    assert daemon.state() == "off"


def test_state_changed_only_public_states(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    daemon.set_active(True)
    daemon.set_active(False)

    assert wait_until(lambda: daemon.signals == ["on", "off"], timeout=5)
    assert "activating" not in daemon.signals
    assert "deactivating" not in daemon.signals


def test_get_last_error_empty_when_healthy(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    daemon.set_active(False)

    assert daemon.last_error() == ""


def test_second_instance_exits_zero(daemon_factory):
    first = daemon_factory(confirm_delay=0)
    second = daemon_factory(
        confirm_delay=0,
        home=first.home,
        wait_ready=False,
    )

    assert second.wait_exit(timeout=5) == 0
    assert first.state() == "off"


def test_name_visible_implies_object_ready(daemon_factory, control_bus):
    daemon = daemon_factory(confirm_delay=0)

    assert control_bus.name_has_owner(DBUS_NAME) is True
    assert daemon.state() == "off"
