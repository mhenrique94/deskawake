# Tasks: E3 — CLI e Launcher

**Feature:** DeskAwake — E3 | **Data:** 2026-11-20 | **Estimativa:** ≈ 9 h (26 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 6 e 21, “Contratos → CLI”, “Notas ao implementador”) | [`design_e3.md`](design_e3.md) | [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E3

## Resumo

- Total de tasks: 26
- Estimativa total: ≈ 9 h (~1 dia de trabalho focado)
- Dependências externas: E2 concluída no branch `feat/e2-inibidores-estado-daemon` (a E3 é **empilhada** sobre a E2; a E4 e a E5 empilharão sobre a E3); `pytest` de desenvolvimento (`python3-pytest` via apt, executado como `python3 -m pytest`); `python3-dbus` e `python3-gi` instalados. **Nenhuma** migration, serviço ou dependência nova de runtime.
- Gate: **G-E3** — `tests/unit/test_cli.py` verde; `tests/unit` completo verde (sem regressão E1/E2); `python3 bin/deskawake --help` verde da raiz e de `/tmp` sem `PYTHONPATH`; `bin/deskawake` executável; validação manual §9.4 do design registrada no PR.
- Fora de escopo (não criar nesta entrega): `ui_gtk/` (E4), `plasmoid/` (E5), `install.sh`/`uninstall.sh`/`verify.sh`/`data/*.service`/autostart/READMEs (E6), qualquer leitura/escrita de `~/.config/deskawake/config.json`, qualquer mudança em `core/inhibitors.py`, `core/state.py`, `core/daemon.py`, `core/environment.py`, `core/config.py` ou no contrato D-Bus da E2, qualquer membro novo no barramento, qualquer teste de GUI.
- Referência de comportamento: em conflito, a `spec.md` vence o `design_e3.md`; as decisões fechadas em 2026-11-20 estão na §1.1 e nas ADRs do design.
- Este arquivo é versionado em `docs/implementation/`; não entra no PR de código nem é citado em código.

**Sequência:** setup → constantes/parser → guarda Wayland → `status` → ações → `daemon` → `ui` → launcher → validação final e entrega. Cada par RED/GREEN executa o teste antes da implementação; não pular o RED.

**Regras de teste que valem para todas as tasks:**

- Unitários **não** abrem barramento real, display nem `ui_gtk`: usam os fakes duck-typed de `tests/conftest.py` (`fake_bus`/`FakeMethod`) e fakes locais do próprio `tests/unit/test_cli.py` (`TrackingStatusBus`, `FakeUiBus`).
- `tests/conftest.py` **não** é alterado; os testes E1/E2 permanecem intactos.
- Seams internas são injetadas por `monkeypatch` de nomes privados (`_session_bus`, `_detect_environment`, `_load_ui_main`, `_daemon_main`) — nenhuma flag nova, nenhuma variável de ambiente nova (exceto o contrato `DESKAWAKE_FORCE_UI`).
- `capsys` para `stdout`/`stderr`; `subprocess` apenas para o launcher (`--help`).
- **Nunca** fechar `dbus.SessionBus()` compartilhado; os fakes são locais e descartáveis.
- Mensagens e tokens: `stdout` só com `on|off|error` (ou `off` no caso inacessível de `status`); diagnóstico em `stderr`, strings exatas da §4.6 do design.

## Tasks

### 0. Setup e fundação

- [ ] **T-01**: Criar a branch da E3 empilhada sobre a E2
  - Comando: `git switch feat/e2-inibidores-estado-daemon && git switch -c feat/e3-cli-launcher`
  - Critério: `git branch --show-current` imprime `feat/e3-cli-launcher`; `git merge-base --is-ancestor feat/e2-inibidores-estado-daemon HEAD` exit 0. **Não** criar a E3 a partir da `main`: o empilhamento é E3 → E2.
  - Estimativa: 5min

- [ ] **T-02**: Conferir as dependências de desenvolvimento e runtime
  - Comandos:
    - `python3 -m pytest --version` (se ausente: `sudo apt install python3-pytest` — passo manual do desenvolvedor)
    - `python3 -c "import dbus, gi; from gi.repository import GLib"`
    - `python3 --version` (≥ 3.10)
  - Critério: todos exit 0; **nenhuma** dependência nova além de `python3-gi`, `python3-dbus` e `pytest` (dev). `pytest` continua dev-only.
  - Estimativa: 5min

- [ ] **T-03**: Rodar a linha de base da E2 antes de tocar em código
  - Comando: `python3 -m pytest tests/unit -q && python3 -m compileall -q core tests`
  - Critério: 0 failures, 0 errors; E1/E2 intactos. Se falhar, parar e resolver antes da E3.
  - Estimativa: 5min

### 1. Constantes, parser e `main()` (TDD)

- [ ] **T-04**: Escrever os testes RED de gramática, `--help` e erros de uso
  - Arquivo: `tests/unit/test_cli.py` (novo)
  - Testes:
    - `test_help_documents_exit_codes` — `main(["--help"])` levanta `SystemExit` com código 0; `stdout` contém `deskawake`, os seis subcomandos e o epílogo exato da §4.6 (`Códigos de saída:` com as 4 linhas `status`/`on|off|toggle`/`ui`/`daemon`); a seam `_session_bus` **não** é chamada (monkeypatch que levanta `AssertionError`).
    - `test_usage_without_subcommand_exits_two` — `main([])` levanta `SystemExit` com código 2.
    - `test_usage_rejects_force_outside_ui` — `main(["status", "--force"])` e `main(["on", "--force"])` levantam `SystemExit` com código 2.
    - `test_main_returns_int_and_never_calls_sys_exit` — `main(["status"])` com seams falsas devolve `int` (não levanta `SystemExit`).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "help or usage or returns_int"`
  - Critério: falha (RED) — `ModuleNotFoundError: No module named 'core.cli'`.
  - Estimativa: 20min

- [ ] **T-05**: Implementar constantes, `_build_parser()` e o esqueleto de `main()`
  - Arquivo: `core/cli.py` (novo)
  - Contrato: ver `design_e3.md` §4.3 e §4.8 — `EXIT_OK/EXIT_ERROR/EXIT_UNREACHABLE`, `PUBLIC_STATES`, `UI_NAME`, `FORCE_UI_ENV`, `BUS_ERRORS`, `CALL_ERRORS`, as cinco `MSG_*` exatas; imports no topo (`dbus`, `DBusGMainLoop`, `Environment`/`detect_environment`/`is_wayland`, `DBUS_NAME`/`OBJECT_PATH`/`INTERFACE` de `core.daemon`); `main(argv=None) -> int` sem `sys.exit`; parser com `prog="deskawake"`, seis subparsers fixos, `--force` **somente** no subparser `ui`, epílogo exato da §4.6. O `main` roteia para `_run_status`/`_run_action`/`_run_ui`/`_daemon_main` (implementadas nas próximas tasks — os testes existentes não as exercitam ainda).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "help or usage or returns_int" && python3 -m compileall -q core/cli.py`
  - Critério: testes de T-04 passam (GREEN); compileall exit 0.
  - Estimativa: 30min

### 2. Guarda Wayland (TDD)

- [ ] **T-06**: Escrever o teste RED da matriz da guarda Wayland
  - Arquivo: `tests/unit/test_cli.py`
  - Teste: `test_wayland_blocked_matrix` — parametrizado sobre `session_type` (`"wayland"`, `"x11"`, `""`) × `wayland_display` (`"wayland-0"`, `None`): bloqueado quando `session_type == "wayland"` **ou** `wayland_display` definido; `Environment` montado à mão (`dataclass` congelado: `desktop`, `session_type`, `wayland_display`, `backends={}`, `tools={}`). Também asserir que `is_wayland()` da E1 mantém a semântica antiga (só `session_type`).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k wayland`
  - Critério: falha (RED) — `AttributeError: module 'core.cli' has no attribute '_wayland_blocked'`.
  - Estimativa: 15min

- [ ] **T-07**: Implementar `_wayland_blocked()`
  - Arquivo: `core/cli.py`
  - Contrato: `design_e3.md` §4.8 — função pura `is_wayland(environment) or environment.wayland_display is not None` (ADR-04: regra combinada mora na CLI; `is_wayland()` da E1 não muda).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k wayland && python3 -m compileall -q core/cli.py`
  - Critério: T-06 passa (GREEN); nenhuma alteração em `core/environment.py`.
  - Estimativa: 10min

### 3. `status` (TDD)

- [ ] **T-08**: Escrever os testes RED de `status`
  - Arquivo: `tests/unit/test_cli.py`
  - Fakes locais: `TrackingStatusBus` (subclasse de `FakeBus` do conftest, com `start_service_by_name()` que registra chamadas para provar que **nunca** é chamado).
  - Testes:
    - `test_status_without_owner_is_unreachable_without_getstate` — sem dono ⇒ exit 3, `stdout` `off\n`, `stderr` `deskawake: daemon inacessível\n`, zero chamadas a `GetState` (nada em `bus.get_object_calls`/`bus.calls`) e zero `start_service_by_name`.
    - `test_status_on` — dono + `GetState()=="on"` ⇒ exit 0, `stdout` `on\n`, `stderr` vazio; `GetState` chamado em `DBUS_NAME`/`OBJECT_PATH`/`INTERFACE`.
    - `test_status_off` — `"off"` ⇒ exit 1, `stdout` `off\n`.
    - `test_status_error` — `"error"` ⇒ exit 1, `stdout` `error\n`.
    - `test_status_getstate_failure_is_unreachable` — `GetState` levanta `dbus.DBusException` ⇒ exit 3, `stdout` `off\n`, `stderr` inacessível.
    - `test_status_bus_failure_is_unreachable` — parametrizado: seam `_session_bus` levanta `dbus.DBusException` / `OSError` / `KeyError` ⇒ exit 3, `stdout` `off\n`, `stderr` inacessível (sem traceback).
    - `test_status_never_calls_start_service_by_name` — com dono e sem dono, `start_service_by_name` nunca é invocado.
    - `test_status_invalid_state_is_unreachable` — `GetState()` devolve `"ligado"` (fora de `PUBLIC_STATES`) ⇒ exit 3, `stdout` `off\n`, `stderr` `deskawake: resposta inválida do daemon\n`.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k status`
  - Critério: falha (RED) — `_run_status`/`_session_bus` ainda não existem.
  - Estimativa: 30min

- [ ] **T-09**: Implementar `_session_bus()` e `_run_status()`
  - Arquivo: `core/cli.py`
  - Contrato: `design_e3.md` §6.1, §4.2 e §4.6 — abre a conexão (`BUS_ERRORS` ⇒ inacessível); `name_has_owner(DBUS_NAME)` primeiro; sem dono/`False`/exceção ⇒ `off` + inacessível + 3, **sem** `GetState` e **sem** `StartServiceByName`; com dono ⇒ `GetState()`; `"on"`→0, `"off"`→1, `"error"`→1; exceção ⇒ `off` + 3; resposta inválida ⇒ `off` + `resposta inválida` + 3. Nenhum `sys.exit`, nenhum traceback cru.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k status && python3 -m compileall -q core/cli.py`
  - Critério: testes de T-08 passam (GREEN); o caminho `status` usa somente `NameHasOwner` + `GetState`.
  - Estimativa: 30min

- [ ] **T-10**: Rodar o arquivo de teste parcial e revisar o caminho `status`
  - Comando: `python3 -m pytest tests/unit/test_cli.py -q`
  - Critério: verde até aqui; mensagens exatas da §4.6 (pt-BR) e tokens `on|off|error` em `stdout`; nenhuma flag nova no parser.
  - Estimativa: 10min

### 4. Ações `on`/`off`/`toggle` (TDD)

- [ ] **T-11**: Escrever os testes RED das ações
  - Arquivo: `tests/unit/test_cli.py`
  - Testes:
    - `test_on_calls_set_active_true` — `main(["on"])` chama `SetActive` com `dbus.Boolean(True)`, imprime `on\n` e retorna 0.
    - `test_off_calls_set_active_false` — `SetActive(dbus.Boolean(False))`, imprime `off\n`, retorna 0.
    - `test_toggle_calls_toggle` — chama `Toggle()`, imprime o retorno, retorna 0.
    - `test_action_error_state_exits_one` — retorno `"error"` ⇒ `stdout` `error\n`, exit 1.
    - `test_action_bus_failure_exits_unreachable` — ação levanta `dbus.DBusException` ⇒ exit 3, `stdout` **vazio**, `stderr` `deskawake: daemon inacessível\n`.
    - `test_action_invalid_state_exits_one` — retorno `"ligado"` ⇒ exit 1, `stdout` **vazio**, `stderr` `deskawake: resposta inválida do daemon\n`.
    - `test_actions_never_check_name_has_owner` — `bus.name_has_owner_calls == []` nos três comandos (ADR-03: a chamada é o gatilho de ativação do `.service` da E6).
    - `test_session_bus_failure_is_unreachable_without_stdout` — `_session_bus` levanta `KeyError` ⇒ exit 3, `stdout` vazio.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "on_calls or off_calls or toggle_calls or action or never_check or without_stdout"`
  - Critério: falha (RED) — `_run_action` ainda não existe.
  - Estimativa: 25min

- [ ] **T-12**: Implementar `_run_action()`
  - Arquivo: `core/cli.py`
  - Contrato: `design_e3.md` §6.2 e §4.6 — `on`→`SetActive(True)`, `off`→`SetActive(False)`, `toggle`→`Toggle()`; sem `NameHasOwner` antes; `"on"`/`"off"` ⇒ `stdout` + 0; `"error"` ⇒ `stdout` + 1; `CALL_ERRORS` ⇒ `stderr` inacessível + 3 sem `stdout`; resposta inválida ⇒ `stderr` resposta inválida + 1 sem `stdout`; não chama `GetLastError` nem imprime motivo.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "on_calls or off_calls or toggle_calls or action or never_check or without_stdout" && python3 -m compileall -q core/cli.py`
  - Critério: testes de T-11 passam (GREEN).
  - Estimativa: 25min

### 5. `daemon` (TDD)

- [ ] **T-13**: Escrever o teste RED da delegação do `daemon`
  - Arquivo: `tests/unit/test_cli.py`
  - Teste: `test_daemon_delegates_to_core_daemon` — monkeypatch de `core.daemon.main` devolvendo 42 ⇒ `main(["daemon"])` retorna 42; `_session_bus` **não** é chamado (monkeypatch levantando `AssertionError`); nenhuma flag é aceita (`main(["daemon", "--force"])` ⇒ `SystemExit` 2).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k daemon`
  - Critério: falha (RED) — `_daemon_main` ainda não existe.
  - Estimativa: 15min

- [ ] **T-14**: Implementar `_daemon_main()`
  - Arquivo: `core/cli.py`
  - Contrato: `design_e3.md` §6.3 e ADR-11 — chama `core.daemon.main()` **sem argumentos**, devolve o `int`; a CLI não abre barramento para `daemon`, não faz double-fork, não redireciona `stdout`, não instala sinais.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k daemon && python3 -m compileall -q core/cli.py`
  - Critério: T-13 passa (GREEN).
  - Estimativa: 10min

### 6. `ui` — guarda, single-instance e loader (TDD)

- [ ] **T-15**: Escrever os testes RED da guarda Wayland e da ordem do GLib
  - Arquivo: `tests/unit/test_cli.py`
  - Testes:
    - `test_ui_refuses_wayland` — `Environment(session_type="wayland")`, sem force ⇒ exit 1, `stdout` vazio, `stderr` é **exatamente** `deskawake: a UI GTK não é suportada em Wayland; use o Plasmoid do KDE ou repita com --force (ou DESKAWAKE_FORCE_UI=1) para depuração\n` (menciona `--force` e `Plasmoid`); `_load_ui_main` **não** é chamado e `request_name` **não** é chamado.
    - `test_ui_refuses_wayland_display` — `session_type="x11"` + `wayland_display="wayland-0"`, sem force ⇒ mesma recusa (exit 1, loader não chamado).
    - `test_ui_registers_glib_loop_before_detection` — `DBusGMainLoop(set_as_default=True)` é registrado **antes** de `_detect_environment()` (monkeypatch com registro de ordem; ADR-13).
    - `test_ui_blocked_does_not_import_ui_gtk` — na recusa, o loader fake não é invocado (nenhum import de `ui_gtk`).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "ui_refuses or glib or does_not_import"`
  - Critério: falha (RED) — o caminho `ui` ainda não existe em `main`.
  - Estimativa: 25min

- [ ] **T-16**: Implementar o caminho `ui` com guarda e escapes
  - Arquivo: `core/cli.py`
  - Contrato: `design_e3.md` §6.4 passos 1–3 — `DBusGMainLoop(set_as_default=True)` antes de `_detect_environment()`; `_wayland_blocked()`; bloqueado sem escape ⇒ `stderr` + exit 1 **antes** de `RequestName` e **antes** de qualquer import de `ui_gtk`; escape = `args.force` **ou** `os.environ.get("DESKAWAKE_FORCE_UI") == "1"` (somente o valor exato `1`; `0`/vazio/`true` não ligam).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "ui_refuses or glib or does_not_import" && python3 -m compileall -q core/cli.py`
  - Critério: testes de T-15 passam (GREEN); nenhum `Gtk`/`Gdk` importado nesse caminho.
  - Estimativa: 25min

- [ ] **T-17**: Escrever os testes RED do single-instance e do loader
  - Arquivo: `tests/unit/test_cli.py`
  - Fakes locais: `FakeUiBus` (duck-typed, com `request_name(name, flags)` configurável para `PRIMARY_OWNER`/`EXISTS`/`IN_QUEUE`/outro valor e lista `request_name_calls`).
  - Testes:
    - `test_ui_force_calls_main` — `main(["ui", "--force"])` em ambiente Wayland ⇒ loader fake chamado **uma vez**, `main()` da UI fake chamado, exit 0, `stdout` vazio.
    - `test_ui_force_env_calls_main` — `DESKAWAKE_FORCE_UI=1` equivale a `--force` (mesmo resultado do teste anterior).
    - `test_ui_force_env_requires_exact_one` — `DESKAWAKE_FORCE_UI=0` / `=true` **não** ligam o escape (recusa, exit 1).
    - `test_ui_second_instance_exits_zero` — `request_name` devolve `EXISTS` ⇒ exit 0, loader **não** chamado, `stdout` e `stderr` vazios.
    - `test_ui_request_name_uses_do_not_queue` — a chamada é `request_name("org.local.DeskAwake.Ui", dbus.bus.NAME_FLAG_DO_NOT_QUEUE)` (ADR-05).
    - `test_ui_bus_failure_exits_one` — `_session_bus` levanta `KeyError`/`dbus.DBusException` ⇒ exit 1, `stderr` `deskawake: barramento de sessão indisponível\n`, `stdout` vazio.
    - `test_ui_loader_failure_exits_one` — loader levanta `ImportError("ui_gtk não existe")` ⇒ exit 1, `stderr` `deskawake: falha ao iniciar a UI: ui_gtk não existe\n`, sem traceback cru (cobre a E3 sem E4).
    - `test_ui_unexpected_request_name_result_exits_one` — devolve um valor inesperado ⇒ exit 1, `stderr` `deskawake: falha ao iniciar a UI\n`.
    - `test_ui_loader_not_called_before_request_name` — na segunda instância e na recusa, o loader nunca é invocado (import tardio, ADR-05).
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "ui_"` (sem `ui_refuses` — já verde)
  - Critério: falha (RED) — `_run_ui`/`_load_ui_main` ainda não existem.
  - Estimativa: 30min

- [ ] **T-18**: Implementar `_load_ui_main()` e `_run_ui()`
  - Arquivo: `core/cli.py`
  - Contrato: `design_e3.md` §6.4 passos 4–7 e §4.7 — abre a conexão (`BUS_ERRORS` ⇒ barramento indisponível + 1); `request_name(UI_NAME, NAME_FLAG_DO_NOT_QUEUE)`: `EXISTS`/`IN_QUEUE` ⇒ 0 silencioso; `PRIMARY_OWNER`/`ALREADY_OWNER` ⇒ chama `ui_loader()`; outro ⇒ `MSG_UI_FAILED` + 1. `_load_ui_main()` importa `ui_gtk.widget` **dentro** da função e devolve `main` (import tardio; `ui_gtk` não pode entrar em `sys.modules` no carregamento de `core.cli`). Qualquer exceção do loader/UI ⇒ `MSG_UI_FAILED: <motivo>` + 1. O nome permanece com a conexão até o processo terminar.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k "ui_" && python3 -m compileall -q core/cli.py`
  - Critério: testes de T-17 passam (GREEN); `python3 -m pytest tests/unit/test_cli.py -q` inteiro verde.
  - Estimativa: 30min

- [ ] **T-19**: Auditar imports e mensagens do `core/cli.py`
  - Comandos:
    - `python3 -c "import sys, core.cli; assert 'ui_gtk' not in sys.modules; assert not any(m.startswith('gi.repository.Gtk') for m in sys.modules)"` ⇒ exit 0
    - `grep -n "StartServiceByName\|GetLastError" core/cli.py` ⇒ sem saída
    - `grep -n "os.environ" core/cli.py` ⇒ apenas a leitura de `DESKAWAKE_FORCE_UI`
    - `python3 -m pytest tests/unit/test_cli.py -q` ⇒ verde
  - Critério: `core/cli.py` importável sem display; nenhum `Gtk`/`Gdk`; nenhuma chamada proibida; só a env contratada é lida.
  - Estimativa: 10min

### 7. Launcher `bin/deskawake`

- [ ] **T-20**: Escrever os testes RED do launcher
  - Arquivo: `tests/unit/test_cli.py`
  - Testes:
    - `test_launcher_is_executable` — `bin/deskawake` existe, tem bit executável (`os.access(..., os.X_OK)`) e shebang `#!/usr/bin/env python3`.
    - `test_launcher_help_from_repo_root` — `subprocess.run([sys.executable, "bin/deskawake", "--help"], cwd=raiz_do_repo)` ⇒ returncode 0, `stdout` contém `deskawake` e `Códigos de saída:`.
    - `test_launcher_help_from_tmp_without_pythonpath` — `cwd=tmp_path`, caminho **absoluto** do launcher, ambiente **sem** `PYTHONPATH` ⇒ returncode 0, `stdout` contém os subcomandos.
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v -k launcher`
  - Critério: falha (RED) — `bin/deskawake` ainda não existe.
  - Estimativa: 20min

- [ ] **T-21**: Criar `bin/deskawake` executável
  - Arquivo: `bin/deskawake` (novo)
  - Contrato: `design_e3.md` §4.4 e ADR-06 — código exato: `ROOT = Path(__file__).resolve().parent.parent`, inserir no `sys.path` se ausente, `from core.cli import main`, `raise SystemExit(main())` sob `if __name__ == "__main__"`; `chmod +x`; sem lógica além do bootstrap; não lê CWD nem `PYTHONPATH`.
  - Comandos:
    - `python3 -m pytest tests/unit/test_cli.py -v -k launcher`
    - `python3 bin/deskawake --help` ⇒ exit 0 (da raiz)
    - `cd /tmp && env -u PYTHONPATH python3 /home/marcelosilva/Github/deskawake/bin/deskawake --help` ⇒ exit 0 (caminho absoluto)
  - Critério: os três comandos exit 0; testes de T-20 passam (GREEN).
  - Estimativa: 15min

### 8. Validação final e entrega

- [ ] **T-22**: Rodar a suíte da entrega (gate unitário da E3)
  - Comando: `python3 -m pytest tests/unit/test_cli.py -v`
  - Critério: 0 failures, 0 errors, 0 skipped; todos os testes da §9.2 do design presentes e verdes.
  - Estimativa: 5min

- [ ] **T-23**: Rodar a suíte completa sem regressão
  - Comando: `python3 -m pytest tests/unit -q && python3 -m compileall -q core tests`
  - Critério: 0 failures, 0 errors; E1 (`test_config`, `test_environment`) e E2 (`test_inhibitors`, `test_state`) intactos; compileall exit 0.
  - Estimativa: 5min

- [ ] **T-24**: Auditar escopo, higiene e dependências
  - Comandos:
    - `grep -RInE "AC-[0-9]|T-[0-9]|design_e|tasks_e|spec\.md|DELIVERY_MAP" core bin tests` ⇒ sem saída
    - `grep -RInE "ui_gtk|plasmoid|install\.sh|config\.json" core/cli.py bin/deskawake` ⇒ sem saída (exceto o import tardio `ui_gtk.widget` em `_load_ui_main`)
    - `python3 -m py_compile bin/deskawake` ⇒ exit 0
    - `git status --short` ⇒ apenas os 3 arquivos da entrega (`core/cli.py`, `bin/deskawake`, `tests/unit/test_cli.py`) + pré-existentes; nenhum artefato gerado
    - `python3 -m pytest tests/unit -q` ⇒ verde
  - Critério: todos os comandos conforme acima; nenhuma dependência de runtime nova; nenhuma decisão da `spec.md` contrariada (estados só `on|off|error`; `status` sem auto-start; guarda Wayland; single-instance; `--force` só em `ui`).
  - Estimativa: 10min

- [ ] **T-25**: Validação manual rápida (Mint) e registro do resultado
  - Comandos (design §9.4; em dois terminais):
    - `./bin/deskawake status; echo $?` ⇒ 3 se o daemon não estiver rodando (mensagem em `stderr`, `off` em `stdout`)
    - `./bin/deskawake daemon` (foreground no outro terminal)
    - `./bin/deskawake on; echo $?` ⇒ 0 imprimindo `on`; `./bin/deskawake status; echo $?` ⇒ 0
    - `./bin/deskawake off; echo $?` ⇒ 0 imprimindo `off`; `./bin/deskawake status; echo $?` ⇒ 1
    - `./bin/deskawake ui` ⇒ no Kubuntu (Wayland) recusa com a mensagem citando `--force` e o Plasmoid, exit 1, sem janela
  - Critério: comportamento conforme a §4.6 em todos os passos; na E3 (sem `.service`), ações sem daemon retornam 3 — comportamento esperado; resultados colados no corpo do PR. Se a máquina não estiver disponível, registrar a pendência no PR (não bloqueia o gate automatizado).
  - Estimativa: 20min

- [ ] **T-26**: Preparar commit e PR somente com a entrega
  - Comandos:
    - `git add core/cli.py bin/deskawake tests/unit/test_cli.py`
    - `git diff --cached --name-only` ⇒ exatamente os 3 arquivos (o bit executável de `bin/deskawake` preservado)
    - `python3 -m pytest tests/unit/test_cli.py -v` ⇒ gate unitário verde
    - `python3 -m pytest tests/unit -q` ⇒ suíte completa verde
    - `git commit -m "feat(e3): CLI e launcher"`
    - `git push -u origin feat/e3-cli-launcher`
    - `gh pr create --base feat/e2-inibidores-estado-daemon --head feat/e3-cli-launcher --title "feat(e3): CLI e launcher" --body "<corpo no template do DELIVERY_MAP §0.2>"`
    - `gh pr view --json baseRefName,headRefName,files --jq '{base: .baseRefName, head: .headRefName, files: [.files[].path]}'` ⇒ base `feat/e2-inibidores-estado-daemon`, head `feat/e3-cli-launcher` e apenas os 3 arquivos
  - Corpo do PR: gate com comando/resultado (unit + launcher + manual), checklist manual preenchida, fora de escopo (E4/E5/E6) e riscos residuais (§10 do design); **não** citar `spec.md`, `design_e3.md`, `tasks_e3.md` nem IDs `AC-*`/`T-*`.
  - Critério: PR contém apenas os 3 arquivos; base é a branch da E2 (empilhamento), **não** `main`, sem retarget sem confirmação; `docs/implementation/` e `README.md` fora do stage/PR de código. **Nunca** usar `git add -A`/`git add .`.
  - Estimativa: 20min

## Mapeamento AC → Tasks

Os critérios vêm do `DELIVERY_MAP.md` §E3.4 (automático e manual) e do gate G-E3 do `design_e3.md` §9.5.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-01 — `status` sem daemon ⇒ exit 3, zero `GetState`/`StartServiceByName` | T-08, T-09 |
| AC-02 — `status` com `GetState()` `on`/`off`/`error` ⇒ exit 0/1/1 e `stdout` correspondente | T-08, T-09 |
| AC-03 — `on`/`off`/`toggle` chamam o método certo e imprimem o retorno (exit 0) | T-11, T-12 |
| AC-04 — `ui` com `XDG_SESSION_TYPE=wayland` ⇒ exit ≠ 0, mensagem cita `--force`/Plasmoid, UI não chamada | T-15, T-16 |
| AC-05 — `ui` com `WAYLAND_DISPLAY` definido e sem `--force` ⇒ recusa | T-06, T-07, T-15, T-16 |
| AC-06 — `ui --force` ⇒ chama `main()` fake, sem abrir janela | T-17, T-18 |
| AC-07 — `DESKAWAKE_FORCE_UI=1` equivale a `--force`; outros valores não ligam | T-17, T-18 |
| AC-08 — Segunda instância (`RequestName` `EXISTS`) ⇒ exit 0, `main()` não chamado | T-17, T-18 |
| AC-09 — `python3 bin/deskawake --help` da raiz e de `/tmp` (absoluto), sem `PYTHONPATH` | T-20, T-21 |
| AC-10 — Uso inválido (sem subcomando/flag extra) ⇒ exit 2 do `argparse`; nenhum caminho de estado retorna 2 | T-04, T-05 |
| AC-11 — Falha de comunicação: ações exit 3 sem `stdout`; `ui` exit 1; mensagens exatas em `stderr` | T-08, T-09, T-11, T-12, T-17, T-18 |
| AC-12 — Resposta inválida do daemon: `status` ⇒ 3 com `off`; ações ⇒ 1 sem `stdout` | T-08, T-09, T-11, T-12 |
| AC-13 — `daemon` delega a `core.daemon.main()` e propaga o código (foreground, sem flags) | T-13, T-14 |
| AC-14 — `bin/deskawake` executável com shebang `#!/usr/bin/env python3` | T-20, T-21 |
| AC-M01 — Manual: ciclo `status`/`on`/`status`/`off`/`status` coerente com 0/1/3; recusa Wayland no Kubuntu | T-25 |
| AC-G01 — Gate unitário da entrega verde | T-22 |
| AC-G02 — Suíte completa sem regressão E1/E2 | T-23 |
| AC-G03 — Nenhuma dependência nova; nenhum `Gtk`/`ui_gtk` no carregamento da CLI | T-02, T-19, T-24 |
| AC-G04 — Nenhum artefato de spec em código/comentários/commits/PRs | T-24, T-26 |
| AC-G05 — `docs/implementation/` fora do PR de código; PR empilhado sobre a E2 | T-26 |

## Cobertura das decisões do design (ADR)

| Decisão | Tasks que a fixam |
|---|---|
| ADR-01 — códigos 0/1/3 nas ações/`status`; `2` só do `argparse` | T-04, T-05, T-08, T-11 |
| ADR-02 — `status` só leitura: `NameHasOwner` primeiro, nunca `StartServiceByName` | T-08, T-09 |
| ADR-03 — ações chamam D-Bus direto, sem `NameHasOwner` (ativação via `.service` na E6) | T-11, T-12 |
| ADR-04 — guarda Wayland combinada em `_wayland_blocked()` pura na CLI | T-06, T-07, T-15, T-16 |
| ADR-05 — single-instance com `DO_NOT_QUEUE` + import tardio do GTK via `ui_loader` | T-17, T-18, T-19 |
| ADR-06 — launcher portátil por `__file__`, sem CWD/`PYTHONPATH` | T-20, T-21 |
| ADR-07 — seams privadas (`_session_bus`, `_detect_environment`, `_load_ui_main`, `_daemon_main`) sem flags/env novas | T-08–T-18 (monkeypatch) |
| ADR-08 — mensagens em pt-BR; tokens de estado em inglês; strings exatas da §4.6 | T-04, T-08, T-11, T-15, T-17 |
| ADR-09 — `argparse` mínimo: `prog="deskawake"`, `--force` só em `ui`, epílogo com códigos | T-04, T-05 |
| ADR-10 — respostas inválidas validadas contra `PUBLIC_STATES` (status 3 / ações 1) | T-08, T-11 |
| ADR-11 — `daemon` em foreground delegando a `core.daemon.main()` sem argumentos | T-13, T-14 |
| ADR-12 — `DBUS_NAME`/`OBJECT_PATH`/`INTERFACE` importados de `core.daemon` (fonte única) | T-05 |
| ADR-13 — `DBusGMainLoop(set_as_default=True)` registrado antes da detecção no caminho `ui` | T-15, T-16 |

## Notas de execução

1. **RED obrigatório:** em cada task de teste, rodar o comando e confirmar a falha esperada (import ausente, atributo ausente ou asserção). Se um teste passar antes da implementação, ele é regressão — registrar na task e não “implementar” o que já existe.
2. **Sem display, sem barramento real, sem `ui_gtk`:** toda a suíte da E3 roda headless; a interface `ui` é validada só com loader fake até a E4. Nenhum teste fecha `dbus.SessionBus()` compartilhado.
3. **Não alterar `tests/conftest.py`** nem os testes E1/E2; os fakes necessários (`TrackingStatusBus`, `FakeUiBus`) vivem em `tests/unit/test_cli.py`.
4. **Nunca usar `git add -A`/`git add .`:** `README.md`, `docs/implementation/` e artefatos gerados ficam fora do PR de código; a documentação vai em PR/commit `docs:` separado.
5. **Sem artefatos de spec no código:** `core/` e `tests/` não podem citar `AC-*`, `T-*`, `design_e3.md`, `tasks_e3.md`, `spec.md` ou `DELIVERY_MAP.md` em código, comentários, commits ou corpo do PR.
6. **Fora de escopo intocável:** nenhuma alteração em `core/daemon.py`, `core/environment.py`, `core/state.py`, `core/inhibitors.py`, `core/config.py`, no contrato D-Bus da E2 ou em `tests/conftest.py`; nenhum arquivo de E4/E5/E6.
7. **PRs empilhados:** E3 → E2, E4 → E3, E5 → E3 (paralela à E4), E6 só depois de E4 e E5 mergeadas. A branch da E3 nasce de `feat/e2-inibidores-estado-daemon` e o PR tem essa branch como base; não retargetar para `main` sem confirmação.
