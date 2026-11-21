from __future__ import annotations

import itertools
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import dbus
import pytest
from dbus.mainloop.glib import DBusGMainLoop
from dbus_contract import (
    BACKEND_NAMES,
    DAEMON_IFACE,
    DAEMON_NAME,
    DAEMON_PATH,
    POLICYAGENT_NAME,
)
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

REPO_ROOT = Path(__file__).resolve().parents[1]

DBUS_NAME = DAEMON_NAME
OBJECT_PATH = DAEMON_PATH
INTERFACE = DAEMON_IFACE

FAKE_SCREENSAVER = REPO_ROOT / "tests/integration/fakes/fake_screensaver.py"
FAKE_POLICYAGENT = REPO_ROOT / "tests/integration/fakes/fake_policyagent.py"

SCREENSAVER_NAMES = {
    "--fdo": BACKEND_NAMES["fdo"],
    "--mate": BACKEND_NAMES["mate"],
    "--gsm": BACKEND_NAMES["gsm"],
}


# --- fakes unitários de D-Bus -------------------------------------------------


class FakeMethod:
    def __init__(self, return_value=None, *, raises=None, side_effect=None):
        self.calls = []
        self.return_value = return_value
        self.raises = raises
        self.side_effect = list(side_effect) if side_effect is not None else None

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.side_effect is not None:
            value = self.side_effect.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value
        if self.raises is not None:
            raise self.raises
        return self.return_value


class FakeProxy:
    def __init__(self, bus, name, path, methods):
        self.bus = bus
        self.name = name
        self.path = path
        self.methods = methods

    def get_dbus_method(self, member, dbus_interface=None):
        method = self.bus._lookup(self.name, self.path, member, dbus_interface)
        self.bus.get_dbus_method_calls.append((self.name, self.path, member, dbus_interface))
        return method


def _coerce_method(value):
    if isinstance(value, FakeMethod) or callable(value):
        return value
    if isinstance(value, BaseException):
        return FakeMethod(raises=value)
    return FakeMethod(value)


class FakeBus:
    def __init__(self, owners=(), methods=None, fail_owners=()):
        self.owners = set(owners)
        self.fail_owners = set(fail_owners)
        self._methods = {
            key: _coerce_method(value) for key, value in (methods or {}).items()
        }
        self.name_has_owner_calls = []
        self.get_object_calls = []
        self.get_dbus_method_calls = []
        self.calls = []
        self._proxies = {}

    def name_has_owner(self, name):
        self.name_has_owner_calls.append(name)
        if name in self.fail_owners:
            raise RuntimeError("falha ao consultar dono")
        return name in self.owners

    def set_owner(self, name, owned=True):
        if owned:
            self.owners.add(name)
        else:
            self.owners.discard(name)

    def add_method(self, key, method):
        self._methods[key] = _coerce_method(method)

    def get_object(self, name, path):
        self.get_object_calls.append((name, path))
        proxy = self._proxies.get((name, path))
        if proxy is None:
            proxy = FakeProxy(self, name, path, self._methods)
            self._proxies[(name, path)] = proxy
        return proxy

    def _lookup(self, name, path, member, dbus_interface):
        for key in (
            (name, path, member),
            (name, member),
            (name, dbus_interface, member),
            (name, dbus_interface, "Properties", member),
            member,
        ):
            if key in self._methods:
                method = self._methods[key]
                break
        else:
            method = FakeMethod()
        if isinstance(method, FakeMethod):
            return lambda *args, **kwargs: self._invoke(name, path, member, method, args, kwargs)
        return method

    def _invoke(self, name, path, member, method, args, kwargs):
        self.calls.append((name, path, member, args))
        return method(*args, **kwargs)


class FakeSystemd:
    def __init__(self, alive=False, *, start_raises=None, stop_raises=None):
        self.alive = alive
        self.start_raises = start_raises
        self.stop_raises = stop_raises
        self.calls = []

    def start(self):
        self.calls.append("start")
        if self.start_raises is not None:
            raise self.start_raises
        self.alive = True

    def stop(self):
        self.calls.append("stop")
        if self.stop_raises is not None:
            raise self.stop_raises
        self.alive = False


