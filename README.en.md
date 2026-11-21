# DeskAwake

A desktop widget that keeps your screen on and your system awake while you need it — no conventional window, no taskbar entry, no `Alt+Tab`.

Runs on **Linux Mint 22.3 MATE (X11)** and **Kubuntu 26.04 / KDE Plasma 6.6 (Wayland)**, with a shared Python core and two interfaces: a GTK3 widget on MATE and a native Plasma widget on KDE.

> Version `0.1.0`, MIT license. Documentation in Brazilian Portuguese: [`README.md`](README.md).

## Supported systems

- **Linux Mint 22.3 MATE/X11** — GTK3 widget, `org.mate.ScreenSaver` backend and `systemd-inhibit --what=idle`.
- **Kubuntu 26.04 / KDE Plasma 6.6/Wayland** — native Plasmoid, `org.freedesktop.ScreenSaver` backend and `systemd-inhibit --what=idle`.
- Python ≥ 3.10; `python3-gi`, `python3-dbus`, `systemd` and `libglib2.0-bin` (which provides `systemd-inhibit` and `gdbus`).

## What it does and does not do

**Does:**

- Prevents screen lock/blanking and **idle** suspension while the state is `on`.
- Lives on the desktop, behind normal windows and draggable; on Plasma, size and position are remembered by Plasma itself.
- Always starts disabled; quitting the UI releases the locks immediately.
- Provides a single control interface (`deskawake`) for terminals, shortcuts and diagnostics.

**Does not:**

- **Not** block closing the laptop lid (`lid`) or manual suspend (`Suspend` in the system menu or `systemctl suspend`). This is intentional.
- **Not** replace the system screen lock; it only prevents idle blanking/locking.
- **Not** add the Plasmoid to the desktop automatically: you must add it through “Add Widgets”.

## Requirements and `--install-deps`

The installer checks dependencies and never runs `apt` by itself. To print the commands and the current status:

```bash
./install.sh --install-deps
```

Mandatory runtime dependencies:

```bash
apt install python3-gi python3-dbus systemd libglib2.0-bin
```

For the Plasmoid on KDE:

```bash
apt install kpackagetool6
```

Optional (Inter font):

```bash
apt install fonts-inter
```

`kpackagetool6` does not exist on Linux Mint 22.3; on that system the KDE target is unavailable and `--all` degrades with an explicit warning.

## Installation

The installer is **per-user** and does not require administrative privileges. It writes only to `${XDG_DATA_HOME:-~/.local/share}/deskawake`, `~/.local/bin`, `${XDG_DATA_HOME:-~/.local/share}/dbus-1/services`, `~/.config/autostart` and, for the KDE target, `${XDG_DATA_HOME:-~/.local/share}/plasma/plasmoids/org.local.deskawake`.

Without a flag, the desktop is detected from `XDG_CURRENT_DESKTOP`:

```bash
./install.sh
./install.sh --only-mate
./install.sh --only-kde
./install.sh --all
```

- Without a flag: detects MATE or KDE automatically. `--only-mate` installs daemon+GTK; `--only-kde` installs daemon+Plasmoid; `--all` installs everything available.

