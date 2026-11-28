# DeskAwake

Keeps your screen on and your system awake while you need it — no conventional window, no taskbar entry, no `Alt+Tab`.

Runs on **Linux Mint 22.3 MATE (X11)** and **Kubuntu 26.04 / KDE Plasma 6.6 (Wayland)**: a GTK3 widget on MATE and a native Plasmoid on Plasma.

> Version `0.1.0`, MIT license. Português: [`README.md`](README.md).

## What it does

- Prevents screen blanking/locking and **idle** suspension while it is on.
- Lives on the desktop, behind normal windows and draggable; on Plasma, size and position are remembered by Plasma itself.
- Always starts off; `Quit` releases the locks immediately.
- Provides the `deskawake` CLI for terminals, shortcuts and diagnostics.

## What it does not do

- **Does not** block closing the laptop lid or manual suspend (`systemctl suspend` or the system menu).
- **Does not** replace the system screen lock; it only prevents idle blanking/locking.
- **Does not** add the Plasmoid automatically: use “Add Widgets”.

## Installation

### Via `.deb` (recommended)

Download the package from [Releases](https://github.com/mhenrique94/deskawake/releases/latest) and install it:

```bash
sudo apt install ./deskawake_0.1.0_all.deb
```

`sudo dpkg -i ./deskawake_0.1.0_all.deb` works as a fallback, but it does not resolve dependencies; run `sudo apt install -f` afterwards.

The package installs for all users under `/usr/lib/deskawake` and `/usr/bin/deskawake`. Configuration (`~/.config/deskawake`) and state (`~/.local/state/deskawake`) remain per-user and are preserved on removal.

### Per-user (no `sudo`)

```bash
./install.sh
./install.sh --only-mate
./install.sh --only-kde
./install.sh --all
```

- Without a flag, the desktop is detected automatically. `--only-mate` installs daemon + GTK widget; `--only-kde`, daemon + Plasmoid; `--all` installs whatever is available.
- To see the dependencies and install commands: `./install.sh --install-deps`.
- If `~/.local/bin` is not in `PATH`, add it for Bash:

  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```

- On Kubuntu, after installing, add DeskAwake through “Add Widgets”.
- `kpackagetool6` does not exist on Linux Mint 22.3; on that system the KDE target is unavailable.

### Coexistence

The two installations should not coexist. Always run `./uninstall.sh` before installing the `.deb`.

- With the system-wide package present, `./install.sh` refuses and asks you to run `apt remove deskawake`.
- `./uninstall.sh` only warns that the package is not removed by it.
- `./verify.sh` accepts both installations and warns if both exist.

### Integrity

Each release publishes the `.deb`, the source code in `deskawake-0.1.0.tar.gz` and `SHA256SUMS`. Download all three and verify them in the downloads directory:

```bash
sha256sum -c SHA256SUMS
```

HTTPS and SHA-256 provide integrity; there is no GPG signature or APT repository.

## Usage

```bash
deskawake on       # turns on; prints "on"
deskawake off      # turns off; prints "off"
deskawake toggle   # toggles
deskawake status   # 0 = on, 1 = off/error, 3 = daemon unreachable
deskawake ui       # opens the GTK widget (refuses Wayland without --force)
```

On MATE, click the widget toggle. The menu offers `Ativar/Desativar`, `Tema`, `Iniciar com o sistema`, `Sobre o DeskAwake…` and `Sair`.

On Plasma, use the Plasmoid toggle or the hamburger menu with `Ativar/Desativar` and `Sair`.

## Updating

Updating is manual: download the `.deb` for the new version and install it over the old one with `sudo apt install ./deskawake_<new>_all.deb`. There is no auto-update or APT repository in this version. The previous version stays active until the next login or until the daemon is restarted.

## Removal

System-wide:

```bash
sudo apt remove deskawake
```

Per-user:

```bash
./uninstall.sh
./uninstall.sh --purge
```

`--purge` also removes `~/.config/deskawake`. Without it, configuration and state are preserved.

## Diagnostics

```bash
deskawake status
./verify.sh
systemd-inhibit --list
```

- `./verify.sh` prints one `[ok]`/`[falha]` line per check and always ends with DeskAwake **OFF**.
- `systemd-inhibit --list` shows the `DeskAwake` inhibition while the state is `on`.
- The log is at `~/.local/state/deskawake/daemon.log`, rotated to `daemon.log.1` at 256 KB.

## Limitations

- **Lid and manual suspend:** both still work while DeskAwake is on. Closing the lid still suspends the laptop; `systemctl suspend` and the system menu do too.
- **Plasmoid:** adding it to the desktop is manual, through “Add Widgets”. After removing the package, it disappears on the next login.
- **`kpackagetool6`:** absent on Mint 22.3, so the KDE target is unavailable on that distribution.
- **GTK on Wayland:** the GTK widget is blocked on Wayland; `--force` is for debugging only.
- **Plasmoid `Configure`:** opens Plasma's native configuration, without custom categories.
- **Updating:** the previous version stays active until the next login or daemon restart.
- **Removal with a running daemon:** after `sudo apt remove deskawake`, an already running daemon continues until logout. Log out and back in to stop it.
- **System-wide autostart:** to disable it for one user, create `~/.config/autostart/deskawake-*.desktop` with `Hidden=true`.
- **MATE — “Show Desktop”:** Marco may hide the widget; it returns when the desktop is restored.

## Credits and license

Developed by **Marcelo Silva · Maniva Software** — [https://manivasoftware.com.br](https://manivasoftware.com.br).

Version `0.1.0`. MIT license.

Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79