class FakeScreen:
    def __init__(
        self,
        *,
        backend="fdo",
        needs_verification=False,
        confirm_value=True,
        acquire_raises=None,
        release_raises=None,
        on_acquire=None,
        on_confirm=None,
    ):
        self.backend = backend
        self.needs_verification = needs_verification
        self.confirm_value = confirm_value
        self.acquire_raises = acquire_raises
        self.release_raises = release_raises
        self.on_acquire = on_acquire
        self.on_confirm = on_confirm
        self.calls = []
        self.cookie = None
        self.acquired_cookie = None
        self.confirm_calls = 0

    def acquire(self):
        self.calls.append("acquire")
        if self.on_acquire is not None:
            self.on_acquire()
        if self.acquire_raises is not None:
            raise self.acquire_raises
        self.acquired_cookie = 4242
        self.cookie = self.acquired_cookie
        return self.cookie

    def confirm(self):
        self.calls.append("confirm")
        self.confirm_calls += 1
        if self.on_confirm is not None:
            self.on_confirm()
        if isinstance(self.confirm_value, BaseException):
            raise self.confirm_value
        return self.confirm_value

    def release(self):
        self.calls.append("release")
        if self.release_raises is not None:
            raise self.release_raises
        self.cookie = None


class FakeScheduler:
    def __init__(self):
        self.scheduled = {}
        self.delays = []
        self.cancelled = []
        self._next_id = 1

    def schedule(self, delay, callback):
        source_id = self._next_id
        self._next_id += 1
        self.scheduled[source_id] = (delay, callback)
        self.delays.append(delay)
        return source_id

    def cancel(self, source_id):
        self.cancelled.append(source_id)
        self.scheduled.pop(source_id, None)

    def fire(self):
        results = []
        for source_id, (_delay, callback) in list(self.scheduled.items()):
            result = callback()
            results.append(result)
            if result is False or result == 0:
                self.scheduled.pop(source_id, None)
        return results


class FakeStream:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeProcess:
    def __init__(
        self,
        pid=4242,
        *,
        poll_return=None,
        wait_results=None,
        communicate_result=(b"", b""),
    ):
        self.pid = pid
        self._poll_return = poll_return
        self._wait_results = list(wait_results or [])
        self.communicate_result = communicate_result
        self.stderr = FakeStream()
        self.waits = []

    def set_poll(self, value):
        self._poll_return = value

    def poll(self):
        return self._poll_return

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self._wait_results:
            result = self._wait_results.pop(0)
            if isinstance(result, BaseException):
                raise result
            return result
        return 0

    def communicate(self, timeout=None):
        return self.communicate_result


@pytest.fixture
def fake_bus():
    def make_bus(owners=(), methods=None, fail_owners=()):
        return FakeBus(owners=owners, methods=methods or {}, fail_owners=fail_owners)

    return make_bus


@pytest.fixture
def fake_systemd():
    return FakeSystemd


@pytest.fixture
def fake_screen():
    return FakeScreen


@pytest.fixture
def fake_scheduler():
    return FakeScheduler


@pytest.fixture
def fake_process():
    return FakeProcess


@pytest.fixture
def fake_method():
    return FakeMethod


@pytest.fixture
def fake_popen(monkeypatch):
    def install(process, *, raises=None):
        calls = []

        def popen(args, **kwargs):
            calls.append((args, kwargs))
            if raises is not None:
                raise raises
            return process

        import core.inhibitors

        monkeypatch.setattr(core.inhibitors.subprocess, "Popen", popen)
        return calls

    return install


# --- harness de integração ----------------------------------------------------


def wait_until(predicate, timeout=5.0, interval=0.02):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # a condição pode falhar enquanto sobe
            last_error = exc
        try:
            context = GLib.MainContext.default()
            while context.pending():
                context.iteration(False)
        except Exception:
            pass
        time.sleep(interval)
    raise AssertionError(
        f"timeout de {timeout}s aguardando condição; último erro: {last_error}"
    )