- `--all` on Linux Mint 22.3: installs daemon+GTK, prints `KDE indisponível: kpackagetool6 ausente` and exits successfully while making it clear that daemon+GTK were installed.
- `--only-kde` without `kpackagetool6`: fails with `alvo KDE indisponível: kpackagetool6 ausente` and copies nothing.
- In a Wayland session with the GTK target active, the installer warns that the GTK widget requires X11; on KDE the supported UI is the Plasmoid.
- On Kubuntu, after installation, open “Add Widgets” and drag DeskAwake to the desktop.
- If `~/.local/bin` is not in `PATH`, the installer warns you. To add it for Bash:
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```
- Re-running the installer is idempotent. Upgrading does **not** stop a running daemon; the new version starts on the next login or daemon restart. To apply it immediately, stop the daemon and let the `.service` activate the new version on the next action:
  ```bash
  gdbus call --session --dest org.local.DeskAwake --object-path /org/local/DeskAwake --method org.local.DeskAwake.Quit
  deskawake on
  ```

## Usage

CLI:

```bash
deskawake on       # turns on; prints "on"
deskawake off      # turns off; prints "off"
deskawake toggle   # toggles
deskawake status   # 0 = on, 1 = off/error, 3 = daemon unreachable
deskawake daemon   # runs the daemon in the foreground
deskawake ui       # opens the GTK widget (refuses Wayland without --force)
```

On the MATE GTK widget, click the toggle to turn it on/off. The menu offers `Ativar/Desativar`, `Tema`, `Iniciar com o sistema`, `Sobre o DeskAwake…` and `Sair` (kill switch). `Sobre o DeskAwake…` shows the author, website and MIT license.

On Plasma, use the Plasmoid toggle or the hamburger menu with `Ativar/Desativar` and `Sair`. Size and position are managed by Plasma.

## Diagnostics

```bash
./verify.sh
deskawake status
```

`verify.sh` prints one `[ok]`/`[falha]` line per check and ends with `verify: OK` or `verify: FALHOU`. It always ends with DeskAwake **OFF**, even on failure.

Other resources:

- `GetLastError()` over D-Bus returns the reason for the last error.
- `~/.local/state/deskawake/daemon.log` is the daemon log, rotated to `daemon.log.1` at 256 KB.
- `systemd-inhibit --list` shows the `DeskAwake` inhibition while the state is `on`.
- On MATE, `GetInhibitors` from `org.mate.ScreenSaver` lists the `deskawake` application; when available, `mate-screensaver-command -q` complements the diagnosis.
- On KDE, `PolicyAgent.ActiveInhibitions` lists `deskawake`/`DeskAwake active` after the ~5 s debounce; `HasInhibition(4)` confirms the block during ON.

## Limitations

- **KDE:** PowerDevil applies `AddInhibition(4)` after ~5 s (debounce). The ON is therefore optimistic and asynchronous confirmation happens in ~6 s; `verify.sh` waits up to 8 s.
- **Lid and manual suspend:** both still work while the state is `on`. Closing the lid still suspends the laptop; `systemctl suspend` and the system menu do too. Do not use DeskAwake to keep a closed laptop running.
- **Plasmoid:** adding it to the desktop is manual, through “Add Widgets”; `install.sh` only installs the package.
- **`kpackagetool6`:** absent on Mint 22.3, so the KDE target is unavailable on that distribution.
- **GTK on Wayland:** the GTK widget is blocked on Wayland; `--force` (or `DESKAWAKE_FORCE_UI=1`) is for debugging only.
- **Plasmoid `Configure`:** opens Plasma's native configuration, but without custom categories.
- **Upgrade:** `install.sh` does not stop a running daemon; the previous version stays active until the next login/restart.
- **`verify.sh`:** always ends OFF; do not use the script as a way to leave DeskAwake on.
- **MATE — “Show Desktop”:** Marco (Ctrl+Alt+D) may hide the widget; it returns when the desktop is restored. This is a known limitation; the window type is not changed to avoid breaking click/drag.
- **MATE — `auto` theme:** resolves the theme by name (`*Dark*`), because `gtk-application-prefer-dark-theme` does not exist in `org.mate.interface` on Mint 22.3.
- **MATE — `error` state:** a backend drop preserves the `systemd-inhibit` child and releases the screen inhibitor; an activation/verification failure releases everything.
- **MATE — `IsInhibited(8)`:** does not exist in `mate-screensaver` 1.26.2; diagnostics use `GetInhibitors` and, when available, `mate-screensaver-command -q`.
- **Idle on MATE:** `idle-delay` is read at login; testing a short interval requires a new session. `lock-enabled` is destructive/optional.
- **`CanSuspend`:** does not reflect DeskAwake inhibitors and is not used as a test.
- **Paths with spaces:** supported and quoted in generated files; paths with quotes or line breaks are not supported.
- **Manual pending items:** logout, external monitor disconnect and screen lock still need to be exercised manually.

## Development and tests

Development dependency (not installed by `install.sh`):

```bash
sudo apt install python3-pytest
```

Unit tests:

```bash
python3 -m pytest
```

Integration tests in a private D-Bus session:

```bash
dbus-run-session -- python3 -m pytest
```

The opt-in real-cycle test (debounce of ~5–6 s) does not run by default:

```bash
python3 -m pytest tests/integration -m slow
```

Script syntax and optional lint:

```bash
bash -n install.sh uninstall.sh verify.sh
shellcheck install.sh uninstall.sh verify.sh    # when available
```

## Manual checklist — Linux Mint 22.3 MATE/X11

> The GTK UI was validated on the Mint machine; this checklist covers installation, uninstallation and the remaining manual items.

- [ ] Widget opens in the top-right corner, 24 px margin, without decorations.
- [ ] It does not appear in `Alt+Tab`, the taskbar or the pager; it appears on all workspaces. Explicitly verify `keep_below`, `skip_taskbar`, `skip_pager` and `stick()` (create a second workspace: the validation machine has only 1).
- [ ] It stays behind normal windows. **“Show Desktop” (Ctrl+Alt+D):** the widget is hidden and returns when the desktop is restored; the attempt to observe `_NET_SHOWING_DESKTOP` and show it once was dropped (Marco ignores deiconify and `present()` restores all windows); if flicker appears or dragging breaks, record the limitation.
- [ ] Dragging works from any point, including over the toggle; dragging > 5 px does not toggle.
- [ ] Clicking the toggle toggles; clicking outside changes nothing.
- [ ] During `Toggle`/`SetActive`, the two-arrow spinner appears and the toggle is blocked until the response; no amber.
- [ ] With the Marco compositor disabled, the surface is solid and legible; with the compositor enabled, translucency appears.
- [ ] Position survives logout; disconnecting an external monitor resets the widget to the default position.
- [ ] Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sobre o DeskAwake…`, `Sair`; `Sobre` shows author, website and MIT, without a copyright symbol or CNPJ.
- [ ] `Sair` while ON releases immediately (`systemd-inhibit --list` without `deskawake`; `GetInhibitors` empty; if `mate-screensaver-command` exists, `-q` without `deskawake`). `IsInhibited(8)` is not used (absent in mate-screensaver 1.26.2).
- [ ] `kill -9` on the daemon leaves no orphan `systemd-inhibit` and no stuck screen.
- [ ] With `mate-screensaver` idle/lock enabled, ON prevents blanking/locking; after OFF, behavior returns. (On this machine idle/lock are disabled; enable temporarily.) The `idle-delay` of `org.mate.session` is read at login; to test 1 min, open a new session. `lock-enabled` is destructive/optional.
- [ ] Manual suspend (`systemctl suspend`/menu) works while ON. (Destructive test; optional.)
- [ ] Closing the lid suspends while ON. (Requires a laptop; this machine is a desktop without a lid.)
- [ ] Switching `Mint-Y` ↔ `Mint-Y-Dark` updates the widget theme without restarting.
- [ ] Without Inter, the widget uses Ubuntu/Noto Sans without `@font-face` errors.
- [ ] The `error` state caused by a **backend drop** (e.g., killing `mate-screensaver`) shows the tooltip/`GetLastError()` and **preserves** the `systemd-inhibit` child (the MATE inhibitor is released). An **activation/verification failure** goes to `error` releasing everything.
- [ ] Pending items not executed on 2026-11-21: logout, external monitor disconnect and screen lock; record them in the PR/README.

