from __future__ import annotations

import dbus

from conftest import wait_until
from dbus_contract import BACKEND_IFACES, BACKEND_NAMES, BACKEND_PATHS


def _mate_control(bus, method):
    proxy = bus.get_object(BACKEND_NAMES["gsm"], BACKEND_PATHS["gsm"])
    interface = dbus.Interface(proxy, BACKEND_IFACES["gsm"])
    getattr(interface, method)()


def test_fdo_drop_and_return(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake = fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    assert daemon.set_active(True) == "on"
    child = helpers.child_pids(daemon.pid)[0]

    fake.proc.terminate()
    fake.proc.wait(timeout=5)

    assert wait_until(lambda: daemon.state() == "error", timeout=5)
    assert wait_until(lambda: "error" in daemon.signals, timeout=5)
    assert daemon.last_error() != ""
    assert child in helpers.child_pids(daemon.pid)

    replacement = fake_screensaver_factory("--fdo")

    assert wait_until(
        lambda: daemon.state() == "on"
        and bool(daemon.signals)
        and daemon.signals[-1] == "on",
        timeout=8,
    )
    assert child in helpers.child_pids(daemon.pid)
    entry = next(
        entry
        for entry in replacement.entries()
        if entry.get("backend") == "fdo"
        and entry.get("method") == "Inhibit"
        and entry.get("proxy") is None
    )
    assert entry["args"][0] == "deskawake"


def test_mate_drop_and_return(
    daemon_factory, fake_screensaver_factory, control_bus, helpers
):
    fake = fake_screensaver_factory("--mate", "--gsm")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    assert daemon.set_active(True) == "on"
    child = helpers.child_pids(daemon.pid)[0]

    _mate_control(control_bus, "DropMate")

    assert wait_until(lambda: daemon.state() == "error", timeout=5)
    assert wait_until(lambda: "error" in daemon.signals, timeout=5)
    assert daemon.last_error() != ""
    assert child in helpers.child_pids(daemon.pid)

    _mate_control(control_bus, "RestoreMate")

    assert wait_until(
        lambda: daemon.state() == "on"
        and bool(daemon.signals)
        and daemon.signals[-1] == "on",
        timeout=8,
    )
    assert child in helpers.child_pids(daemon.pid)
    entries = fake.entries()
    mate_inhibits = [
        entry
        for entry in entries
        if entry.get("backend") == "mate"
        and entry.get("method") == "Inhibit"
    ]
    assert len(mate_inhibits) == 2
    assert not [
        entry
        for entry in entries
        if entry.get("backend") == "gsm"
        and entry.get("method") == "Inhibit"
        and entry.get("proxy") is None
    ]
