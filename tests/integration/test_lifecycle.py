from __future__ import annotations

import os
import signal
import subprocess

from conftest import DBUS_NAME, wait_until


def _start_private_bus():
    proc = subprocess.Popen(
        ["dbus-daemon", "--session", "--nofork", "--print-address"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    address = proc.stdout.readline().strip()
    return proc, address


def test_sigterm_releases_and_exits_zero(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake = fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    child = helpers.child_pids(daemon.pid)[0]

    daemon.proc.send_signal(signal.SIGTERM)

    assert daemon.wait_exit(timeout=5) == 0
    assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
    assert child not in helpers.inhibit_pids()
    entries = fake.entries()
    assert any(entry.get("method") == "UnInhibit" for entry in entries)
    assert "sinal" in daemon.log_path.read_text(encoding="utf-8").lower()


def test_sigint_releases_and_exits_zero(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake = fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    child = helpers.child_pids(daemon.pid)[0]

    daemon.proc.send_signal(signal.SIGINT)

    assert daemon.wait_exit(timeout=5) == 0
    assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
    assert child not in helpers.inhibit_pids()
    entries = fake.entries()
    assert any(entry.get("method") == "UnInhibit" for entry in entries)


def test_quit_releases_and_name_disappears(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake = fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    child = helpers.child_pids(daemon.pid)[0]

    daemon.quit()

    assert daemon.wait_exit(timeout=5) == 0
    assert wait_until(lambda: not daemon.bus.name_has_owner(DBUS_NAME), timeout=5)
    assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
    assert child not in helpers.inhibit_pids()
    entries = fake.entries()
    assert any(entry.get("method") == "UnInhibit" for entry in entries)


def test_local_disconnected_exits_zero_without_uninhibit(
    daemon_factory, fake_screensaver_factory, helpers
):
    bus_proc, address = _start_private_bus()
    environment = {"DBUS_SESSION_BUS_ADDRESS": address}
    try:
        fake = fake_screensaver_factory("--fdo", env_extra=environment)
        daemon = daemon_factory(
            confirm_delay=0,
            verify_delay=30,
            debounce=30,
            env_extra=environment,
            address=address,
        )
        assert daemon.set_active(True) == "on"
        child = helpers.child_pids(daemon.pid)[0]

        bus_proc.send_signal(signal.SIGTERM)

        assert daemon.wait_exit(timeout=5) == 0
        assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
        assert wait_until(
            lambda: any(
                entry.get("event") == "bus_disconnected"
                for entry in fake.entries()
            ),
            timeout=5,
        )
        entries = fake.entries()
        marker = next(
            index
            for index, entry in enumerate(entries)
            if entry.get("event") == "bus_disconnected"
        )
        assert not any(
            entry.get("method") in ("UnInhibit", "Uninhibit")
            for entry in entries[marker:]
        )
    finally:
        if bus_proc.poll() is None:
            bus_proc.kill()
        bus_proc.wait(timeout=5)


def test_pdeathsig_no_orphan(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    daemon.set_active(True)
    child = helpers.child_pids(daemon.pid)[0]

    os.kill(daemon.pid, signal.SIGKILL)
    daemon.wait_exit(timeout=5)

    assert wait_until(lambda: not helpers.pid_exists(child), timeout=2.5)
    assert child not in helpers.inhibit_pids()
