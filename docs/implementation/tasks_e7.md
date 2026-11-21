# Tasks: E7 — Instalação, Desinstalação, Verificação, Testes e Documentação

**Feature:** DeskAwake — E7 | **Data:** 2026-11-21 | **Estimativa:** ≈ 11 h 15 min (30 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 9, 10, 18, 19, 20 e 34–38; “Arquivos instalados”;
tarefas 11–15; checklists manuais), [`design_e7.md`](design_e7.md) (§1–§11),
[`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E7 e [`design_e6.md`](design_e6.md) (UI congelada, versão e
`Sobre`).

## Resumo

- Total de tasks: 30
- Estimativa total: ≈ 11 h 15 min (~1,5 dia de trabalho focado, incluindo as duas checklists manuais)
- Dependências externas: **E6 mergeada na `main`** (a branch da E7 nasce depois dela); Mint 22.3
  MATE/X11 e Kubuntu 26.04.1 / Plasma 6.6.7 disponíveis para a validação manual; `kpackagetool6`
  2.0 no Kubuntu e ausente no Mint; `desktop-file-validate` presente; `shellcheck` ausente nas
  máquinas validadas. **Nenhuma** migration, serviço novo de runtime, dependência Python nova ou
  alteração em `core/`, `ui_gtk/`, `plasmoid/contents/` ou `bin/`.
- Gate **G-E7**: `bash -n` limpo nos três scripts; `install.sh`/`uninstall.sh` idempotentes;
  `verify.sh` verde nos dois backends (manual); `tests/unit/test_scripts.py` e
  `tests/integration/test_installer_scripts.py` verdes; suíte completa sem regressão; READMEs
  completos com créditos e checklists; `git diff -- core ui_gtk plasmoid/contents bin pyproject.toml`
  vazio.
- Fora de escopo (não criar nesta entrega): `.deb`/AUR/Flatpak/AppImage (E8); instalação system-wide;
  alterações de comportamento/contrato D-Bus; testes automatizados de GUI; execução real de
  `verify.sh` na suíte; criação de `config.json` pelo instalador; remoção de `~/.config/deskawake/`
  sem `--purge`; traduções `.po`.
- Referência de comportamento: em conflito, a `spec.md` vence o `design_e7.md`; em seguida vêm
  `DELIVERY_MAP.md` §E7 e `design_e6.md` (UI congelada).
- Este arquivo é um artefato transitório em `docs/implementation/`; **não** entra no PR de código nem
  é citado em código, comentários, commits ou corpo do PR.

**Sequência:** branch/baseline → templates `data/` (TDD) → contratos estáticos (TDD) → sandbox
(TDD) → `install.sh` → `uninstall.sh` → `verify.sh` → READMEs/créditos → gate automatizado →
checklists manuais → auditoria e PR.

**Regras de teste que valem para todas as tasks:**

- **TDD:** as tasks de teste vêm antes das tasks de implementação correspondentes. O RED esperado
  deve ser confirmado (arquivo ausente, `bash -n` falhando ou teste ainda não presente) antes de
  criar o artefato. Se um teste passar antes da implementação, é regressão: registrar e não
  “implementar” o que já existe.
- `tests/unit/test_scripts.py` usa somente stdlib (`configparser`, `json`, `pathlib`, `re`,
  `shutil`, `subprocess`) + `pytest`; **não** importa `gi` nem `dbus`.
- `tests/integration/test_installer_scripts.py` executa os scripts reais em `HOME`/`XDG_DATA_HOME`/
  `PATH` temporários, com `kpackagetool6` e `gdbus` falsos. **Nunca** toca o `HOME` real, não sobe
  daemon, não abre GUI e não usa sessão D-Bus real.
- `verify.sh` **não** é executado na suíte: depende de daemon e backend reais. Seu contrato é
  estático em `test_scripts.py` e a validação é manual (§9.2/§9.3 do design).
- `tests/conftest.py` **não** é alterado; os testes E1–E6 permanecem intactos.
- Mensagens dos scripts em pt-BR, uma linha por evento; caminhos absolutos e entre aspas.
- Nenhum script contém ou imprime `sudo`, `pkexec` ou `su`; o único `sudo` da entrega é o do README
  na seção de desenvolvimento (`sudo apt install python3-pytest`), que é instrução ao usuário.
- Nenhuma referência a `AC-*`, `T-*`, `design_e7.md`, `tasks_e7.md`, `spec.md` ou `DELIVERY_MAP.md`
  em scripts, templates, testes ou código. O README pode linkar a spec como documentação de
  desenvolvedor, conforme o design.

## Priorização

Score = (Impacto × Confiança) / Esforço (H=3, M=2, L=1).

| Grupo | Impacto | Confiança | Esforço | Score | Execução |
|---|---|---|---|---|---|
| Fundação, templates e contratos (T-01–T-07) | 3 | 3 | 2 | 4,5 | Primeiro — destrava todo o resto |
| Sandbox de instalação (T-08–T-10) | 3 | 3 | 3 | 3,0 | Antes dos scripts (TDD); vira o aceite deles |
| Scripts `install`/`uninstall`/`verify` (T-11–T-20) | 3 | 2 | 3 | 2,0 | Neste ciclo — é a entrega em si |
| READMEs e créditos (T-21–T-23) | 3 | 3 | 2 | 4,5 | Após os scripts; testes já escritos em T-07 |
| Gate e checklists manuais (T-24–T-28) | 3 | 2 | 3 | 2,0 | Fecha o G-E7 |
| Auditoria e PR (T-29–T-30) | 2 | 3 | 1 | 6,0 | Último |

Nenhuma task cai em backlog (< 2): o gate só fecha com todas as tasks.

## Tasks

### 0. Setup e fundação

- [ ] **T-01**: Confirmar a E6 na `main` e criar a branch da E7
  - Comandos:
    - `git switch main && git pull --ff-only` ⇒ exit 0
    - `git log --oneline -20 | grep -iE "e6|ui gtk"` ⇒ merge da E6 presente
    - `git switch -c feat/e7-instalador-verificacao-docs` ⇒ branch criada
    - `git branch --show-current` ⇒ `feat/e7-instalador-verificacao-docs`
  - Critério: a `main` contém a E6 mergeada e a branch da E7 nasce dela. Se a E6 ainda não estiver
    mergeada, **parar** e pedir a confirmação do usuário; não criar a E7 sobre a branch de UI.
  - Estimativa: 5min

- [ ] **T-02**: Medir o baseline e conferir as ferramentas
  - Comandos:
    - `python3 -m pytest tests/unit -q` ⇒ **282 passed** (baseline pós-E6), 0 failures
    - `dbus-run-session -- python3 -m pytest tests/integration -q` ⇒ **34 passed, 1 skipped**
    - `command -v python3 gdbus systemd-inhibit desktop-file-validate` ⇒ quatro caminhos
    - `command -v shellcheck || true` ⇒ vazio é esperado e **não** bloqueia
    - `command -v kpackagetool6 || true` ⇒ presente no Kubuntu; ausente no Mint é esperado
    - `test ! -e install.sh && test ! -e uninstall.sh && test ! -e verify.sh && test ! -d data` ⇒ exit 0
  - Critério: baseline verde e lacunas confirmadas (scripts, `data/`, README.en.md e testes de
    scripts ausentes). Registrar a disponibilidade de `shellcheck`/`kpackagetool6` para o gate.
  - Estimativa: 10min

### 1. Templates `data/` (TDD)

- [ ] **T-03**: Escrever os testes RED dos três templates
  - Arquivo: `tests/unit/test_scripts.py` (novo)
  - Estrutura: `REPO_ROOT = Path(__file__).resolve().parents[2]`, `DATA = REPO_ROOT / "data"`;
    helper `_desktop(path)` com `configparser.ConfigParser(interpolation=None)` e
    `optionxform = str` (chaves case-sensitive).
  - Testes:
    - `test_data_contains_only_templates` — `data/` existe e contém exatamente
      `org.local.DeskAwake.service`, `deskawake-daemon.desktop` e `deskawake-widget.desktop`.
    - `test_service_template_contract` — seção `D-BUS Service`; `Name=org.local.DeskAwake`;
      `Exec=@EXEC@ daemon`; nenhuma outra chave obrigatória.
    - `test_daemon_autostart_template_contract` — `Desktop Entry`; `Type=Application`;
      `Name=DeskAwake Daemon`; `Exec=@EXEC@ daemon`; `Terminal=false`; `NoDisplay=true`;
      `X-GNOME-Autostart-enabled=true`.
    - `test_widget_autostart_template_contract` — `Desktop Entry`; `Type=Application`;
      `Name=DeskAwake`; `Exec=@EXEC@ ui`; `Terminal=false`; `NoDisplay=true`;
      `OnlyShowIn=MATE;`; `X-GNOME-Autostart-enabled=true`.
    - `test_templates_have_no_hardcoded_home` — nenhum arquivo contém `/home/`.
    - `test_desktop_templates_validate` — `desktop-file-validate` nos dois `.desktop` quando o
      comando existir; `pytest.skip` quando ausente.
  - Comando: `python3 -m pytest tests/unit/test_scripts.py -v -k template`
  - Critério: falha (RED) — `data/` ausente (`test_data_contains_only_templates` e os demais).
  - Estimativa: 20min

- [ ] **T-04**: Criar os templates de `.service` e autostart
  - Arquivos:
    - `data/org.local.DeskAwake.service`
    - `data/deskawake-daemon.desktop`
    - `data/deskawake-widget.desktop`
  - Contrato: `design_e7.md` §4.3, conteúdo literal (sem `@EXEC@` sobrando após a renderização):
    ```ini
    # org.local.DeskAwake.service
    [D-BUS Service]
    Name=org.local.DeskAwake
    Exec=@EXEC@ daemon

    # deskawake-daemon.desktop
    [Desktop Entry]
    Type=Application
    Name=DeskAwake Daemon
    Comment=Mantém a tela e o sistema acordados quando ativado
    Exec=@EXEC@ daemon
    Terminal=false
    NoDisplay=true
    X-GNOME-Autostart-enabled=true

    # deskawake-widget.desktop
    [Desktop Entry]
    Type=Application
    Name=DeskAwake
    Comment=Widget DeskAwake
    Exec=@EXEC@ ui
    Terminal=false
    NoDisplay=true
    OnlyShowIn=MATE;
    X-GNOME-Autostart-enabled=true
    ```
  - Comandos:
    - `chmod 644 data/*`
    - `desktop-file-validate data/deskawake-daemon.desktop data/deskawake-widget.desktop` ⇒ exit 0
    - `python3 -m pytest tests/unit/test_scripts.py -v -k template` ⇒ GREEN
  - Critério: os três arquivos existem, têm modo 644, parsing case-sensitive e validação de desktop
    limpa; nenhum caminho fixo de usuário.
  - Estimativa: 10min

### 2. Contratos estáticos dos scripts, READMEs e créditos (TDD)

- [ ] **T-05**: Escrever os testes RED de contrato estático do `install.sh`
  - Arquivo: `tests/unit/test_scripts.py` (append)
  - Testes:
    - `test_install_script_exists_and_is_executable` — arquivo existe e bit `0o111` ligado.
    - `test_install_script_bash_syntax` — `subprocess.run(["bash", "-n", "install.sh"])` exit 0.
    - `test_install_script_header` — começa com `#!/usr/bin/env bash`; contém
      `set -euo pipefail` e `umask 022`.
    - `test_install_script_has_no_privilege_escalation` — regex `\b(sudo|pkexec|su)\b` ausente.
    - `test_install_script_flags_and_detection` — contém `--all`, `--only-mate`, `--only-kde`,
      `--install-deps`, `--help`, `XDG_CURRENT_DESKTOP`, `MATE`, `KDE`, `PLASMA`,
      `KPKG_TOOL=${KPKG_TOOL:-kpackagetool6}` e `command -v "$KPKG_TOOL"`.
    - `test_install_script_plasmoid_contract` — contém `-t Plasma/Applet`, `-i`, `-u` e o
      fallback de `-u` para `-i`.
    - `test_install_script_renders_templates` — contém `@EXEC@`, `org.local.DeskAwake.service`,
      `deskawake-daemon.desktop`, `deskawake-widget.desktop`, `OnlyShowIn` e troca com `sed`.
    - `test_install_script_exact_messages` — contém exatamente
      `KDE indisponível: kpackagetool6 ausente` e
      `alvo KDE indisponível: kpackagetool6 ausente`.
    - `test_install_script_deps_contract` — contém `python3-gi`, `python3-dbus`, `systemd`,
      `libglib2.0-bin`, `kpackagetool6`, `fonts-inter`, `apt install`, `Verificação:`.
  - Comando: `python3 -m pytest tests/unit/test_scripts.py -v -k install_script`
  - Critério: falha (RED) — `install.sh` ausente.
  - Estimativa: 20min

- [ ] **T-06**: Escrever os testes RED de contrato estático de `uninstall.sh` e `verify.sh`
  - Arquivo: `tests/unit/test_scripts.py` (append)
  - Testes de `uninstall.sh`:
    - `test_uninstall_script_exists_and_is_executable`
    - `test_uninstall_script_bash_syntax`
    - `test_uninstall_script_header`
    - `test_uninstall_script_has_no_privilege_escalation`
    - `test_uninstall_script_contract` — contém `--purge`, `Quit`,
      `GetConnectionUnixProcessID`, `org.local.DeskAwake.Ui`, `-t Plasma/Applet`, `-r`,
      `$HOME/.local/state/deskawake` (ou `~/.local/state/deskawake`), `--help`.
    - `test_uninstall_script_never_uses_pkill` — `pkill -f` ausente.
  - Testes de `verify.sh`:
    - `test_verify_script_exists_and_is_executable`
    - `test_verify_script_bash_syntax`
    - `test_verify_script_header` — `#!/usr/bin/env bash`, `set -euo pipefail`, `umask 022`,
      `LC_ALL=C`.
    - `test_verify_script_has_no_privilege_escalation`
    - `test_verify_script_preconditions` — contém `DeskAwake não instalado; rode ./install.sh`,
      `dependência de diagnóstico ausente:` e `trap`.
    - `test_verify_script_generic_checks` — contém `systemd-inhibit --list`, `verify: OK`,
      `verify: FALHOU`, `[ok]` e `[falha]`.
    - `test_verify_script_mate_tokens` — contém `GetInhibitors` e `mate-screensaver-command`.
    - `test_verify_script_kde_tokens` — contém `ActiveInhibitions`, `HasInhibition` e um timeout
      de poll de 8 s.
    - `test_verify_script_never_uses_forbidden` — `CanSuspend` ausente e
      `re.search(r"IsInhibited\s*\(", source)` é `None`.
  - Comando: `python3 -m pytest tests/unit/test_scripts.py -v -k "uninstall_script or verify_script"`
  - Critério: falha (RED) — `uninstall.sh` e `verify.sh` ausentes.
  - Estimativa: 20min

- [ ] **T-07**: Escrever os testes RED de READMEs, LICENSE e créditos do metadata
  - Arquivo: `tests/unit/test_scripts.py` (append)
  - Testes:
    - `test_readmes_exist_and_crosslink` — `README.md` e `README.en.md` existem; o primeiro linka
      `README.en.md` e o segundo linka `README.md`; ambos começam com `# DeskAwake`.
    - `test_readmes_have_normative_commands` (parametrizado pt/en) — contêm, literalmente:
      `./install.sh --all`, `./install.sh --only-mate`, `./install.sh --only-kde`,
      `./install.sh --install-deps`, `./uninstall.sh`, `--purge`, `./verify.sh`,
      `systemd-inhibit --list`, `daemon.log`, `python3 -m pytest`,
      `dbus-run-session -- python3 -m pytest`,
      `python3 -m pytest tests/integration -m slow`, `--force`.
    - `test_readmes_document_limitations` (parametrizado pt/en) — contêm `kpackagetool6`, `Wayland`,
      `~5 s`/`~6 s` (debounce/verificação), `tampa`/`lid`, `systemctl suspend`,
      `CanSuspend`, `GetInhibitors`, `ActiveInhibitions`, `HasInhibition`, `Mint 22.3`,
      `Kubuntu 26.04` e `checklist`; o pt-BR contém `Adicionar widgets` e `Configurar`, o inglês
      contém `Add Widgets` e `Configure`.
    - `test_readmes_credits_and_version` (parametrizado) — contêm `Marcelo Silva`,
      `Maniva Software`, `0.1.0`, `MIT`, `https://manivasoftware.com.br` e a linha legal
      `Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79`.
    - `test_readmes_link_spec` (parametrizado) — contêm `docs/implementation/spec.md`.
    - `test_license_has_company_and_cnpj` — `LICENSE` contém `MIT` e
      `Copyright (c) 2026 Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79`.
    - `test_metadata_credits` — `plasmoid/metadata.json` tem, em `KPlugin`:
      `Authors == [{"Name": "Marcelo Silva"}]`,
      `Website == "https://manivasoftware.com.br"` e `Copyright` com a linha legal; nenhum `©`
      em todo o JSON; os campos existentes (`Id`, `Name`, `License`, `Version`) permanecem.
  - Comando: `python3 -m pytest tests/unit/test_scripts.py -v -k "readme or license or metadata_credits"`
  - Critério: falha (RED) — `README.en.md` ausente, `LICENSE` sem CNPJ e metadata sem créditos.
  - Estimativa: 20min

### 3. Sandbox de instalação/desinstalação (TDD)

- [ ] **T-08**: Criar a fixture `sandbox` e os falsos `kpackagetool6`/`gdbus`
  - Arquivo: `tests/integration/test_installer_scripts.py` (novo)
  - Fixture `sandbox(tmp_path, monkeypatch)`:
    - `home = tmp_path / "home"`; `data = tmp_path / "data"`; `bin = tmp_path / "bin"`;
      criar os três diretórios.
    - `env` copiado de `os.environ` com `HOME=$home`, `XDG_DATA_HOME=$data`,
      `PATH=$bin:$PATH`, `KPKG_LOG=$tmp_path/kpackagetool6.log`,
      `GDBUS_LOG=$tmp_path/gdbus.log` e `GDBUS_STATE=$tmp_path/gdbus-state.json`.
    - `$bin/kpackagetool6` falso (Python executável): registra `sys.argv[1:]` em `KPKG_LOG`;
      para `-t Plasma/Applet -i/-u` cria `$XDG_DATA_HOME/plasma/plasmoids/org.local.deskawake/metadata.json`;
      para `-r org.local.deskawake` remove o diretório; se `KPKG_FAIL=1`, sai 1.
    - `$bin/gdbus` falso (Python executável): registra chamada em `GDBUS_LOG`; lê `GDBUS_STATE`
      (JSON `{nome: pid|null}`); `org.freedesktop.DBus.NameHasOwner` ⇒ `(true,)`/`(false,)`;
      `Quit` ⇒ limpa o dono no JSON e imprime `()` (com `GDBUS_QUIT_NOOP=1`, mantém o dono para
      testar o fallback por PID); `GetConnectionUnixProcessID` ⇒ `(uint32 <pid>,)`.
    - Helper `sandbox.run(script, *args, env_extra=None)` chama
      `subprocess.run([str(REPO_ROOT / script), *args], cwd=REPO_ROOT, env=env, text=True,
      capture_output=True, timeout=60)` e devolve o `CompletedProcess`.
  - Teste `test_sandbox_is_isolated`: `HOME` e `XDG_DATA_HOME` são `tmp_path`; o `PATH` contém
    `tmp_path/bin`; `$bin/kpackagetool6` e `$bin/gdbus` são executáveis.
  - Comando: `python3 -m pytest tests/integration/test_installer_scripts.py -v -k sandbox`
  - Critério: fixture funciona e os falsos respondem aos formatos esperados; nenhum processo real
    de daemon/Plasma/MATE é iniciado.
  - Estimativa: 30min

- [ ] **T-09**: Escrever os testes RED do `install.sh` em sandbox
  - Arquivo: `tests/integration/test_installer_scripts.py` (append)
  - Casos:
    - `test_install_only_mate_copies_code` — `--only-mate`: existem `$SHARE/core/`,
      `$SHARE/bin/deskawake` (755), `$SHARE/ui_gtk/`, `$SHARE/assets/`,
      `$SHARE/data/deskawake-widget.desktop`; `$SHARE` é `${XDG_DATA_HOME}/deskawake`.
    - `test_install_only_mate_renders_files` — launcher `$HOME/.local/bin/deskawake` (755) com
      caminho absoluto; `.service` em `${XDG_DATA_HOME}/dbus-1/services/` (644);
      autostart do daemon e do widget em `$HOME/.config/autostart/` (644);
      `OnlyShowIn=MATE;` no widget; nenhum `@EXEC@` nos arquivos gerados (launcher, `.service`,
      autostarts); o template copiado em `$SHARE/data/deskawake-widget.desktop` pode preservar
      `@EXEC@` para a UI (E4) reescrever o `Exec`.
    - `test_install_only_mate_does_not_call_kpackagetool6` — `KPKG_LOG` vazio/inexistente.
    - `test_install_only_mate_is_idempotent` — segunda execução exit 0; árvore idêntica; nenhum
      `*.new.*`/`*.tmp` em `$HOME`/`$XDG_DATA_HOME`.
    - `test_install_does_not_stop_daemon` — `GDBUS_LOG` não contém `Quit`.
    - `test_install_only_kde_with_tool_installs_daemon_and_plasmoid` — `--only-kde` com a
      ferramenta falsa: `core/`, `bin/`, `.service`, autostart do daemon e Plasmoid presentes;
      `ui_gtk/`, `assets/` e autostart do widget ausentes; chamada `-t Plasma/Applet -i`.
    - `test_install_explicit_flag_wins_over_desktop` — `XDG_CURRENT_DESKTOP=KDE` com
      `--only-mate` instala daemon+GTK (a flag explícita vence a detecção).
    - `test_install_all_with_tool_installs_and_upgrades_plasmoid` — primeiro run chama
      `-t Plasma/Applet -i`; segundo chama `-u`; `$PLASMOID_DIR/metadata.json` existe; exit 0.
    - `test_install_all_without_tool_degrades_with_warning` — `KPKG_TOOL=__missing__`: exit 0,
      stdout com `KDE indisponível: kpackagetool6 ausente`, daemon+GTK instalados, sem Plasmoid.
    - `test_install_only_kde_without_tool_fails_without_copying` — exit 1, mensagem
      `alvo KDE indisponível: kpackagetool6 ausente`, `$SHARE` ausente.
    - `test_install_auto_detects_mate` — `XDG_CURRENT_DESKTOP=MATE` equivale a `--only-mate`.
    - `test_install_auto_detects_kde` — `XDG_CURRENT_DESKTOP=KDE` equivale a `--only-kde`.
    - `test_install_unknown_desktop_exits_2` — `XDG_CURRENT_DESKTOP` vazio/desconhecido: exit 2,
      `$SHARE` ausente.
    - `test_install_all_unknown_desktop_installs_all` — `--all` em desktop desconhecido instala
      daemon+GTK+Plasmoid (ferramenta falsa presente).
    - `test_install_rejects_conflicting_flags` — `--all --only-kde` ⇒ exit 2.
    - `test_install_rejects_unknown_flag` — `--wat` ⇒ exit 2.
    - `test_install_deps_output_has_no_sudo` — `--install-deps`: contém os três blocos e
      `Verificação:`; `"sudo" not in stdout.lower()`.
    - `test_install_deps_only_kde_without_tool_exits_1` — `--install-deps --only-kde` com
      `KPKG_TOOL=__missing__` ⇒ exit 1.
    - `test_install_deps_all_exits_0` — `--install-deps --all` com `KPKG_TOOL=__missing__` ⇒
      exit 0 (ferramenta é aviso no alvo `--all`).
    - `test_install_handles_home_with_spaces` — `HOME` com espaço: exit 0; `Exec` do `.service`
      e do autostart cita o caminho; launcher cita o caminho.
    - `test_install_all_plasmoid_failure_exits_1` — `KPKG_FAIL=1` com ferramenta presente ⇒
      exit 1.
  - Comando: `python3 -m pytest tests/integration/test_installer_scripts.py -v -k install`
  - Critério: falha (RED) — `install.sh` ausente (exit 127/`FileNotFoundError`).
  - Estimativa: 35min

- [ ] **T-10**: Escrever os testes RED do `uninstall.sh` em sandbox
  - Arquivo: `tests/integration/test_installer_scripts.py` (append)
  - Casos:
    - `test_uninstall_removes_everything_and_preserves_config` — após `--only-mate`, criar
      `$HOME/.config/deskawake/config.json` e `$HOME/.local/state/deskawake/daemon.log`; rodar
      `uninstall.sh`: exit 0; `$SHARE`, launcher, `.service`, autostarts e state ausentes; config
      presente.
    - `test_uninstall_is_idempotent` — segunda execução exit 0; nada recriado.
    - `test_uninstall_purge_removes_config` — `--purge` remove `$HOME/.config/deskawake/`.
    - `test_uninstall_stops_daemon_by_quit` — `GDBUS_STATE` com dono do daemon; `Quit` limpa o
      dono; exit 0; log contém `Quit`.
    - `test_uninstall_falls_back_to_pid` — `gdbus` informa um `sleep 60` real como dono e, com
      `GDBUS_QUIT_NOOP=1`, `Quit` não limpa o dono; `uninstall.sh` envia TERM e o processo morre
      em ≤ 3 s; log contém `GetConnectionUnixProcessID`.
    - `test_uninstall_stops_ui_widget` — `org.local.DeskAwake.Ui` com `sleep 60` real; TERM
      encerra o processo; best-effort.
    - `test_uninstall_removes_plasmoid_with_tool` — após `--all`, `-t Plasma/Applet -r
      org.local.deskawake` no log; diretório removido.
    - `test_uninstall_removes_plasmoid_without_tool` — diretório do Plasmoid criado à mão e
      `KPKG_TOOL=__missing__`: diretório removido, exit 0.
    - `test_uninstall_rejects_unknown_flag` — `--wat` ⇒ exit 2.
  - Comando: `python3 -m pytest tests/integration/test_installer_scripts.py -v -k uninstall`
  - Critério: falha (RED) — `uninstall.sh` ausente.
  - Estimativa: 30min

### 4. `install.sh`

- [ ] **T-11**: Criar o esqueleto do `install.sh` com flags, ajuda e detecção de alvo
  - Arquivo: `install.sh` (novo)
  - Contrato: `design_e7.md` §4.1–§4.2 e §2.3 —
    - `#!/usr/bin/env bash`, `set -euo pipefail`, `umask 022`.
    - `REPO_DIR` resolvido por `BASH_SOURCE[0]`; não depende do CWD.
    - Constantes: `SHARE=${XDG_DATA_HOME:-$HOME/.local/share}/deskawake`,
      `BIN_DIR=$HOME/.local/bin`,
      `SERVICE_DIR=${XDG_DATA_HOME:-$HOME/.local/share}/dbus-1/services`,
      `AUTOSTART_DIR=$HOME/.config/autostart`,
      `PLASMOID_DIR=${XDG_DATA_HOME:-$HOME/.local/share}/plasma/plasmoids/org.local.deskawake`,
      `KPKG_TOOL=${KPKG_TOOL:-kpackagetool6}`.
    - Parse de `--all`, `--only-mate`, `--only-kde`, `--install-deps`, `--help`; flags de alvo
      mutuamente exclusivas ⇒ exit 2; flag desconhecida ⇒ exit 2.
    - `--help` imprime usage, exemplos e “não requer privilégios administrativos”; exit 0.
    - Sem flag de alvo: detecta `XDG_CURRENT_DESKTOP` case-insensitive (`MATE` ⇒ mate;
      `KDE`/`PLASMA` ⇒ kde); desconhecido ⇒ exit 2 com
      `não foi possível detectar o desktop (XDG_CURRENT_DESKTOP); use --only-mate, --only-kde ou --all`.
    - Funções `log`, `warn`, `die` com mensagens pt-BR de uma linha.
  - Comandos:
    - `bash -n install.sh` ⇒ exit 0
    - `./install.sh --help` ⇒ exit 0 e usage
    - `./install.sh --only-mate --only-kde` ⇒ exit 2
    - `./install.sh --wat` ⇒ exit 2
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "install_script_header or install_script_flags or install_script_bash_syntax"`
  - Critério: header/flags/detecção verdes; nenhuma cópia ou dependência avaliada ainda.
  - Estimativa: 25min

- [ ] **T-12**: Implementar checagem de dependências e `--install-deps`
  - Arquivo: `install.sh`
  - Contrato: `design_e7.md` §4.2 —
    - Universais: `python3`, `gi`, `dbus`, `systemd-inhibit`, `gdbus`.
    - GTK: `Gtk 3.0` (via `python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk'`).
    - KDE: `command -v "$KPKG_TOOL"`.
    - `fonts-inter` não é verificado; é sugestão opcional.
    - Falha de dependência obrigatória: mensagem + sugestão `./install.sh --install-deps`, exit 1,
      **sem copiar nada**.
    - `--install-deps` imprime os blocos normativos (`Dependências obrigatórias (runtime)`,
      `KDE (necessário apenas para o Plasmoid)`, `Opcional (fonte Inter)`, `Verificação:`), com
      `apt install` e status `ok`/`ausente`; **nunca** executa `apt`, `sudo` ou instala algo.
    - `--install-deps` sozinho: exit 0/1 conforme dependências universais; com `--only-kde`, o
      `kpackagetool6` é obrigatório; com `--all`/`--only-mate`, é aviso.
    - `--install-deps` combinado com alvo explícito: imprime e continua a instalação.
  - Comandos:
    - `./install.sh --install-deps` ⇒ três blocos + verificação; `"sudo" not in output`
    - `./install.sh --install-deps --only-kde` (com `KPKG_TOOL` inexistente) ⇒ exit 1
    - `python3 -m pytest tests/unit/test_scripts.py -v -k install_script_deps`
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k "install_deps"`
  - Critério: saída normativa sem `sudo`; falha de dependência acontece antes de qualquer cópia;
    testes de deps verdes.
  - Estimativa: 25min

- [ ] **T-13**: Implementar staging e cópia de `core/`, `bin/` e UI
  - Arquivo: `install.sh`
  - Contrato: `design_e7.md` §2.4 e §4.2 (passo 5) —
    - Staging em `$SHARE.new.$$`; ao final `rm -rf "$SHARE"` + `mv "$STAGE" "$SHARE"`.
    - Copiar `core/` e `bin/deskawake` sempre; `ui_gtk/`, `assets/` e
      `data/deskawake-widget.desktop` só no alvo GTK.
    - Excluir `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `tests/`, `docs/` e `.venv/`.
    - `$SHARE/bin/deskawake` 755; demais arquivos conforme o original.
    - `trap` de limpeza do staging em erro; nunca deixar instalação parcial.
    - **Não** iniciar nem parar o daemon; **não** criar `config.json`.
  - Comandos:
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k "only_mate_copies_code or does_not_stop_daemon"`
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k "only_mate_is_idempotent"`
  - Critério: cópia correta e idempotente; nenhuma chamada `Quit`; sem `*.new.*`/`*.tmp`.
  - Estimativa: 20min

- [ ] **T-14**: Renderizar launcher, `.service` e autostarts a partir de `data/`
  - Arquivo: `install.sh`
  - Contrato: `design_e7.md` §4.3–§4.4 —
    - Launcher `$HOME/.local/bin/deskawake`:
      ```sh
      #!/bin/sh
      exec "<SHARE>/bin/deskawake" "$@"
      ```
      caminho absoluto resolvido na instalação; modo 755; sem symlink.
    - `.service` em `$SERVICE_DIR/org.local.DeskAwake.service`; autostart do daemon sempre;
      autostart do widget só no alvo GTK, com `OnlyShowIn=MATE;`.
    - `@EXEC@` substituído por `$SHARE/bin/deskawake`; escapar `\`, `&` e `|` antes do `sed`;
      citar o caminho quando houver espaços; falhar se sobrar `@EXEC@` nos arquivos gerados. O
      template copiado para `$SHARE/data/deskawake-widget.desktop` preserva o token, porque a UI
      (E4) o lê e reescreve o `Exec`.
    - Escrita atômica (`tmp` + `mv`); `.service`/`.desktop` 644.
    - Não alterar `.profile`/`.bashrc`; apenas avisar se `~/.local/bin` não estiver no `PATH`.
  - Comandos:
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k "renders_files or home_with_spaces"`
    - `grep -R "@EXEC@" "$HOME/.local/share/dbus-1/services" "$HOME/.config/autostart" "$HOME/.local/bin"` (quando existirem) ⇒ sem saída
    - `grep -c "@EXEC@" "$HOME/.local/share/deskawake/data/deskawake-widget.desktop"` ⇒ 1 (template preservado para a UI)
  - Critério: arquivos renderizados com caminho absoluto, modos corretos e nenhum token restante;
    teste com espaço no `HOME` verde.
  - Estimativa: 25min

- [ ] **T-15**: Instalar Plasmoid, resumo final e permissões; fechar os testes do `install.sh`
  - Arquivo: `install.sh`
  - Contrato: `design_e7.md` §2.3, §4.2 (passos 7–8) e ADR-05 —
    - Alvo KDE com ferramenta: `$KPKG_TOOL -t Plasma/Applet -i ./plasmoid` se `$PLASMOID_DIR`
      não existe; `-u` se existe; fallback `-i` se `-u` falhar; falha do Plasmoid em alvo KDE
      explícito ⇒ exit 1.
    - `--all` sem ferramenta: aviso exato `KDE indisponível: kpackagetool6 ausente`, mensagem de
      que daemon+GTK foram instalados, exit 0.
    - `--only-kde`/auto-KDE sem ferramenta: mensagem exata
      `alvo KDE indisponível: kpackagetool6 ausente`, exit 1, nada copiado (já garantido na
      checagem de dependências).
    - Aviso de Wayland quando o alvo GTK estiver ativo (widget exige X11; no KDE a UI suportada é
      o Plasmoid); não falhar.
    - Resumo: alvo, `$SHARE`, launcher, `.service`, autostarts, Plasmoid e próximos passos por DE;
      aviso se `~/.local/bin` não estiver no `PATH`; aviso de que o daemon em execução continua
      com a versão anterior até o próximo login/reinício.
    - `chmod 755 install.sh`.
  - Comandos:
    - `bash -n install.sh`
    - `python3 -m pytest tests/unit/test_scripts.py -v -k install_script` ⇒ GREEN
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k install` ⇒ GREEN
  - Critério: todos os testes estáticos e de sandbox do `install.sh` verdes; mensagens exatas de
    degradação; nenhum `@EXEC@` nos arquivos gerados; scripts executável.
  - Estimativa: 25min

### 5. `uninstall.sh`

- [ ] **T-16**: Implementar parse, encerramento do daemon e da UI GTK
  - Arquivo: `uninstall.sh` (novo)
  - Contrato: `design_e7.md` §4.5 e ADR-06 —
    - Header `#!/usr/bin/env bash`, `set -euo pipefail`, `umask 022`; `--purge`, `--help`;
      flag desconhecida ⇒ exit 2.
    - Se `gdbus` e barramento existirem: `NameHasOwner` de `org.local.DeskAwake`; se houver
      dono, chamar `Quit()` e esperar até 3 s o nome sumir. Se ainda houver dono,
      `GetConnectionUnixProcessID`, `SIGTERM`, esperar 2 s, `SIGKILL`. **Nunca** `pkill -f`.
    - UI GTK: se `org.local.DeskAwake.Ui` tiver dono, obter PID e encerrar
      (`SIGTERM` → 2 s → `SIGKILL`), best-effort; ausência não é erro.
    - Daemon morto/barramento ausente: falhas de `gdbus` em silêncio; a remoção de arquivos
      continua.
    - `chmod 755 uninstall.sh`.
  - Comandos:
    - `bash -n uninstall.sh`
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "uninstall_script_header or uninstall_script_bash_syntax"`
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k "uninstall_stops_daemon or uninstall_falls_back_to_pid or uninstall_stops_ui_widget"`
  - Critério: daemon e UI encerrados conforme o contrato; fallback por PID funciona; sem
    `pkill -f`.
  - Estimativa: 25min

- [ ] **T-17**: Implementar remoção de Plasmoid, arquivos, estado, `--purge` e idempotência
  - Arquivo: `uninstall.sh`
  - Contrato: `design_e7.md` §4.5 e ADR-07 —
    - Plasmoid: se `$PLASMOID_DIR` existe e a ferramenta está disponível, `-t Plasma/Applet -r
      org.local.deskawake`; se a ferramenta falta ou a remoção falha, `rm -rf` do diretório fixo;
      se ainda restar, reportar e exit 1. Nunca remover `~/.local/share/plasma` inteiro.
    - Remover `.service`, os dois autostarts, o launcher, `$SHARE` e
      `$HOME/.local/state/deskawake/`; ausência é sucesso.
    - Preservar `$HOME/.config/deskawake/`; `--purge` remove também.
    - Segunda execução exit 0; nada é recriado.
    - Após encerrar o daemon, se `systemd-inhibit --list` ainda mostrar `DeskAwake`, imprimir
      aviso com o comando de inspeção; **não** matar processos de terceiros.
    - Só remover caminhos fixos derivados de `$HOME`; não seguir symlink para fora do alvo.
  - Comandos:
    - `bash -n uninstall.sh`
    - `python3 -m pytest tests/unit/test_scripts.py -v -k uninstall_script` ⇒ GREEN
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v -k uninstall` ⇒ GREEN
  - Critério: remoção completa preservando config; `--purge` remove; idempotente; tolera
    `kpackagetool6` ausente; todos os testes de uninstall verdes.
  - Estimativa: 25min

### 6. `verify.sh`

- [ ] **T-18**: Implementar pré-condições, `trap` e checagens genéricas de ON/OFF
  - Arquivo: `verify.sh` (novo)
  - Contrato: `design_e7.md` §4.6 —
    - Header `#!/usr/bin/env bash`, `set -euo pipefail`, `umask 022`, `LC_ALL=C`.
    - Pré-condições: instalação presente (`$HOME/.local/bin/deskawake` ou
      `$SHARE/bin/deskawake`) e `.service` instalado; senão
      `DeskAwake não instalado; rode ./install.sh`, exit 1.
    - `gdbus` e `systemd-inhibit` obrigatórios; ausência ⇒
      `dependência de diagnóstico ausente: <nome>`, exit 1. `mate-screensaver-command` é
      opcional.
    - `trap` de `EXIT`/`INT`/`TERM`: `deskawake off` best-effort para nunca deixar ON.
    - `deskawake off` inicial; `deskawake on` (stdout `on`, exit 0); `systemd-inhibit --list`
      contém `DeskAwake`; `deskawake status` exit 0/stdout `on`; `deskawake off` (stdout `off`,
      exit 0); poll de até 3 s por ausência de `DeskAwake` no `systemd-inhibit --list`;
      `deskawake status` exit 1/stdout `off`.
    - `[ok]`/`[falha]` por checagem; `verify: OK`/`verify: FALHOU`; exit 0/1.
    - Não executar o script na suíte; contrato estático apenas.
  - Comandos:
    - `bash -n verify.sh`
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "verify_script_header or verify_script_bash_syntax or verify_script_preconditions or verify_script_generic_checks"`
  - Critério: esqueleto do verify válido, com trap e checagens genéricas; backend ainda em stub.
  - Estimativa: 25min

- [ ] **T-19**: Implementar a verificação de backend no MATE
  - Arquivo: `verify.sh`
  - Contrato: `design_e7.md` §4.6 e ADR-08 —
    - Detectar MATE por `XDG_CURRENT_DESKTOP` (case-insensitive).
    - ON: `gdbus` em `org.mate.ScreenSaver.GetInhibitors` contém `Application="deskawake"`.
      Se `mate-screensaver-command` existir, `-q` deve listar `deskawake`; ausência do comando
      não falha.
    - **Não** exigir `IsInhibited(8)`; o mate-screensaver 1.26.2 não expõe o método.
    - OFF: poll até `GetInhibitors` sem `deskawake`; se `mate-screensaver-command` existir, `-q`
      não deve mais listar `deskawake`.
  - Comandos:
    - `bash -n verify.sh`
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "verify_script_mate_tokens or verify_script_never_uses_forbidden"`
    - `grep -nE "GetInhibitors|mate-screensaver-command" verify.sh` ⇒ funções presentes
    - `grep -nE "IsInhibited\s*\(" verify.sh` ⇒ sem saída
  - Critério: backend MATE implementado sem `IsInhibited`; `mate-screensaver-command` opcional.
  - Estimativa: 20min

- [ ] **T-20**: Implementar a verificação de backend no KDE e fechar o `verify.sh`
  - Arquivo: `verify.sh`
  - Contrato: `design_e7.md` §4.6 e ADR-08 —
    - Detectar KDE/Plasma por `XDG_CURRENT_DESKTOP`.
    - ON: poll de `PolicyAgent.ActiveInhibitions` por até 8 s (debounce de ~5 s) até conter
      `deskawake` **e** `DeskAwake active`; `HasInhibition(4)` ⇒ `(true,)`.
      Usar `gdbus` em `/org/kde/Solid/PowerManagement/PolicyAgent`; nunca `CanSuspend`.
    - OFF: poll até `ActiveInhibitions` sem `deskawake`; `HasInhibition(4)` é informativo.
    - Desktop desconhecido: apenas as checagens genéricas (3–5), com aviso.
    - `chmod 755 verify.sh`.
  - Comandos:
    - `bash -n verify.sh`
    - `python3 -m pytest tests/unit/test_scripts.py -v -k verify_script` ⇒ GREEN
    - `grep -n "CanSuspend" verify.sh` ⇒ sem saída
  - Critério: todos os testes estáticos do verify verdes; poll de 8 s e `HasInhibition` presentes;
    `CanSuspend` e `IsInhibited` ausentes.
  - Estimativa: 25min

### 7. Documentação e créditos

- [ ] **T-21**: Escrever o `README.md` em pt-BR
  - Arquivo: `README.md` (substituir o conteúdo bilíngue atual)
  - Contrato: `design_e7.md` §4.8 — 13 seções na ordem: título + descrição + link para o inglês;
    sistemas suportados; o que faz/não faz; requisitos e `--install-deps`; instalação com
    `./install.sh`, `--all`, `--only-mate`, `--only-kde`; uso (CLI `on/off/toggle/status/daemon/ui`,
    códigos 0/1/3, widget GTK e `Sobre`, Plasmoid); diagnóstico (`verify.sh`, `status`,
    `GetLastError`, `daemon.log` e `.log.1`, `systemd-inhibit --list`); limitações (debounce de
    ~5 s no KDE, tampa/suspensão manual, Plasmoid manual, `kpackagetool6` ausente no Mint, GTK
    bloqueado em Wayland com `--force`, `Configurar` sem categorias, upgrade não interrompe daemon,
    `verify.sh` termina OFF, achados MATE A1–A5 e A7); desenvolvimento e testes (`sudo apt install
    python3-pytest`, `python3 -m pytest`, `dbus-run-session`, `-m slow`, `bash -n`, `shellcheck`
    opcional); checklist manual Mint 22.3 MATE **copiada da spec sem resumir**; checklist manual
    Kubuntu 26.04/Plasma 6.6 copiada da spec sem resumir; desinstalação (`./uninstall.sh`,
    `--purge`); créditos e licença (Marcelo Silva · Maniva Software, site, linha legal com CNPJ,
    versão `0.1.0`, MIT e link para `docs/implementation/spec.md`).
  - Comandos:
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "readme or license or metadata_credits"`
    - `grep -c "^- \[ \]" README.md` ⇒ checklists presentes (≥ 20 itens)
    - `grep -n "MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79" README.md`
  - Critério: testes de README pt-BR verdes; nenhuma promessa fora do contrato; comandos idênticos
    aos do design; link para `README.en.md`.
  - Estimativa: 35min

- [ ] **T-22**: Escrever o `README.en.md` espelhando o conteúdo normativo
  - Arquivo: `README.en.md` (novo)
  - Contrato: `design_e7.md` §4.8 e ADR-10 — mesma estrutura de 13 seções em inglês; comandos,
    nomes de arquivos, flags, códigos, avisos normativos e linhas legais **idênticos** ao pt-BR;
    duas checklists traduzidas sem resumir; link para `README.md`; link para a spec; créditos
    `Marcelo Silva`, `Maniva Software`, `0.1.0`, MIT e linha legal com CNPJ. Nenhum `©`.
  - Comandos:
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "readme or license or metadata_credits"` ⇒ GREEN
    - `grep -c "^- \[ \]" README.en.md` ⇒ checklists presentes (≥ 20 itens)
    - `diff <(grep -oE '\./(install|uninstall|verify)\.sh[^`]*' README.md | sort) <(grep -oE '\./(install|uninstall|verify)\.sh[^`]*' README.en.md | sort)` ⇒ sem diferenças
  - Critério: paridade de comandos entre os dois idiomas; créditos e limitações equivalentes.
  - Estimativa: 30min

- [ ] **T-23**: Atualizar `LICENSE` e `plasmoid/metadata.json` com os créditos
  - Arquivos:
    - `LICENSE`
    - `plasmoid/metadata.json`
  - Contrato: `spec.md` decisão 34 e `design_e7.md` §4.8/ADR-11 —
    - `LICENSE`: `MIT` + linha exata
      `Copyright (c) 2026 Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79`.
    - `metadata.json`: adicionar dentro de `KPlugin` `Authors: [{"Name": "Marcelo Silva"}]`,
      `Website: "https://manivasoftware.com.br"` e `Copyright` com a linha legal **sem** `©`;
      não alterar `Id`, `Name`, `Description`, `Icon`, `Category`, `License`, `Version` nem o QML.
  - Comandos:
    - `python3 -m json.tool plasmoid/metadata.json > /dev/null` ⇒ exit 0
    - `python3 -m pytest tests/unit/test_scripts.py -v -k "license or metadata_credits"` ⇒ GREEN
    - `python3 -m pytest tests/unit/test_plasmoid_assets.py tests/unit/test_version.py -q` ⇒ GREEN
    - `grep -R "©" plasmoid/metadata.json` ⇒ sem saída
  - Critério: créditos nos dois lugares, JSON válido, testes existentes do Plasmoid e de versão
    verdes; nenhuma mudança de QML.
  - Estimativa: 10min

### 8. Gate automatizado

- [ ] **T-24**: Rodar sintaxe, lint e a suíte unitária
  - Comandos:
    - `chmod 755 install.sh uninstall.sh verify.sh`
    - `bash -n install.sh uninstall.sh verify.sh` ⇒ exit 0
    - `command -v shellcheck >/dev/null && shellcheck install.sh uninstall.sh verify.sh || true` ⇒ rodar quando existir; ausência documentada
    - `python3 -m pytest tests/unit -q` ⇒ **0 failures**, ≥ 282 passed
    - `python3 -m pytest tests/unit/test_scripts.py -v` ⇒ GREEN
    - `python3 -m pytest tests/unit/test_plasmoid_assets.py tests/unit/test_version.py -q` ⇒ GREEN
  - Critério: `bash -n` limpo; `shellcheck` limpo ou ausência registrada; nenhum teste unitário
    quebrado; nenhum arquivo `.pyc`/cache novo versionado.
  - Estimativa: 10min

- [ ] **T-25**: Rodar a suíte de integração e o slow opt-in
  - Comandos:
    - `dbus-run-session -- python3 -m pytest tests/integration -q` ⇒ 0 failures; ≥ 64 passed
      (34 existentes + 30 novos), 1 skip padrão do slow
    - `python3 -m pytest tests/integration/test_installer_scripts.py -v` ⇒ GREEN
    - `python3 -m pytest tests/integration -m slow -q` ⇒ verde no Kubuntu com PolicyAgent real;
      skip documentado onde não houver backend real
    - `systemd-inhibit --list` ⇒ sem entrada `DeskAwake` deixada pelos testes
  - Critério: suíte de integração sem falhas; sandbox isolado; slow opt-in não roda por padrão e
    não deixa processos/órfãos.
  - Estimativa: 15min

- [ ] **T-26**: Auditar isolamento e ausência de vazamentos da sandbox
  - Comandos:
    - `python3 -m pytest tests/integration/test_installer_scripts.py -q` (duas vezes) ⇒ GREEN nas duas
    - `pgrep -af "sleep 60" || true` ⇒ sem processos dos testes
    - `systemd-inhibit --list | grep -i deskawake || true` ⇒ sem saída
    - `grep -nE "expanduser|Path\.home|HOME=/home" tests/integration/test_installer_scripts.py` ⇒ sem saída
    - `find "$HOME/.local/share/deskawake" -maxdepth 0 -newer pyproject.toml 2>/dev/null` ⇒ sem saída (nada instalado no HOME real pelos testes)
  - Critério: testes repetíveis, sem tocar o `HOME` real, sem processos residuais e sem locks.
  - Estimativa: 10min

### 9. Validação manual

- [ ] **T-27**: Checklist manual Mint 22.3 MATE/X11
  - Pré-condição: branch da E7 na máquina Mint; `kpackagetool6` ausente; `desktop-file-validate`
    presente; `shellcheck` ausente.
  - Passos (design §9.2; a UI GTK já foi validada na E6):
    - `./install.sh --only-mate`: conferir `$SHARE`, launcher, `.service`, autostart do daemon e
      do widget, permissões 755/644.
    - `./install.sh --all` no Mint: exit 0, aviso `KDE indisponível: kpackagetool6 ausente`,
      mensagem explícita de que daemon+GTK foram instalados.
    - `./install.sh --only-kde`: exit ≠ 0, mensagem clara; nada copiado.
    - `./install.sh --install-deps`: comandos `apt` com `fonts-inter` separado; nenhum `sudo` no
      output.
    - Reexecutar `./install.sh --all` duas vezes: exit 0, sem estado quebrado.
    - `./verify.sh`: `on` → lock + `GetState()=="on"`; `GetInhibitors` contém `deskawake`;
      `off` → lock ausente e sem órfãos; **não** usar `IsInhibited(8)`; conferir
      `mate-screensaver-command -q` quando existir.
    - `./uninstall.sh`: remove tudo exceto `~/.config/deskawake/`; segunda execução exit 0;
      tolera `kpackagetool6` ausente; `--purge` remove a config.
    - Login novo ou `deskawake ui`: widget abre; "Iniciar com o sistema" reflete o autostart.
    - Pendências não executadas (logout, monitor externo, bloqueio de tela): registrar no PR/README.
  - Critério: cada item marcado OK ou com desvio descrito e colado no corpo do PR; `verify.sh`
    termina OFF; nenhum resíduo em `$HOME`.
  - Estimativa: 45min

- [ ] **T-28**: Checklist manual Kubuntu 26.04.1 / Plasma 6.6
  - Pré-condição: branch da E7 no Kubuntu; sessão Plasma 6.6.7/Wayland; `kpackagetool6` 2.0.
  - Passos (design §9.3):
    - `./install.sh` sem flag (auto-KDE) e `./install.sh --all`: conferir daemon, `.service`,
      autostart do daemon e Plasmoid em
      `~/.local/share/plasma/plasmoids/org.local.deskawake/`.
    - Reexecutar `--all`: usa `-t Plasma/Applet -u`, exit 0.
    - `./install.sh --only-kde` com `kpackagetool6` 2.0: exit 0; sem a ferramenta (simulada):
      exit ≠ 0.
    - Plasmoid aparece em "Adicionar widgets"; `preview.png` visível; o "Sobre" nativo mostra
      `Marcelo Silva`, `manivasoftware.com.br` e a linha legal com CNPJ.
    - `./verify.sh`: poll de ~6–8 s; `ActiveInhibitions` contém `deskawake`/`DeskAwake active`;
      `HasInhibition(4)` verdadeiro; `off` libera a entrada; sem órfãos; `CanSuspend` não é usado.
    - `./uninstall.sh`: remove o Plasmoid e o restante, preservando `~/.config/deskawake/`;
      segunda execução exit 0.
    - "Iniciar com o sistema" do GTK não aparece no Plasmoid; autostart do widget não roda no KDE.
    - Checklists da spec copiadas no README, incluindo tampa/suspensão manual (destrutivo) e o
      debounce de ~5 s.
  - Critério: cada item marcado OK ou com desvio descrito e colado no PR; itens destrutivos
    explicitamente marcados como não executados quando não seguros.
  - Estimativa: 45min

### 10. Auditoria e entrega

- [ ] **T-29**: Auditar escopo, higiene e ausência de artefatos de spec no código
  - Comandos:
    - `git status --short` ⇒ somente arquivos da E7 + `docs/implementation/` (fora do stage)
    - `git diff --stat -- core ui_gtk plasmoid/contents bin pyproject.toml tests/conftest.py` ⇒
      sem saída
    - `find data -type f | sort` ⇒ exatamente os três templates
    - `grep -RInE "AC-[0-9]|T-[0-9]|design_e7|tasks_e7|DELIVERY_MAP" install.sh uninstall.sh verify.sh data tests/unit/test_scripts.py tests/integration/test_installer_scripts.py` ⇒ sem saída
    - `grep -RInE "sudo|pkexec|\bsu\b" install.sh uninstall.sh verify.sh` ⇒ sem saída
    - `grep -RInE "@EXEC@" data` ⇒ 3 ocorrências, uma por template (esperado antes da renderização); nos arquivos gerados, nunca
    - `grep -RIn "pkill -f" uninstall.sh` ⇒ sem saída
    - `grep -RIn "CanSuspend" verify.sh` ⇒ sem saída
    - `grep -RInE "IsInhibited\s*\(" verify.sh` ⇒ sem saída
  - Critério: escopo limpo; nenhuma dependência nova; nenhum artefato de spec em código/testes;
    nenhuma alteração em `core/`, `ui_gtk/`, `plasmoid/contents/`, `bin/`, `pyproject.toml` ou
    `tests/conftest.py`.
  - Estimativa: 15min

- [ ] **T-30**: Preparar commit e PR somente com a entrega da E7
  - Comandos:
    - `git add data/org.local.DeskAwake.service data/deskawake-daemon.desktop data/deskawake-widget.desktop install.sh uninstall.sh verify.sh tests/unit/test_scripts.py tests/integration/test_installer_scripts.py README.md README.en.md LICENSE plasmoid/metadata.json`
    - `git diff --cached --name-only` ⇒ exatamente os 12 arquivos acima
    - `python3 -m pytest tests/unit -q && dbus-run-session -- python3 -m pytest tests/integration -q` ⇒ gate verde
    - `git commit -m "feat(e7): instalador, verificação e documentação"`
    - `git push -u origin feat/e7-instalador-verificacao-docs`
    - `gh pr create --base main --head feat/e7-instalador-verificacao-docs --title "feat(e7): instalador, verificação e documentação" --body "<corpo com gate e checklists>"`
    - `gh pr view --json baseRefName,headRefName,files --jq '{base: .baseRefName, head: .headRefName, files: [.files[].path]}'` ⇒ base `main`, head `feat/e7-instalador-verificacao-docs` e apenas os 12 arquivos
  - Corpo do PR: gate com comando/resultado (`bash -n`, `shellcheck` ausente, unit, integração,
    `test_scripts.py`, `test_installer_scripts.py`), checklists manuais T-27/T-28 preenchidas,
    fora de escopo (E8), riscos residuais (design §10) e pendências manuais (logout, monitor
    externo, lock). **Não** citar `spec.md`, `design_e7.md`, `tasks_e7.md` nem IDs `AC-*`/`T-*`.
  - Critério: PR contém apenas os 12 arquivos; `docs/implementation/` e artefatos de spec fora do
    stage/PR; **nunca** usar `git add -A`/`git add .`; base `main`.
  - Estimativa: 20min

## Mapeamento AC → Tasks

Os critérios vêm do `DELIVERY_MAP.md` §E7.4, da §9.1–§9.4 do `design_e7.md` e do gate G-E7.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-01 — `bash -n` limpo nos três scripts; `shellcheck` quando disponível | T-24, T-29 |
| AC-02 — Templates `data/` com `@EXEC@`, chaves obrigatórias e `OnlyShowIn=MATE;` | T-03, T-04 |
| AC-03 — `--only-mate` instala daemon+GTK, launcher, `.service` e autostarts com modos corretos | T-09, T-13, T-14, T-15 |
| AC-04 — `--all` no Mint degrada com aviso exato, exit 0 e daemon+GTK instalados | T-09, T-15 |
| AC-05 — `--only-kde` sem `kpackagetool6` falha com exit 1 e nada copiado | T-09, T-12, T-15 |
| AC-06 — Auto-detecção MATE/KDE/desconhecido e rejeição de flags conflitantes/desconhecidas | T-09, T-11 |
| AC-07 — `--install-deps` imprime os blocos normativos, sem `sudo`, com status 0/1 correto | T-09, T-12 |
| AC-08 — Instalação idempotente, staging atômico, sem resíduos e sem parar o daemon | T-09, T-13, T-14, T-15 |
| AC-09 — Plasmoid com `-t Plasma/Applet`, `-i`/`-u`/fallback e falha explícita | T-09, T-15, T-17 |
| AC-10 — Launcher wrapper absoluto, `.service`/autostart com `Exec` absoluto e modos 755/644 | T-11, T-13, T-14 |
| AC-11 — `uninstall.sh` com `Quit()` + fallback por PID, UI GTK e sem `pkill -f` | T-10, T-16 |
| AC-12 — Uninstall remove tudo, preserva config, `--purge`, idempotente e tolera ferramenta ausente | T-10, T-17 |
| AC-13 — `verify.sh` com pré-condições, trap, checagens genéricas e estado final OFF | T-18 |
| AC-14 — `verify.sh` MATE com `GetInhibitors` + `mate-screensaver-command` opcional, sem `IsInhibited` | T-19 |
| AC-15 — `verify.sh` KDE com poll de ~8 s, `ActiveInhibitions`/`HasInhibition(4)`, sem `CanSuspend` | T-20 |
| AC-16 — `test_scripts.py` verde: `bash -n`, flags, mensagens, templates, READMEs, créditos e LICENSE | T-03, T-05, T-06, T-07, T-24 |
| AC-17 — `test_installer_scripts.py` verde em `HOME` isolado, com falsos e sem daemon/GUI/barramento | T-08, T-09, T-10, T-25, T-26 |
| AC-18 — READMEs pt-BR/en com comandos equivalentes, checklists completas, limitações e créditos | T-07, T-21, T-22 |
| AC-19 — `LICENSE` e `metadata.json` com razão social/CNPJ; versão `0.1.0`; testes existentes verdes | T-07, T-23 |
| AC-20 — Suíte completa verde; slow opt-in não roda por padrão | T-24, T-25, T-26 |
| AC-21 — Checklist manual Mint 22.3 (instalação, verify, uninstall, autostart) | T-27 |
| AC-22 — Checklist manual Kubuntu 26.04 (auto-KDE, `--all`, `-u`, Plasmoid, verify, uninstall) | T-28 |
| AC-23 — PR somente com os 12 arquivos da E7, sem `core/`/`ui_gtk/`/QML e sem docs de spec | T-29, T-30 |

## Cobertura das decisões do design

| Decisão | Tasks que a fixam |
|---|---|
| §1.1-1 — alvo automático por desktop, flags explícitas vencendo | T-09, T-11 |
| §1.1-2 — testes estáticos + smoke em `HOME` isolado | T-05–T-10, T-25 |
| §1.1-3 — upgrade não interrompe o daemon | T-09, T-13, T-15 |
| §1.1-4 — `verify.sh` sempre termina OFF | T-18 |
| ADR-01 — auto-detecção e exit 2 para desktop desconhecido | T-09, T-11 |
| ADR-02 — templates `data/` com `@EXEC@` e escape de `\`, `&`, `|` | T-03, T-04, T-14 |
| ADR-03 — wrapper `sh` absoluto em `~/.local/bin` | T-14 |
| ADR-04 — autostart do widget com `OnlyShowIn=MATE;` | T-04, T-14 |
| ADR-05 — Plasmoid idempotente com `-t Plasma/Applet`, `-i`/`-u`/`-r` | T-09, T-15, T-17 |
| ADR-06 — upgrade não interrompe; uninstall encerra daemon e UI | T-13, T-16, T-17 |
| ADR-07 — remover estado/log e preservar config até `--purge` | T-17 |
| ADR-08 — `verify.sh` em shell + `gdbus`, sempre OFF | T-18, T-19, T-20 |
| ADR-09 — testes estáticos + sandbox, sem daemon/GUI/instalação real | T-05–T-10, T-24–T-26 |
| ADR-10 — dois READMEs com o mesmo conteúdo normativo | T-21, T-22 |
| ADR-11 — créditos no `metadata.json` sem tocar QML | T-23 |

## Notas de execução

1. **RED obrigatório:** em cada task de teste, rodar o comando e confirmar a falha esperada
   (arquivo ausente ou token ainda não presente). Se um teste passar antes da implementação, é
   regressão — registrar e não “implementar” o que já existe.
2. **Sandbox hermética:** `tests/integration/test_installer_scripts.py` usa `tmp_path` para `HOME`,
   `XDG_DATA_HOME` e `PATH`; `kpackagetool6` e `gdbus` são falsos; nenhum daemon, GUI ou barramento
   real é usado. O teste de fallback por PID usa um `sleep` real, encerrado ao final.
3. **`verify.sh` não roda na suíte:** depende de daemon e backend reais. A validação é manual
   (T-27/T-28); a suíte cobre apenas o contrato estático.
4. **Não alterar `tests/conftest.py`** nem os testes E1–E6; os dois arquivos novos são
   `tests/unit/test_scripts.py` e `tests/integration/test_installer_scripts.py`.
5. **Nunca usar `git add -A`/`git add .`:** `docs/implementation/` (incl. este `tasks_e7.md`) fica
   fora do PR de código; a documentação, se commitada, vai em commit/PR `docs:` separado.
6. **Sem artefatos de spec no código:** scripts, templates, testes e READMEs não podem citar
   `AC-*`, `T-*`, `design_e7.md`, `tasks_e7.md` ou `DELIVERY_MAP.md`. O README pode linkar
   `docs/implementation/spec.md` como documentação de desenvolvedor.
7. **Fora de escopo intocável:** nenhuma alteração em `core/`, `ui_gtk/`, `plasmoid/contents/`,
   `bin/deskawake`, `pyproject.toml`, `assets/` ou `tests/conftest.py`. A única mudança em
   `plasmoid/` é aditiva no `metadata.json`.
8. **Créditos nos quatro lugares:** LICENSE (razão social + CNPJ), READMEs (linha legal),
   `metadata.json` (`Authors`/`Website`/`Copyright` sem ©) e About do GTK (E6, já congelado).
9. **Versão única:** `0.1.0` vem de `core.__version__`; README e E8 leem o mesmo valor; não
   duplicar a fonte.
10. **Documento transitório:** este `tasks_e7.md` é o escopo canônico do `/implement`; não entra no
    PR de código nem é citado em código.

## Execução real

Status: **pendente**. Preencher ao final de cada rodada com baseline, contagens de testes, hashes
de commit e resultado das checklists manuais; manter as divergências e correções registradas aqui.
