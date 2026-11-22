"""Smoke tests de ``install.sh`` e ``uninstall.sh`` em ``HOME`` isolado.

Nenhum daemon, GUI ou sessão D-Bus real é usado: ``HOME``, ``XDG_DATA_HOME`` e
``PATH`` apontam para ``tmp_path`` e ``kpackagetool6``/``gdbus`` são scripts
falsos que registram as chamadas. ``verify.sh`` não é executado aqui; seu
contrato é estático e a validação real é manual.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

FAKE_PYTHON = """
#!/bin/sh
if [ "$1" = "-c" ]; then
    exit 0
fi
exec "{real_python}" "$@"
"""

FAKE_SYSTEMD_INHIBIT = """
#!/bin/sh
exit 0
"""

FAKE_KPKG = """
#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

log = Path(os.environ["KPKG_LOG"])
with log.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")

if os.environ.get("KPKG_FAIL") == "1":
    sys.exit(1)

args = sys.argv[1:]
target = (
    Path(os.environ["XDG_DATA_HOME"])
    / "plasma"
    / "plasmoids"
    / "org.local.deskawake"
)
if "-r" in args:
    shutil.rmtree(target, ignore_errors=True)
elif "-i" in args or "-u" in args:
    target.mkdir(parents=True, exist_ok=True)
    (target / "metadata.json").write_text("{}\\n", encoding="utf-8")
sys.exit(0)
"""

FAKE_GDBUS = """
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
log = Path(os.environ["GDBUS_LOG"])
with log.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\\n")

state_path = Path(os.environ["GDBUS_STATE"])
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except (OSError, ValueError):
    state = {}


def save():
    state_path.write_text(json.dumps(state), encoding="utf-8")


method = ""
for index, arg in enumerate(args):
    if arg == "--method":
        method = args[index + 1]

if method.endswith("NameHasOwner"):
    name = args[-1]
    owner = state.get(name)
    print("(true,)" if owner not in (None, 0) else "(false,)")
elif method.endswith(".Quit"):
    dest = ""
    for index, arg in enumerate(args):
        if arg == "--dest":
            dest = args[index + 1]
    if os.environ.get("GDBUS_QUIT_NOOP") != "1" and dest:
        state[dest] = None
        save()
    print("()")
elif method.endswith("GetConnectionUnixProcessID"):
    pid = state.get(args[-1])
    if pid in (None, 0):
        print("(uint32 0,)", file=sys.stderr)
        sys.exit(1)
    print(f"(uint32 {pid},)")
else:
    print("()")