def _connect(address):
    bus = dbus.bus.BusConnection(address)
    bus.set_exit_on_disconnect(False)
    return bus


def session_bus():
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    if not address:
        pytest.skip("teste de integração requer dbus-run-session")
    return _connect(address)


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def child_pids(pid):
    result = subprocess.run(
        ["ps", "--ppid", str(pid), "-o", "pid="],
        capture_output=True,
        text=True,
        check=False,
    )
    pids = []
    for token in result.stdout.split():
        try:
            pids.append(int(token))
        except ValueError:
            pass
    return pids


def inhibit_pids():
    result = subprocess.run(
        ["systemd-inhibit", "--list", "--no-pager"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    lines = result.stdout.splitlines()
    if not lines:
        return set()
    header = lines[0].split()
    if "PID" not in header:
        return set()
    pid_index = header.index("PID")
    pids = set()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) <= pid_index:
            continue
        try:
            pids.add(int(parts[pid_index]))
        except ValueError:
            pass
    return pids


def pid_exists(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_names(names, timeout=5.0, address=None):
    if not names:
        return
    bus = _connect(address) if address else session_bus()
    try:
        wait_until(
            lambda: all(bus.name_has_owner(name) for name in names),
            timeout=timeout,
        )
    finally:
        bus.close()


class FakeHandle:
    def __init__(self, proc, log_path, names):
        self.proc = proc
        self.pid = proc.pid
        self.log_path = Path(log_path)
        self.names = tuple(names)

    def entries(self):
        return read_jsonl(self.log_path)

    def terminate(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)


def _start_fake(script, flags, log_path, names, env_extra=None, timeout=5.0, label=""):
    command = [sys.executable, str(script), *flags, "--log", str(log_path)]
    env = os.environ.copy()
    if env_extra:
        env.update({key: str(value) for key, value in env_extra.items()})
    proc = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_names(
            names,
            timeout=timeout,
            address=env.get("DBUS_SESSION_BUS_ADDRESS"),
        )
    except Exception:
        proc.kill()
        stderr = proc.communicate()[1].decode(errors="replace")
        raise AssertionError(f"{label} não subiu: {stderr}")
    return FakeHandle(proc, log_path, names)


def start_fake_screensaver(*flags, log_path, env_extra=None, timeout=5.0):
    names = [SCREENSAVER_NAMES[flag] for flag in flags if flag in SCREENSAVER_NAMES]
    return _start_fake(
        FAKE_SCREENSAVER,
        flags,
        log_path,
        names,
        env_extra=env_extra,
        timeout=timeout,
        label="fake_screensaver",
    )


def start_fake_policyagent(*flags, log_path, env_extra=None, timeout=5.0):
    return _start_fake(
        FAKE_POLICYAGENT,
        flags,
        log_path,
        [POLICYAGENT_NAME],
        env_extra=env_extra,
        timeout=timeout,
        label="fake_policyagent",
    )


class DaemonHandle:
    def __init__(self, proc, bus, log_path, home, stderr_path):
        self.proc = proc
        self.pid = proc.pid
        self.bus = bus
        self.log_path = Path(log_path)
        self.home = Path(home)
        self.stderr_path = Path(stderr_path)
        self.signals = []
        self.bus.add_signal_receiver(
            self._on_state_changed,
            signal_name="StateChanged",
            dbus_interface=INTERFACE,
            path=OBJECT_PATH,
        )

    def _on_state_changed(self, state):
        self.signals.append(str(state))

    def _call(self, method, *args):
        proxy = self.bus.get_object(DBUS_NAME, OBJECT_PATH)
        interface = dbus.Interface(proxy, INTERFACE)
        return getattr(interface, method)(*args)

    def state(self):
        return str(self._call("GetState"))

    def last_error(self):
        return str(self._call("GetLastError"))

    def set_active(self, active):
        return str(self._call("SetActive", dbus.Boolean(active)))

    def toggle(self):
        return str(self._call("Toggle"))

    def quit(self):
        try:
            self._call("Quit")
        except dbus.DBusException:
            pass

    def wait_exit(self, timeout=5.0):
        return self.proc.wait(timeout=timeout)

    def terminate(self):
        children = child_pids(self.pid)
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)
        for child in children:
            if pid_exists(child):
                try:
                    os.kill(child, signal.SIGKILL)
                except OSError:
                    pass
        try:
            self.bus.close()
        except Exception:
            pass


def start_daemon(
    *,
    verify_delay=None,
    debounce=None,
    confirm_delay=None,
    log_path=None,
    home=None,
    env_extra=None,
    address=None,
    wait_ready=True,
    timeout=8.0,
):
    home_path = Path(home) if home is not None else Path(
        tempfile.mkdtemp(prefix="deskawake-home-")
    )
    home_path.mkdir(parents=True, exist_ok=True)
    log_file = Path(log_path) if log_path is not None else home_path / "daemon.log"
    overrides = {}
    if verify_delay is not None:
        overrides["verify_delay"] = verify_delay
    if debounce is not None:
        overrides["debounce"] = debounce
    if confirm_delay is not None:
        overrides["confirm_delay"] = confirm_delay
    overrides["log_path"] = str(log_file)
    arguments = ", ".join(f"{key}={value!r}" for key, value in overrides.items())
    code = f"import core.daemon as d; raise SystemExit(d.main({arguments}))"

    stderr_path = home_path / "daemon.stderr"
    stderr_file = open(stderr_path, "w", encoding="utf-8")
    env = os.environ.copy()
    env["HOME"] = str(home_path)
    if env_extra:
        env.update({key: str(value) for key, value in env_extra.items()})
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
        )
    finally:
        stderr_file.close()

    bus = _connect(address) if address else session_bus()
    handle = DaemonHandle(proc, bus, log_file, home_path, stderr_path)
    if wait_ready:
        try:
            wait_until(
                lambda: bus.name_has_owner(DBUS_NAME),
                timeout=timeout,
            )
        except Exception:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
            stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
            raise AssertionError(f"daemon não publicou o nome: {stderr}")
    return handle


