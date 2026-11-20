from __future__ import annotations

import os
import time

import pytest

from conftest import wait_until


def _wait_elapsed(seconds, helpers):
    deadline = time.monotonic() + seconds
    helpers.wait_until(lambda: time.monotonic() >= deadline, timeout=seconds + 2)


def test_on_is_optimistic_before_confirmation(
    daemon_factory, fake_screensaver_factory, fake_policyagent_factory
):
    fake_screensaver_factory("--fdo", "--kde")
    fake_policyagent_factory("--debounce-ms", "3000")
    daemon = daemon_factory(confirm_delay=0, verify_delay=0.5, debounce=0.1)

    assert daemon.set_active(True) == "on"

    assert daemon.state() == "on"


def test_confirmation_within_window_stays_on(
    daemon_factory, fake_screensaver_factory, fake_policyagent_factory, helpers
):
    fake_screensaver_factory("--fdo", "--kde")
    fake_policyagent_factory("--debounce-ms", "50")
    daemon = daemon_factory(confirm_delay=0, verify_delay=0.5, debounce=0.1)
    assert daemon.set_active(True) == "on"

    _wait_elapsed(0.9, helpers)

    assert daemon.state() == "on"
    assert "error" not in daemon.signals


def test_confirmation_failure_goes_error(
    daemon_factory, fake_screensaver_factory, fake_policyagent_factory, helpers
):
    fake_screensaver_factory("--fdo", "--kde")
    fake_policyagent_factory("--fail")
    daemon = daemon_factory(confirm_delay=0, verify_delay=0.3, debounce=0.05)
    assert daemon.set_active(True) == "on"
    child = helpers.child_pids(daemon.pid)[0]

    assert wait_until(lambda: "error" in daemon.signals, timeout=5)

    assert daemon.state() == "error"
    assert daemon.last_error() != ""
    assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
    assert child not in helpers.inhibit_pids()


def test_set_active_false_during_window_cancels(
    daemon_factory, fake_screensaver_factory, fake_policyagent_factory, helpers
):
    fake_screensaver_factory("--fdo", "--kde")
    fake_policyagent_factory("--debounce-ms", "3000")
    daemon = daemon_factory(confirm_delay=0, verify_delay=0.5, debounce=0.1)
    assert daemon.set_active(True) == "on"

    assert daemon.set_active(False) == "off"
    _wait_elapsed(0.9, helpers)

    assert daemon.state() == "off"
    assert "error" not in daemon.signals


def test_get_last_error_after_forced_failure(
    daemon_factory, fake_screensaver_factory, tmp_path
):
    fake_screensaver_factory("--fdo")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    script = fake_bin / "systemd-inhibit"
    script.write_text(
        "#!/bin/sh\necho 'falha forçada do logind' >&2\nexit 1\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    daemon = daemon_factory(
        confirm_delay=0.2,
        env_extra={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert daemon.set_active(True) == "error"

    assert "falha forçada do logind" in daemon.last_error()


def test_powerdevil_drop_and_return(
    daemon_factory, fake_screensaver_factory, fake_policyagent_factory, helpers
):
    fake = fake_screensaver_factory("--fdo", "--kde")
    policyagent = fake_policyagent_factory("--debounce-ms", "50")
    daemon = daemon_factory(confirm_delay=0, verify_delay=0.3, debounce=0.05)
    assert daemon.set_active(True) == "on"
    _wait_elapsed(0.7, helpers)
    assert daemon.state() == "on"
    child = helpers.child_pids(daemon.pid)[0]
    initial_inhibits = [
        entry
        for entry in fake.entries()
        if entry.get("backend") == "fdo" and entry.get("method") == "Inhibit"
    ]
    assert len(initial_inhibits) == 1

    policyagent.proc.terminate()
    policyagent.proc.wait(timeout=5)

    assert wait_until(lambda: daemon.state() == "error", timeout=5)
    assert wait_until(lambda: "error" in daemon.signals, timeout=5)
    assert child in helpers.child_pids(daemon.pid)
    assert len(
        [
            entry
            for entry in fake.entries()
            if entry.get("backend") == "fdo" and entry.get("method") == "Inhibit"
        ]
    ) == len(initial_inhibits)

    fake_policyagent_factory("--debounce-ms", "50")

    assert wait_until(
        lambda: daemon.state() == "on"
        and daemon.signals
        and daemon.signals[-1] == "on",
        timeout=8,
    )
    assert child in helpers.child_pids(daemon.pid)
    inhibits = [
        entry
        for entry in fake.entries()
        if entry.get("backend") == "fdo" and entry.get("method") == "Inhibit"
    ]
    assert len(inhibits) == len(initial_inhibits) + 1


def test_gsm_drop_with_gsm_backend_exits_zero(
    daemon_factory, fake_screensaver_factory, helpers
):
    fake = fake_screensaver_factory("--gsm")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)
    assert daemon.set_active(True) == "on"
    child = helpers.child_pids(daemon.pid)[0]

    fake.proc.terminate()
    fake.proc.wait(timeout=5)

    assert daemon.wait_exit(timeout=5) == 0
    assert wait_until(lambda: not helpers.pid_exists(child), timeout=3)
    assert not any(
        entry.get("method") in ("UnInhibit", "Uninhibit")
        for entry in fake.entries()
    )


@pytest.mark.slow
def test_real_cycle_opt_in(daemon_factory, helpers):
    from core.environment import detect_environment

    environment = detect_environment()
    if "kde" not in environment.desktop.lower() or not environment.backends.get(
        "policyagent"
    ):
        pytest.skip("ciclo real requer KDE com PolicyAgent")

    daemon = daemon_factory()
    assert daemon.set_active(True) == "on"
    _wait_elapsed(6.5, helpers)
    assert daemon.state() == "on"
    assert daemon.set_active(False) == "off"
    daemon.quit()
    assert daemon.wait_exit(timeout=5) == 0
