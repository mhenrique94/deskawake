from __future__ import annotations

from conftest import wait_until


def test_chain_uses_fdo_when_available(
    daemon_factory, fake_screensaver_factory
):
    fake = fake_screensaver_factory("--fdo")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    assert daemon.set_active(True) == "on"
    assert daemon.state() == "on"

    entries = fake.entries()
    assert any(
        entry.get("backend") == "fdo" and entry.get("method") == "Inhibit"
        for entry in entries
    )
    assert not any(entry.get("backend") in ("mate", "gsm") for entry in entries)


def test_chain_uses_mate_when_fdo_absent(
    daemon_factory, fake_screensaver_factory
):
    fake = fake_screensaver_factory("--mate", "--gsm")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    assert daemon.set_active(True) == "on"
    assert daemon.state() == "on"

    entries = fake.entries()
    assert any(
        entry.get("backend") == "mate" and entry.get("method") == "Inhibit"
        for entry in entries
    )
    assert any(entry.get("backend") == "gsm" for entry in entries)
    assert not any(entry.get("backend") == "fdo" for entry in entries)


def test_chain_uses_gsm_when_both_absent(
    daemon_factory, fake_screensaver_factory
):
    fake = fake_screensaver_factory("--gsm")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    assert daemon.set_active(True) == "on"
    assert daemon.state() == "on"

    entries = fake.entries()
    inhibit = next(
        entry
        for entry in entries
        if entry.get("backend") == "gsm" and entry.get("method") == "Inhibit"
    )
    assert inhibit["args"][1] == 0
    assert inhibit["args"][3] == 8


def test_kde_forwards_to_policyagent_once(
    daemon_factory, fake_screensaver_factory, fake_policyagent_factory
):
    fake_screensaver_factory("--fdo", "--kde")
    policyagent = fake_policyagent_factory("--debounce-ms", "50")
    daemon = daemon_factory(confirm_delay=0, verify_delay=30, debounce=30)

    assert daemon.set_active(True) == "on"

    assert wait_until(
        lambda: [
            entry
            for entry in policyagent.entries()
            if entry.get("method") == "AddInhibition"
        ],
        timeout=3,
    )
    additions = [
        entry
        for entry in policyagent.entries()
        if entry.get("method") == "AddInhibition"
    ]
    assert len(additions) == 1
    assert additions[0]["args"][0] == 4