"""


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    path.chmod(0o755)


def _snapshot(*roots: Path) -> dict[str, tuple[int, bytes]]:
    snapshot: dict[str, tuple[int, bytes]] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            key = str(path)
            if path.is_file():
                snapshot[key] = (
                    stat.S_IMODE(path.stat().st_mode),
                    path.read_bytes(),
                )
            elif path.is_dir():
                snapshot[key] = (stat.S_IMODE(path.stat().st_mode), b"")
    return snapshot


class Sandbox:
    def __init__(self, root: Path, env: dict[str, str]) -> None:
        self.root = root
        self.home = root / "home"
        self.data = root / "data"
        self.bin = root / "bin"
        self.env = env
        self.kpkg_log = root / "kpackagetool6.log"
        self.gdbus_log = root / "gdbus.log"
        self.gdbus_state = root / "gdbus-state.json"

    @property
    def share(self) -> Path:
        return self.data / "deskawake"

    @property
    def launcher(self) -> Path:
        return self.home / ".local" / "bin" / "deskawake"

    @property
    def service(self) -> Path:
        return (
            self.data
            / "dbus-1"
            / "services"
            / "org.local.DeskAwake.service"
        )

    @property
    def autostart(self) -> Path:
        return self.home / ".config" / "autostart"

    @property
    def plasmoid(self) -> Path:
        return (
            self.data
            / "plasma"
            / "plasmoids"
            / "org.local.deskawake"
        )

    def run(
        self,
        script: str,
        *args: str,
        env_extra: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [str(REPO_ROOT / script), *args],
            cwd=cwd or REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )

    def _calls(self, path: Path) -> list[list[str]]:
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def kpkg_calls(self) -> list[list[str]]:
        return self._calls(self.kpkg_log)

    def gdbus_calls(self) -> list[list[str]]:
        return self._calls(self.gdbus_log)

    def read_owners(self) -> dict[str, int | None]:
        try:
            return json.loads(self.gdbus_state.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def set_owner(self, name: str, pid: int) -> None:
        owners = self.read_owners()
        owners[name] = pid
        self.gdbus_state.write_text(json.dumps(owners), encoding="utf-8")

    def snapshot(self) -> dict[str, tuple[int, bytes]]:
        return _snapshot(self.home, self.data)


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    home = tmp_path / "home"
    data = tmp_path / "data"
    bin_dir = tmp_path / "bin"
    for directory in (home, data, bin_dir):
        directory.mkdir()

    env = dict(os.environ)
    for name in (
        "XDG_CURRENT_DESKTOP",
        "XDG_SESSION_TYPE",
        "WAYLAND_DISPLAY",
        "KPKG_TOOL",
        "KPKG_FAIL",
        "GDBUS_QUIT_NOOP",
        "KPKG_LOG",
        "GDBUS_LOG",
        "GDBUS_STATE",
    ):
        env.pop(name, None)

    env.update(
        HOME=str(home),
        XDG_DATA_HOME=str(data),
        PATH=f"{bin_dir}:{env.get('PATH', '')}",
        KPKG_LOG=str(tmp_path / "kpackagetool6.log"),
        GDBUS_LOG=str(tmp_path / "gdbus.log"),
        GDBUS_STATE=str(tmp_path / "gdbus-state.json"),
    )
    (tmp_path / "gdbus-state.json").write_text("{}", encoding="utf-8")
    real_python = shutil.which("python3")
    assert real_python is not None
    _write_executable(
        bin_dir / "python3", FAKE_PYTHON.format(real_python=real_python)
    )
    _write_executable(bin_dir / "systemd-inhibit", FAKE_SYSTEMD_INHIBIT)
    _write_executable(bin_dir / "kpackagetool6", FAKE_KPKG)
    _write_executable(bin_dir / "gdbus", FAKE_GDBUS)

    return Sandbox(tmp_path, env)


def test_sandbox_is_isolated(sandbox: Sandbox):
    assert Path(sandbox.env["HOME"]) == sandbox.home
    assert Path(sandbox.env["XDG_DATA_HOME"]) == sandbox.data
    assert sandbox.env["PATH"].split(":")[0] == str(sandbox.bin)

    for name in ("python3", "systemd-inhibit", "kpackagetool6", "gdbus"):
        fake = sandbox.bin / name
        assert fake.is_file()
        assert os.access(fake, os.X_OK)


# --- install.sh ---------------------------------------------------------------


def test_install_only_mate_copies_code(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--only-mate")

    assert result.returncode == 0, result.stderr
    assert (sandbox.share / "core").is_dir()
    assert (sandbox.share / "ui_gtk").is_dir()
    assert (sandbox.share / "assets").is_dir()
    assert (sandbox.share / "data" / "deskawake-widget.desktop").is_file()

    binary = sandbox.share / "bin" / "deskawake"
    assert binary.is_file()
    assert stat.S_IMODE(binary.stat().st_mode) == 0o755


def test_install_only_mate_renders_files(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--only-mate")

    assert result.returncode == 0, result.stderr
    exec_path = sandbox.share / "bin" / "deskawake"

    launcher = sandbox.launcher
    assert launcher.is_file()
    assert stat.S_IMODE(launcher.stat().st_mode) == 0o755
    launcher_text = launcher.read_text(encoding="utf-8")
    assert launcher_text.startswith("#!/bin/sh")
    assert str(exec_path) in launcher_text
    assert "@EXEC@" not in launcher_text

    service = sandbox.service
    assert service.is_file()
    assert stat.S_IMODE(service.stat().st_mode) == 0o644
    service_text = service.read_text(encoding="utf-8")
    assert f"Exec={exec_path} daemon" in service_text
    assert "@EXEC@" not in service_text

    daemon_entry = sandbox.autostart / "deskawake-daemon.desktop"
    widget_entry = sandbox.autostart / "deskawake-widget.desktop"
    assert daemon_entry.is_file()
    assert widget_entry.is_file()
    assert stat.S_IMODE(daemon_entry.stat().st_mode) == 0o644
    assert stat.S_IMODE(widget_entry.stat().st_mode) == 0o644

    daemon_text = daemon_entry.read_text(encoding="utf-8")
    widget_text = widget_entry.read_text(encoding="utf-8")
    assert f"Exec={exec_path} daemon" in daemon_text
    assert f"Exec={exec_path} ui" in widget_text
    assert "OnlyShowIn=MATE;" in widget_text
    assert "@EXEC@" not in daemon_text
    assert "@EXEC@" not in widget_text


def test_install_only_mate_does_not_call_kpackagetool6(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--only-mate")

    assert result.returncode == 0, result.stderr
    assert sandbox.kpkg_calls() == []


def test_install_only_mate_is_idempotent(sandbox: Sandbox):
    first = sandbox.run("install.sh", "--only-mate")
    assert first.returncode == 0, first.stderr
    before = sandbox.snapshot()

    second = sandbox.run("install.sh", "--only-mate")
    assert second.returncode == 0, second.stderr
    assert sandbox.snapshot() == before

    leftovers = [
        path
        for path in sandbox.root.rglob("*")
        if path.is_file()
        and (".new." in path.name or path.name.endswith(".tmp"))
    ]
    assert leftovers == []


def test_install_does_not_stop_daemon(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--only-mate")

    assert result.returncode == 0, result.stderr
    assert all("Quit" not in call for call in sandbox.gdbus_calls())


def test_install_only_kde_with_tool_installs_daemon_and_plasmoid(
    sandbox: Sandbox,
):
    result = sandbox.run("install.sh", "--only-kde")

    assert result.returncode == 0, result.stderr
    assert (sandbox.share / "core").is_dir()
    assert (sandbox.share / "bin" / "deskawake").is_file()
    assert not (sandbox.share / "ui_gtk").exists()
    assert not (sandbox.share / "assets").exists()
    assert sandbox.service.is_file()
    assert (sandbox.autostart / "deskawake-daemon.desktop").is_file()
    assert not (sandbox.autostart / "deskawake-widget.desktop").exists()
    assert (sandbox.plasmoid / "metadata.json").is_file()

    calls = sandbox.kpkg_calls()
    assert any(call[:3] == ["-t", "Plasma/Applet", "-i"] for call in calls)


def test_install_explicit_flag_wins_over_desktop(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        "--only-mate",
        env_extra={"XDG_CURRENT_DESKTOP": "KDE"},
    )

    assert result.returncode == 0, result.stderr
    assert (sandbox.share / "ui_gtk").is_dir()
    assert not sandbox.plasmoid.exists()


def test_install_all_with_tool_installs_and_upgrades_plasmoid(
    sandbox: Sandbox,
):
    first = sandbox.run("install.sh", "--all")
    assert first.returncode == 0, first.stderr
    first_calls = sandbox.kpkg_calls()
    assert any(
        call[:3] == ["-t", "Plasma/Applet", "-i"] for call in first_calls
    )
    assert (sandbox.plasmoid / "metadata.json").is_file()

    second = sandbox.run("install.sh", "--all")
    assert second.returncode == 0, second.stderr
    second_calls = sandbox.kpkg_calls()[len(first_calls) :]
    assert any(
        call[:3] == ["-t", "Plasma/Applet", "-u"] for call in second_calls
    )


def test_install_all_without_tool_degrades_with_warning(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        "--all",
        env_extra={"KPKG_TOOL": "__missing__"},
    )

    assert result.returncode == 0
    assert "KDE indisponível: kpackagetool6 ausente" in result.stdout
    assert (sandbox.share / "core").is_dir()
    assert (sandbox.share / "ui_gtk").is_dir()
    assert not sandbox.plasmoid.exists()


def test_install_only_kde_without_tool_fails_without_copying(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        "--only-kde",
        env_extra={"KPKG_TOOL": "__missing__"},
    )

    assert result.returncode == 1
    assert (
        "alvo KDE indisponível: kpackagetool6 ausente"
        in result.stdout + result.stderr
    )
    assert not sandbox.share.exists()


def test_install_auto_detects_mate(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        env_extra={"XDG_CURRENT_DESKTOP": "MATE"},
    )

    assert result.returncode == 0, result.stderr
    assert (sandbox.share / "ui_gtk").is_dir()
    assert not sandbox.plasmoid.exists()


def test_install_auto_detects_kde(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        env_extra={"XDG_CURRENT_DESKTOP": "KDE"},
    )

    assert result.returncode == 0, result.stderr
    assert not (sandbox.share / "ui_gtk").exists()
    assert (sandbox.plasmoid / "metadata.json").is_file()


def test_install_unknown_desktop_exits_2(sandbox: Sandbox):
    result = sandbox.run("install.sh")

    assert result.returncode == 2
    assert not sandbox.share.exists()


def test_install_all_unknown_desktop_installs_all(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--all")

    assert result.returncode == 0, result.stderr
    assert (sandbox.share / "ui_gtk").is_dir()
    assert (sandbox.plasmoid / "metadata.json").is_file()


def test_install_rejects_conflicting_flags(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--all", "--only-kde")

    assert result.returncode == 2
    assert not sandbox.share.exists()


def test_install_rejects_unknown_flag(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--wat")

    assert result.returncode == 2
    assert not sandbox.share.exists()


def test_scripts_reject_relative_xdg_data_home(sandbox: Sandbox):
    workdir = sandbox.root / "cwd"
    workdir.mkdir()

    for script in ("install.sh", "uninstall.sh", "verify.sh"):
        result = sandbox.run(
            script,
            env_extra={"XDG_DATA_HOME": "relative"},
            cwd=workdir,
        )

        assert result.returncode == 2, script
        assert "XDG_DATA_HOME" in result.stderr
        assert "caminho absoluto obrigatório" in result.stderr
        assert list(workdir.iterdir()) == [], script


def test_scripts_reject_invalid_home(sandbox: Sandbox):
    workdir = sandbox.root / "cwd"
    workdir.mkdir()

    for script in ("install.sh", "uninstall.sh", "verify.sh"):
        for home in ("", "relative"):
            result = sandbox.run(
                script,
                env_extra={"HOME": home},
                cwd=workdir,
            )

            assert result.returncode == 2, (script, home)
            assert "HOME" in result.stderr
            assert "caminho absoluto obrigatório" in result.stderr
            assert list(workdir.iterdir()) == [], (script, home)

            help_result = sandbox.run(
                script,
                "--help",
                env_extra={"HOME": home},
                cwd=workdir,
            )
            assert help_result.returncode == 0, (script, home)


def test_installer_launcher_quotes_shell_specials(sandbox: Sandbox):
    data = sandbox.root / "data$HOME`id`"
    data.mkdir()

    result = sandbox.run(
        "install.sh",
        "--only-kde",
        env_extra={"XDG_DATA_HOME": str(data)},
    )

    assert result.returncode == 0, result.stderr
    launcher = sandbox.launcher
    text = launcher.read_text(encoding="utf-8")
    assert "$HOME" in text
    assert "`id`" in text

    run = subprocess.run(
        [str(launcher), "--help"],
        cwd=sandbox.root,
        env=dict(sandbox.env, XDG_DATA_HOME=str(data)),
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert run.returncode == 0, run.stderr
    assert "usage: deskawake" in run.stdout


def test_install_renders_paths_with_sed_specials(sandbox: Sandbox):
    data = sandbox.root / "data&pipe|back\\slash"
    data.mkdir()

    result = sandbox.run(
        "install.sh",
        "--only-mate",
        env_extra={"XDG_DATA_HOME": str(data)},
    )

    assert result.returncode == 0, result.stderr
    exec_path = data / "deskawake" / "bin" / "deskawake"
    service = (
        data / "dbus-1" / "services" / "org.local.DeskAwake.service"
    ).read_text(encoding="utf-8")
    assert f"Exec={exec_path} daemon" in service
    assert "@EXEC@" not in service


def test_uninstall_does_not_follow_final_symlinks(sandbox: Sandbox):
    assert sandbox.run("install.sh", "--only-mate").returncode == 0

    canary = sandbox.root / "canary"
    for name in ("share", "state", "config"):
        (canary / name).mkdir(parents=True)
        (canary / name / "keep.txt").write_text(name, encoding="utf-8")

    shutil.rmtree(sandbox.share)
    sandbox.share.symlink_to(canary / "share")

    state_dir = sandbox.home / ".local" / "state" / "deskawake"
    state_dir.mkdir(parents=True)
    shutil.rmtree(state_dir)
    state_dir.symlink_to(canary / "state")

    config_dir = sandbox.home / ".config" / "deskawake"
    config_dir.mkdir(parents=True)
    shutil.rmtree(config_dir)
    config_dir.symlink_to(canary / "config")

    result = sandbox.run("uninstall.sh", "--purge")

    assert result.returncode == 0, result.stderr
    assert not sandbox.share.exists()
    assert not state_dir.exists()
    assert not config_dir.exists()
    for name in ("share", "state", "config"):
        assert (canary / name / "keep.txt").read_text(encoding="utf-8") == name


def test_install_deps_output_has_no_sudo(sandbox: Sandbox):
    result = sandbox.run("install.sh", "--install-deps")

    assert result.returncode == 0, result.stderr
    for block in (
        "Dependências obrigatórias (runtime):",
        "KDE (necessário apenas para o Plasmoid):",
        "Opcional (fonte Inter):",
        "Verificação:",
    ):
        assert block in result.stdout
    assert "sudo" not in result.stdout.lower()


def test_install_deps_only_kde_without_tool_exits_1(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        "--install-deps",
        "--only-kde",
        env_extra={"KPKG_TOOL": "__missing__"},
    )

    assert result.returncode == 1


def test_install_deps_all_exits_0(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        "--install-deps",
        "--all",
        env_extra={"KPKG_TOOL": "__missing__"},
    )

    assert result.returncode == 0


def test_install_handles_home_with_spaces(sandbox: Sandbox):
    home = sandbox.root / "home with space"
    data = sandbox.root / "data with space"
    home.mkdir()
    data.mkdir()

    result = sandbox.run(
        "install.sh",
        "--only-mate",
        env_extra={"HOME": str(home), "XDG_DATA_HOME": str(data)},
    )

    assert result.returncode == 0, result.stderr
    share = data / "deskawake"
    binary = share / "bin" / "deskawake"
    exec_path = f'"{binary}"'
    service = (
        data / "dbus-1" / "services" / "org.local.DeskAwake.service"
    ).read_text(encoding="utf-8")
    assert f"Exec={exec_path} daemon" in service

    daemon_entry = (
        home / ".config" / "autostart" / "deskawake-daemon.desktop"
    ).read_text(encoding="utf-8")
    assert f"Exec={exec_path} daemon" in daemon_entry

    launcher = (home / ".local" / "bin" / "deskawake").read_text(
        encoding="utf-8"
    )
    assert f"exec '{binary}' \"$@\"" in launcher


def test_install_all_plasmoid_failure_exits_1(sandbox: Sandbox):
    result = sandbox.run(
        "install.sh",
        "--all",
        env_extra={"KPKG_FAIL": "1"},
    )

    assert result.returncode == 1


# --- uninstall.sh -------------------------------------------------------------


def test_uninstall_removes_everything_and_preserves_config(sandbox: Sandbox):
    assert sandbox.run("install.sh", "--only-mate").returncode == 0

    config = sandbox.home / ".config" / "deskawake" / "config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("{}", encoding="utf-8")
    state = sandbox.home / ".local" / "state" / "deskawake" / "daemon.log"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("log\n", encoding="utf-8")

    result = sandbox.run("uninstall.sh")

    assert result.returncode == 0, result.stderr
    assert not sandbox.share.exists()
    assert not sandbox.launcher.exists()
    assert not sandbox.service.exists()
    assert not (sandbox.autostart / "deskawake-daemon.desktop").exists()
    assert not (sandbox.autostart / "deskawake-widget.desktop").exists()
    assert not state.parent.exists()
    assert config.is_file()


def test_uninstall_is_idempotent(sandbox: Sandbox):
    assert sandbox.run("install.sh", "--only-mate").returncode == 0

    first = sandbox.run("uninstall.sh")
    assert first.returncode == 0, first.stderr
    after_first = sandbox.snapshot()

    second = sandbox.run("uninstall.sh")
    assert second.returncode == 0, second.stderr
    assert sandbox.snapshot() == after_first


def test_uninstall_purge_removes_config(sandbox: Sandbox):
    assert sandbox.run("install.sh", "--only-mate").returncode == 0
    config_dir = sandbox.home / ".config" / "deskawake"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text("{}", encoding="utf-8")

    result = sandbox.run("uninstall.sh", "--purge")

    assert result.returncode == 0, result.stderr
    assert not config_dir.exists()


def test_uninstall_stops_daemon_by_quit(sandbox: Sandbox):
    sandbox.set_owner("org.local.DeskAwake", 12345)

    result = sandbox.run("uninstall.sh")

    assert result.returncode == 0, result.stderr
    assert any(
        any("Quit" in argument for argument in call)
        for call in sandbox.gdbus_calls()
    )
    assert sandbox.read_owners().get("org.local.DeskAwake") is None


def test_uninstall_falls_back_to_pid(sandbox: Sandbox):
    process = subprocess.Popen(["sleep", "60"])
    try:
        sandbox.set_owner("org.local.DeskAwake", process.pid)

        result = sandbox.run(
            "uninstall.sh",
            env_extra={"GDBUS_QUIT_NOOP": "1"},
        )

        assert result.returncode == 0, result.stderr
        deadline = time.monotonic() + 3
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert process.poll() is not None
        assert any(
            any("GetConnectionUnixProcessID" in argument for argument in call)
            for call in sandbox.gdbus_calls()
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_uninstall_stops_ui_widget(sandbox: Sandbox):
    process = subprocess.Popen(["sleep", "60"])
    try:
        sandbox.set_owner("org.local.DeskAwake.Ui", process.pid)

        result = sandbox.run("uninstall.sh")

        assert result.returncode == 0, result.stderr
        deadline = time.monotonic() + 3
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_uninstall_removes_plasmoid_with_tool(sandbox: Sandbox):
    assert sandbox.run("install.sh", "--all").returncode == 0
    assert (sandbox.plasmoid / "metadata.json").is_file()

    result = sandbox.run("uninstall.sh")

    assert result.returncode == 0, result.stderr
    assert not sandbox.plasmoid.exists()
    calls = sandbox.kpkg_calls()
    assert any(
        call[:3] == ["-t", "Plasma/Applet", "-r"] for call in calls
    )


def test_uninstall_removes_plasmoid_without_tool(sandbox: Sandbox):
    sandbox.plasmoid.mkdir(parents=True)
    (sandbox.plasmoid / "metadata.json").write_text("{}", encoding="utf-8")

    result = sandbox.run(
        "uninstall.sh",
        env_extra={"KPKG_TOOL": "__missing__"},
    )

    assert result.returncode == 0, result.stderr
    assert not sandbox.plasmoid.exists()


def test_uninstall_rejects_unknown_flag(sandbox: Sandbox):
    result = sandbox.run("uninstall.sh", "--wat")

    assert result.returncode == 2