## Manual checklist — Kubuntu 26.04 / Plasma 6.6 Wayland

- [ ] `kpackagetool6 -t Plasma/Applet -i ./plasmoid` installs to `~/.local/share/plasma/plasmoids/org.local.deskawake/`; `--upgrade` updates it. Re-running `./install.sh --all` does not fail (idempotent); `--install-deps` prints the `apt` commands (mandatory × optional `fonts-inter`) and does not run administrative commands.
- [ ] The Plasmoid added to the desktop shows the preferred initial size (184×48); the widget explorer shows `preview.png`; the widget is resizable from 168×44 to 300×84 with Plasma handles.
- [ ] Drag: press and hold moves the widget (native Plasma behavior); a quick click on the toggle toggles and does **not** move it; clicking the hamburger opens the menu and does not start a drag; the rest of the pill remains draggable. If it does not drag, check “Locked Widgets” in the desktop menu.
- [ ] Toggle reflects `on/off/error` in real time (native transport, no polling); removing the Plasmoid does not turn off the state of other clients.
- [ ] Menu: hamburger and right-click share the same actions — `Ativar/Desativar` (dynamic label), `Sair` (kill switch) and native Plasma items; while `callPending`, `Ativar/Desativar` and `Sair` are disabled and configure/remove remain enabled. `Sair` while ON releases immediately (`ActiveInhibitions` without `deskawake`, `systemd-inhibit --list` without `deskawake`).
- [ ] Two-arrow spinner during the in-flight call (toggle blocked) and during the ~6 s verification (toggle still `on`, click accepted); turning off before 6 s cancels verification without `error`; failure after ~6 s becomes `error` + tooltip.
- [ ] `deskawake ui` refuses Wayland with a message; `--force` opens it for debugging.
- [ ] **PowerDevil/idle**: with ON, idle auto-suspend is blocked (dim/DPMS/screen lock too). Check `PolicyAgent.ActiveInhibitions` **after ~6 s** (~5 s `AddInhibition` debounce); `HasInhibition(4)` must become `true`. Do not use `CanSuspend` as a test.
- [ ] **Lid/manual suspend**: with ON, closing the lid and manual suspend still suspend (the `sleep` inhibitor is not held; PowerDevil paths are `Explicit=true`). Destructive test; the machine is a laptop.
- [ ] **Cookie**: another connection can call `UnInhibit` (no ownership); killing the daemon releases the inhibition (PowerDevil watches the connection). The isolation test does **not** apply to KDE.
- [ ] **PowerDevil drop**: `systemctl --user restart plasma-powerdevil` (or killing `org_kde_powerdevil`) while ON → `error` state + `StateChanged`; when it returns, reacquire and go back to `on` after ~6 s, without a retry burst.
- [ ] **`error` state** caused by a backend drop (e.g., PowerDevil/`org.freedesktop.ScreenSaver` absent) shows the reason in the tooltip/`GetLastError()` and **preserves** the `systemd-inhibit` child; an activation/verification failure goes to `error` releasing everything.
- [ ] **Plasmoid theme/font**: in BreezeDark and in a light theme, the chip follows the wallpaper tone (dark over dark, light over light); ink, logo, border and spinner follow; state colors (mint/gray/red) remain fixed and legible.
- [ ] **Adaptive chip**: changing the wallpaper or moving/resizing the widget resamples the region; an ambiguous background (medium gray) does not flicker; with a video/slideshow wallpaper without an observable signal, the variant remains until the next event; without a wallpaper object, it falls back to the Plasma theme.

## Uninstallation

```bash
./uninstall.sh
./uninstall.sh --purge
```

The uninstaller stops the daemon (`Quit()` and, if needed, PID fallback), closes the GTK UI, removes the Plasmoid, launcher, `.service`, autostarts, code and log/state. It is idempotent, tolerates a missing `kpackagetool6` and never removes `~/.config` without `--purge`.

## Credits and license

Developed by **Marcelo Silva · Maniva Software** — [https://manivasoftware.com.br](https://manivasoftware.com.br).

Version `0.1.0`. MIT license.

Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79

The development specification is at [`docs/implementation/spec.md`](docs/implementation/spec.md).