@pytest.fixture
def fake_screensaver_factory(tmp_path):
    handles = []
    counter = itertools.count(1)

    def start(*flags, env_extra=None):
        log_path = tmp_path / f"fake-screensaver-{next(counter)}.jsonl"
        handle = start_fake_screensaver(
            *flags, log_path=log_path, env_extra=env_extra
        )
        handles.append(handle)
        return handle

    yield start
    for handle in reversed(handles):
        handle.terminate()


@pytest.fixture
def fake_policyagent_factory(tmp_path):
    handles = []
    counter = itertools.count(1)

    def start(*flags, env_extra=None):
        log_path = tmp_path / f"fake-policyagent-{next(counter)}.jsonl"
        handle = start_fake_policyagent(
            *flags, log_path=log_path, env_extra=env_extra
        )
        handles.append(handle)
        return handle

    yield start
    for handle in reversed(handles):
        handle.terminate()


@pytest.fixture
def daemon_factory(tmp_path):
    handles = []
    counter = itertools.count(1)

    def start(**kwargs):
        number = next(counter)
        home = kwargs.pop("home", None)
        if home is None:
            home = tmp_path / f"home-{number}"
        if "log_path" not in kwargs:
            kwargs["log_path"] = tmp_path / f"daemon-{number}.log"
        handle = start_daemon(home=home, **kwargs)
        handles.append(handle)
        return handle

    yield start
    for handle in reversed(handles):
        handle.terminate()


@pytest.fixture
def helpers():
    return SimpleNamespace(
        wait_until=wait_until,
        read_jsonl=read_jsonl,
        child_pids=child_pids,
        inhibit_pids=inhibit_pids,
        pid_exists=pid_exists,
        session_bus=session_bus,
    )


@pytest.fixture
def control_bus():
    bus = session_bus()
    yield bus
    bus.close()


def pytest_collection_modifyitems(config, items):
    markexpr = config.getoption("markexpr", default="") or ""
    if "slow" in markexpr:
        return
    skip = pytest.mark.skip(reason="teste slow opt-in (use -m slow)")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
