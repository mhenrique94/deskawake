# Tasks: E2 — Núcleo de Inibição, Máquina de Estados e Daemon

**Feature:** DeskAwake — E2 | **Data:** 2026-11-20 | **Estimativa:** ≈ 25 h (68 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 1–33, “Fluxo alvo”, “Contratos”, “Notas ao implementador”) | [`design_e2.md`](design_e2.md) | [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E2

## Resumo

- Total de tasks: 68
- Estimativa total: ≈ 25 h (~3 dias de trabalho focado)
- Dependências externas: E1 concluída no branch `feat/e1-esqueleto-ambiente-config` (a E2 é **empilhada** sobre a E1; a E3 será empilhada sobre a E2 e a E4 sobre a E3); `pytest` de desenvolvimento (`python3-pytest` via apt); `dbus-run-session`, `dbus-daemon`, `systemd-inhibit`, `ps`, `gdbus` presentes; `python3-dbus` e `python3-gi` instalados. Nenhuma migration, serviço ou dependência nova de runtime.
- Gate: **G-E2** — unitários + integração em barramento privado verdes; `SIGTERM`/`SIGINT`/`Quit`/`PDEATHSIG`/`Local.Disconnected` comprovados; nenhum processo órfão.
- Fora de escopo (não criar nesta entrega): `core/cli.py`, `bin/deskawake`, `ui_gtk/`, `plasmoid/`, `data/`, `install.sh`, `uninstall.sh`, `verify.sh`, READMEs, qualquer leitura/escrita de `core/config.py` pelo daemon e qualquer estado persistido.
- Referência de comportamento: em conflito, a `spec.md` vence o `design_e2.md`; as decisões fechadas em 2026-11-20 estão no §E2.5 do mapa e nas ADRs do design.

**Sequência:** setup → fixtures unitárias → `SystemdInhibit` → `ScreenSaverInhibit` → `StateMachine` → fakes/harness de integração → `daemon` → validação final e entrega. Cada par RED/GREEN executa o teste antes da implementação; não pular o RED.

**Regras de teste que valem para todas as tasks:**

- Unitários não abrem barramento real, display, `systemd-inhibit` real nem criam processos: usam fakes duck-typed de `tests/conftest.py`.
- Integração roda sempre sob `dbus-run-session`; fakes são processos reais no barramento privado e o daemon roda em subprocesso.
- Espera de prontidão é sempre `wait_until`/`name_has_owner` com timeout; **nunca** `sleep` fixo.
- Timeouts (`verify_delay`, `debounce`, `confirm_delay`) são injetados nos testes de integração e restaurados pelo `fixture`/teardown.
- Testes não dependem do texto exato de `last_error`/log, exceto `who`/`why` (`deskawake`/`DeskAwake active`) e o `stderr` forçado.

## Tasks

### 0. Setup e fundação

- [ ] **T-01**: Criar a branch da E2 empilhada sobre a E1
  - Comando: `git switch feat/e1-esqueleto-ambiente-config && git pull --ff-only && git merge-base --is-ancestor 787fa30 HEAD && git switch -c feat/e2-inibidores-estado-daemon`
  - Critério: `git branch --show-current` imprime `feat/e2-inibidores-estado-daemon`; `git merge-base --is-ancestor feat/e1-esqueleto-ambiente-config HEAD` exit 0; `git log --oneline -3` mostra o commit da E1 (`787fa30`). **Não** criar a E2 a partir da `main`: o empilhamento é E2 → E1.
  - Estimativa: 5min

- [ ] **T-02**: Conferir as dependências de desenvolvimento e runtime
  - Comandos:
    - `python3 -m pytest --version` (se ausente: `sudo apt install python3-pytest` — passo manual do desenvolvedor; não criar script nem alterar `pyproject.toml`)
    - `dbus-run-session --version`
    - `dbus-daemon --version`
    - `systemd-inhibit --version`
    - `command -v ps gdbus`
    - `python3 -c "import dbus, gi; from gi.repository import GLib"`
  - Critério: todos exit 0; **nenhuma** dependência nova além de `python3-gi`, `python3-dbus`, `systemd` e `pytest` (dev).
  - Estimativa: 10min

- [ ] **T-03**: Rodar a linha de base da E1 antes de tocar em código
  - Comando: `python3 -m pytest tests/unit -v && python3 -m compileall -q core tests`
  - Critério: 0 failures, 0 errors; E1 intacta. Se falhar, parar e resolver antes da E2.
  - Estimativa: 5min

- [ ] **T-04**: Criar os diretórios de integração
  - Arquivos: `tests/integration/` (diretório) e `tests/integration/fakes/` (diretório); sem `__init__.py`
  - Comando: `test -d tests/integration/fakes && test -z "$(find tests -name '__init__.py' -print -quit)"`
  - Critério: exit 0; nenhum `__init__.py` em `tests/`.
  - Estimativa: 2min

### 1. Fixtures unitárias (`tests/conftest.py`)

- [ ] **T-05**: Criar os fakes de barramento e de métodos D-Bus
  - Arquivo: `tests/conftest.py`
  - Conteúdo:
    - `FakeMethod` — registra `calls`, devolve `return_value` ou levanta `raises`.
    - `FakeProxy` — `get_dbus_method(member, iface)` devolve o `FakeMethod` do membro (compatível com `dbus.Interface` real).
    - `FakeBus` — `name_has_owner(name)` consulta um conjunto de donos; `get_object(name, path)` devolve o `FakeProxy` registrado; métodos para marcar/desmarcar dono e inspecionar chamadas.
    - Fixture `fake_bus` que devolve uma fábrica (`make_bus(owners=..., methods={...})`).
  - Comando: `python3 -m compileall -q tests/conftest.py && python3 -m pytest tests/unit -q`
  - Critério: compileall exit 0; suíte da E1 continua verde; um teste de fumaça local (fora de `tests/`) confirma que `dbus.Interface(fake_proxy, "x").Metodo()` chega ao `FakeMethod` — pode ser feito no REPL e não vira arquivo.
  - Estimativa: 20min

- [ ] **T-06**: Criar os fakes de inibidores e agendador
  - Arquivo: `tests/conftest.py`
  - Conteúdo:
    - `FakeSystemd` — `alive` mutável, `start()`/`stop()` configuráveis para levantar, registra ordem das chamadas.
    - `FakeScreen` — `acquire()`/`confirm()`/`release()` configuráveis, `backend`, `needs_verification`, registra chamadas e permite inspecionar `acquired_cookie`.
    - `FakeScheduler` — `schedule(delay, callback)` guarda `{id: (delay, callback)}`; `cancel(id)` remove; `fire()` executa os pendentes e remove os que retornarem falso (semântica `GLib.SOURCE_REMOVE`); registra delays.
    - `FakeProcess` — `pid`, `poll()`, `wait(timeout)`, `communicate()`, `stderr`; sequência de `wait` configurável (retorna ou levanta `subprocess.TimeoutExpired`).
    - Fixtures `fake_systemd`, `fake_screen`, `fake_scheduler`, `fake_process` e `fake_popen` (monkeypatch de `subprocess.Popen`).
  - Comando: `python3 -m compileall -q tests/conftest.py && python3 -m pytest tests/unit -q`
  - Critério: compileall exit 0; E1 verde; os fakes são importáveis sem abrir barramento/processo.
  - Estimativa: 15min

### 2. `SystemdInhibit` — `core/inhibitors.py` (TDD)

- [ ] **T-07**: Escrever os testes RED de `SystemdInhibit.start()`, `alive` e `pid`
  - Arquivo: `tests/unit/test_inhibitors.py`
  - Testes:
    - `test_systemd_command_has_exact_args` — argv exatamente `["systemd-inhibit", "--what=idle", "--mode=block", "--who=DeskAwake", "--why=DeskAwake active", "sleep", "infinity"]`; `--what=sleep` ausente; `--what=idle` presente; `start_new_session=True`, `stdin=subprocess.DEVNULL`, `stdout=subprocess.DEVNULL`, `stderr=subprocess.PIPE`, `preexec_fn` chamável.
    - `test_start_raises_with_stderr_when_child_dies` — `poll()` devolve 1; `communicate()` devolve `(b"", b"falha do logind")`; `InhibitError` com `"falha do logind"` no texto.
    - `test_start_missing_binary_raises_inhibit_error` — `Popen` levanta `FileNotFoundError`; `InhibitError`.
    - `test_start_raises_with_exit_code_when_stderr_empty` — `poll()` devolve 1 e `stderr` vazio; mensagem contém o código.
    - `test_alive_and_pid_reflect_process` — `poll() is None` ⇒ `alive is True` e `pid` igual; `poll() == 0` ⇒ `alive is False`.
    - `test_start_is_idempotent_when_alive` — dois `start()` com o filho vivo ⇒ `Popen` chamado uma vez.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "systemd or start or alive"`
  - Critério: falha (RED) porque `core.inhibitors`/`SystemdInhibit` ainda não existe. Nos testes, instanciar com `confirm_delay=0` para não somar 0,2 s por caso.
  - Estimativa: 20min

- [ ] **T-08**: Implementar `InhibitError`, constantes e `SystemdInhibit` (start/alive/pid)
  - Arquivo: `core/inhibitors.py`
  - Contrato: ver `design_e2.md` §4.1; `_pdeathsig` com `prctl(PR_SET_PDEATHSIG, SIGTERM)` e `os._exit(1)` se `getppid() == 1`; `start()` idempotente, espera `confirm_delay` (padrão 0,2 s), verifica `poll()`, lê `stderr` com `communicate()` e fecha o pipe; `FileNotFoundError`/`OSError` ⇒ `InhibitError`; `alive`/`pid` derivados de `_proc`.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "systemd or start or alive" && python3 -m compileall -q core/inhibitors.py`
  - Critério: testes de T-07 passam (GREEN); compileall exit 0.
  - Estimativa: 25min

- [ ] **T-09**: Escrever os testes RED de `SystemdInhibit.stop()`
  - Arquivo: `tests/unit/test_inhibitors.py`
  - Testes (monkeypatch de `os.killpg` e `time.sleep`/`monotonic` quando necessário):
    - `test_stop_kills_process_group_in_order` — `os.killpg(pid, SIGTERM)`; `wait(timeout=2)`; pipe fechado.
    - `test_stop_escalates_after_timeout` — primeiro `wait` levanta `TimeoutExpired`; depois `os.killpg(pid, SIGKILL)` e novo `wait(timeout=2)`. Ordem registrada `[SIGTERM, SIGKILL]`.
    - `test_stop_is_idempotent_when_dead` — `poll()` devolve 0; nenhum `killpg`; `wait` para reapear; segundo `stop()` não levanta.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k stop`
  - Critério: falha (RED) porque `stop()` ainda não existe.
  - Estimativa: 15min

- [ ] **T-10**: Implementar `SystemdInhibit.stop()`
  - Arquivo: `core/inhibitors.py`
  - Contrato: `killpg` no grupo (pgid == pid), `wait(timeout=2)`, `SIGKILL` + `wait(timeout=2)` em `TimeoutExpired`; absorver `ProcessLookupError`/`PermissionError`; fechar pipe; idempotente; reapear processo morto.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k stop`
  - Critério: testes de T-09 passam (GREEN); nenhum `killpg(pid, ...)` com PID isolado.
  - Estimativa: 20min

- [ ] **T-11**: Refatorar `SystemdInhibit`
  - Arquivo: `core/inhibitors.py`
  - Critério: extrair `_pdeathsig` e `_build_command` se necessário; sem shell; `sleep` apenas como comando, nunca em `--what`; rodar `python3 -m pytest tests/unit/test_inhibitors.py -v -k "systemd or start or stop or alive"` e `python3 -m compileall -q core/inhibitors.py` com exit 0.
  - Estimativa: 10min

### 3. `ScreenSaverInhibit` — `core/inhibitors.py` (TDD)

- [ ] **T-12**: Escrever os testes RED de `acquire()` — cadeia, confirmações e fallback
  - Arquivo: `tests/unit/test_inhibitors.py`
  - Testes:
    - `test_backend_chain_fdo` — só FDO no barramento; `Inhibit` devolve 42; `backend == "fdo"`, `path == "/org/freedesktop/ScreenSaver"`, `cookie == 42`.
    - `test_backend_chain_mate` — MATE + GSM; `GetInhibitors` contém `Application=deskawake`; `IsInhibited(8) is True`; `backend == "mate"`, `cookie` do MATE.
    - `test_backend_chain_gsm` — só GSM; `backend == "gsm"`; `xid == 0`, `flags == 8` (asserção sobre os argumentos).
    - `test_gsm_uses_xid_zero_and_flags_eight` — argumentos exatos `("deskawake", UInt32(0), "DeskAwake active", UInt32(8))`.
    - `test_fdo_inhibit_failure_falls_through_to_mate` — FDO `Inhibit` levanta `DBusException`; MATE confirmado; `backend == "mate"`; nenhum cookie FDO órfão.
    - `test_no_backend_raises_inhibit_error_with_reasons` — nenhum dono; `InhibitError` com `fdo`, `mate` e `gsm` no texto.
    - `test_mate_confirmed_does_not_inhibit_gsm` — MATE + GSM presentes; nenhuma chamada `Inhibit` no GSM.
    - `test_mate_proxy_failure_falls_back_to_gsm` — MATE `GetInhibitors` contém a aplicação, mas `IsInhibited(8)` é `False`; `UnInhibit(cookie_mate)` e `Inhibit` no GSM; `backend == "gsm"`.
    - `test_acquire_releases_partial_mate_cookie_before_gsm` — ordem registrada: `UnInhibit` do MATE antes do `Inhibit` do GSM.
    - `test_gsm_confirmation_failure_releases_and_raises` — só GSM com `IsInhibited(8) False`; `Uninhibit(cookie)` e `InhibitError`.
    - `test_acquire_failure_does_not_hold_partial_cookie` — em qualquer falha, `cookie is None` ao final.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "backend_chain or mate or fdo or gsm or no_backend or acquire"`
  - Critério: falha (RED) porque `ScreenSaverInhibit` ainda não existe.
  - Estimativa: 30min

- [ ] **T-13**: Implementar `ScreenSaverInhibit.acquire()`
  - Arquivo: `core/inhibitors.py`
  - Contrato: ver `design_e2.md` §4.1; ordem `fdo` → `mate` → `gsm`; pular nome sem dono; FDO/MATE `Inhibit(who, why)`; GSM `Inhibit(who, UInt32(0), why, UInt32(8))`; confirmação MATE (`GetInhibitors` + `IsInhibited(8)` quando GSM existir) e GSM (`IsInhibited(8)`); liberar cookie parcial antes de cair para GSM; guardar `backend`/`path`/`cookie`/`_acquired_at`; erro agregado com motivos.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "backend_chain or mate or fdo or gsm or no_backend or acquire" && python3 -m compileall -q core/inhibitors.py`
  - Critério: testes de T-12 passam (GREEN); nenhuma chamada a `PolicyAgent` para inibir.
  - Estimativa: 40min

- [ ] **T-14**: Escrever os testes RED de `release()`
  - Arquivo: `tests/unit/test_inhibitors.py`
  - Testes:
    - `test_release_uses_correct_method_names` — parametrizado `fdo`/`mate`/`gsm`: `UnInhibit(cookie)` em FDO/MATE e `Uninhibit(cookie)` no GSM (asserção sobre o nome do método no fake).
    - `test_release_keeps_last_backend_and_clears_cookie` — após `release()`, `cookie is None`, `backend` e `path` preservados.
    - `test_release_is_idempotent` — segundo `release()` sem chamadas D-Bus e sem exceção.
    - `test_release_absorbs_dbus_exception` — `UnInhibit`/`Uninhibit` levanta `DBusException`; não propaga; `cookie is None`.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k release`
  - Critério: falha (RED) porque `release()` ainda não existe.
  - Estimativa: 15min

- [ ] **T-15**: Implementar `ScreenSaverInhibit.release()`
  - Arquivo: `core/inhibitors.py`
  - Contrato: `UnInhibit` (FDO/MATE) / `Uninhibit` (GSM) na **mesma conexão**; absorver `DBusException`/`OSError`; limpar `cookie`; manter `backend`/`path`; no-op sem cookie/backend (ADR-16).
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k release`
  - Critério: testes de T-14 passam (GREEN); nenhuma conexão nova é aberta para liberar.
  - Estimativa: 20min

- [ ] **T-16**: Escrever os testes RED de `confirm()` e `needs_verification`
  - Arquivo: `tests/unit/test_inhibitors.py`
  - Testes:
    - `test_confirm_without_cookie_is_false` — `backend is None`/`cookie is None` ⇒ `False`.
    - `test_confirm_fdo_non_kde_is_true` — FDO adquirido, `PolicyAgent` sem dono ⇒ `True` (cookie).
    - `test_confirm_kde_active_inhibitions` — `PolicyAgent` com dono; `Properties.Get(PA_IFACE, "ActiveInhibitions")` devolve `(4, "deskawake", "DeskAwake active", 0, 3)` ⇒ `True`.
    - `test_confirm_kde_has_inhibition_fallback` — `ActiveInhibitions` levanta `UnknownMethod` e `HasInhibition(4)` devolve `True` ⇒ `True`.
    - `test_confirm_kde_cookie_fallback_with_warning` — `ActiveInhibitions` **e** `HasInhibition` ausentes (`UnknownMethod`/`UnknownInterface`/`UnknownProperty`/`InvalidArgs`) ⇒ `True` e `caplog` com warning.
    - `test_confirm_kde_available_negative_is_false` — `ActiveInhibitions` disponível sem nossa entrada ⇒ `False`; e, com `HasInhibition` ausente, continua `False` (lista autoritativa).
    - `test_confirm_kde_has_inhibition_false_is_false` — `ActiveInhibitions` ausente e `HasInhibition(4) is False` ⇒ `False`.
    - `test_confirm_kde_transport_error_with_owner_is_false` — `Get` levanta `DBusException` de transporte com dono ⇒ `False` (não degrada).
    - `test_confirm_debounce_guard` — `_acquired_at` recente + mecanismos negativos ⇒ `True`; `_acquired_at` mais antigo que `debounce` + negativos ⇒ `False`.
    - `test_needs_verification_only_for_kde_fdo` — `fdo` + `PolicyAgent` dono ⇒ `True`; `fdo` sem `PolicyAgent` ⇒ `False`; `mate`/`gsm` ⇒ `False`.
    - `test_needs_verification_bus_error_is_false` — `name_has_owner` levanta ⇒ `False`.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "confirm or needs_verification"`
  - Critério: falha (RED) porque `confirm()`/`needs_verification` ainda não existem.
  - Estimativa: 40min

- [ ] **T-17**: Implementar `ScreenSaverInhibit.confirm()` e `needs_verification`
  - Arquivo: `core/inhibitors.py`
  - Contrato: ver `design_e2.md` §4.1 e ADR-02/05; MATE repete `GetInhibitors` + `IsInhibited(8)` quando GSM existir; GSM usa `IsInhibited(8)`; FDO sem `PolicyAgent` ⇒ cookie `True`; KDE usa `ActiveInhibitions` (`flags & 3 == 3`) → `HasInhibition(4)` → cookie + warning **somente** quando ambos ausentes; transporte/serviço com dono ⇒ `False`; guard de `debounce` só em FDO; `needs_verification = backend == "fdo" and bus.name_has_owner(PA_NAME)`.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "confirm or needs_verification"`
  - Critério: testes de T-16 passam (GREEN); mensagens de warning em pt-BR.
  - Estimativa: 35min

- [ ] **T-18**: Escrever os testes RED restantes do contrato
  - Arquivo: `tests/unit/test_inhibitors.py`
  - Testes:
    - `test_acquire_records_acquired_at` — `_acquired_at` definido após o sucesso e não antes.
    - `test_acquire_overwrites_previous_backend` — segundo `acquire()` sobrescreve `backend`/`path`/`cookie`.
    - `test_confirm_after_release_is_false` — após `release()`, `confirm() is False` (cookie limpo).
    - `test_acquire_without_owner_does_not_wake_service` — `name_has_owner` falso ⇒ nenhuma chamada `get_object`/método para aquele backend.
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py -v -k "acquire or confirm_after_release"`
  - Critério: testes passam com o código de T-13/T-15/T-17; qualquer falha indica contrato em falta (corrigir antes de seguir).
  - Estimativa: 15min

- [ ] **T-19**: Refatorar `core/inhibitors.py`
  - Arquivo: `core/inhibitors.py`
  - Critério: extrair `_has_owner`, `_proxy`, `_call`, `_confirm_mate`/`_confirm_gsm`/`_confirm_fdo` se necessário; constantes `BACKENDS`, `POLICYAGENT_*`, `GSM_IDLE_FLAG`, `POLICYAGENT_CHANGE_SCREEN_SETTINGS`, `POLICYAGENT_ACTIVE_MASK`; sem `subprocess` em `ScreenSaverInhibit`; rodar `python3 -m pytest tests/unit/test_inhibitors.py -v` com 0 failures e `python3 -m compileall -q core/inhibitors.py`.
  - Estimativa: 10min

### 4. `StateMachine` — `core/state.py` (TDD)

- [ ] **T-20**: Escrever os testes RED de identidade, estados públicos e dependências
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_initial_state_off_and_last_error_empty` — `state == "off"`, `public_state == "off"`, `last_error == ""`, nenhum sinal.
    - `test_public_state_mapping` — `OFF/ON/ERROR` iguais; `ACTIVATING → "off"`; `DEACTIVATING → "on"` (atribuir `_state` diretamente para cobrir os internos).
    - `test_invalid_dependencies_raise_runtime_error` — `StateMachine(lambda s: None)` + `activate()` levanta `RuntimeError` mencionando inibidores; `deactivate()` em `off` não levanta.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "initial or public_state or invalid"`
  - Critério: falha (RED) porque `core.state` ainda não existe.
  - Estimativa: 10min

- [ ] **T-21**: Implementar `State`, construtor e propriedades da `StateMachine`
  - Arquivo: `core/state.py`
  - Contrato: `State(Enum)` com os cinco valores; `StateMachine(on_change, verify_delay=6.0, *, systemd=None, screen=None, schedule=None, cancel=None)`; `public_state`/`state`/`last_error`; `schedule` padrão com `GLib.timeout_add(max(1, int(delay*1000)), callback)` e `cancel` padrão com `GLib.source_remove` (import de `GLib` dentro do método para não exigir GI nos testes); `activate()` sem `systemd`/`screen` ⇒ `RuntimeError`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "initial or public_state or invalid" && python3 -m compileall -q core/state.py`
  - Critério: testes de T-20 passam (GREEN); `activate()` não emite nada antes da implementação do fluxo.
  - Estimativa: 20min

- [ ] **T-22**: Escrever os testes RED da ativação feliz e idempotência
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_activate_emits_only_public_states` — eventos `["on"]`; nunca `activating`.
    - `test_activate_marks_activating_internally` — dentro de `FakeScreen.acquire`, capturar `machine.state == "activating"`.
    - `test_activate_starts_systemd_before_acquiring_screen` — ordem no log dos fakes: `systemd.start` antes de `screen.acquire`.
    - `test_activation_idempotent_when_on` — segundo `activate()` não chama `start`/`acquire` de novo e não emite.
    - `test_activate_returns_public_state` — retorno `"on"`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k activate`
  - Critério: falha (RED) porque `activate()` ainda não orquestra os inibidores.
  - Estimativa: 20min

- [ ] **T-23**: Implementar `activate()` — caminho feliz
  - Arquivo: `core/state.py`
  - Contrato: `ON` ⇒ no-op; `OFF` ⇒ `ACTIVATING` sem emitir; se `not systemd.alive`, `systemd.start()`; `screen.acquire()`; sucesso ⇒ `ON`, limpa `last_error`, `_recovering = False`, cancela timer pendente, agenda verificação se `screen.needs_verification`, emite `"on"`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k activate`
  - Critério: testes de T-22 passam (GREEN).
  - Estimativa: 25min

- [ ] **T-24**: Escrever os testes RED da falha de ativação e do estado `error`
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_activation_failure_cleans_up` — `screen.acquire` levanta; `screen.release()` chamado (best-effort), `systemd.stop()` chamado (filho iniciado nesta chamada), estado `error`, `last_error` com o motivo, evento `"error"`.
    - `test_activation_failure_on_systemd_start_does_not_acquire_screen` — `systemd.start` levanta; `screen.acquire` nunca chamado; `error`.
    - `test_activate_from_error_keeps_live_child` — após falha de ativação com filho vivo, `activate()` bem-sucedido **não** chama `start` nem `stop` de novo.
    - `test_activate_from_error_starts_child_if_dead` — `systemd.alive is False` em `error`; `activate()` chama `start()` uma vez.
    - `test_repeated_failure_updates_reason_without_signal` — segunda falha com motivo diferente atualiza `last_error`, mas não reemite `"error"`.
    - `test_last_error_cleared_on_off_and_on` — de `error`, `deactivate()` ⇒ `last_error == ""`; de `error`, `activate()` bem-sucedido ⇒ `last_error == ""`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "failure or error or last_error"`
  - Critério: falha (RED) no tratamento de falha (o caminho feliz de T-23 não cobre).
  - Estimativa: 25min

- [ ] **T-25**: Implementar a falha de ativação, `error` e `last_error` (ADR-06/08/17)
  - Arquivo: `core/state.py`
  - Contrato: falha em `systemd.start`/`screen.acquire` ⇒ liberar tela (best-effort), parar o filho **somente se iniciado nesta chamada**, gravar `last_error`, ir a `ERROR`, emitir `"error"` só se o estado público anterior não era `error`; `activate()` a partir de `ERROR` limpa cookie antigo, preserva filho vivo, inicia se morto; `last_error` só existe em `ERROR`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "failure or error or last_error"`
  - Critério: testes de T-24 passam (GREEN); nenhum `stop()` em filho pré-existente.
  - Estimativa: 30min

- [ ] **T-26**: Escrever os testes RED de `deactivate()` e `toggle()`
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_deactivate_releases_and_stops_in_order` — `screen.release` antes de `systemd.stop`; estado `off`; evento `"off"`; `last_error == ""`.
    - `test_deactivation_idempotent_when_off` — sem chamadas e sem sinal.
    - `test_error_deactivate_goes_off` — de `error`, libera cookie (se houver), para filho (se houver), vai a `off`, limpa `last_error`.
    - `test_toggle_matrix` — parametrizado: `on → off`; `off → on`; `error → on` (ativar, ADR-06); retorno é o novo estado público; `on_change` só com transições públicas.
    - `test_deactivate_clears_recovering` — `_recovering` volta a `False`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "deactivate or toggle"`
  - Critério: falha (RED) porque `deactivate`/`toggle` ainda não existem.
  - Estimativa: 20min

- [ ] **T-27**: Implementar `deactivate()` e `toggle()`
  - Arquivo: `core/state.py`
  - Contrato: `OFF` ⇒ no-op; `ON`/`ERROR` ⇒ `DEACTIVATING` interno, cancela verificação, `screen.release()`, `systemd.stop()`, `OFF`, limpa `last_error`, `_recovering = False`, emite `"off"`; falhas de release/stop são absorvidas; `toggle()` usa `deactivate` em `ON` e `activate` em `OFF`/`ERROR`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "deactivate or toggle"`
  - Critério: testes de T-26 passam (GREEN).
  - Estimativa: 25min

- [ ] **T-28**: Escrever os testes RED da verificação assíncrona
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_activate_schedules_verification_when_needed` — `needs_verification is True`, `verify_delay=2.5` ⇒ `FakeScheduler` registra `2.5`.
    - `test_activate_does_not_schedule_without_needs_verification` — `needs_verification is False` ⇒ nenhum agendamento.
    - `test_verification_success_keeps_on_without_signal` — `fire()` com `confirm() is True` ⇒ permanece `on`, nenhum evento novo.
    - `test_verification_failure_while_on` — `confirm() is False` ⇒ libera tela, para o filho (all-or-nothing), `error`, `last_error`, evento `"error"`.
    - `test_verification_failure_while_off_is_silent` — guardar o callback, desativar e chamar o callback manualmente ⇒ estado `off`, **nenhum** `StateChanged` novo.
    - `test_cancel_verification_is_idempotent` — `cancel_pending_verification()` duas vezes sem erro; `_verify_source is None`.
    - `test_deactivate_cancels_pending_verification` — `deactivate()` chama `cancel` com o id agendado.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "verification or cancel"`
  - Critério: falha (RED) porque a verificação ainda não é agendada nem tratada.
  - Estimativa: 30min

- [ ] **T-29**: Implementar o agendamento e o callback de verificação (ADR-05/14)
  - Arquivo: `core/state.py`
  - Contrato: agenda `schedule(verify_delay, _on_verify)` quando `screen.needs_verification`; `_on_verify` só age se `state == ON`; `confirm()` verdadeiro ⇒ mantém `on`; falso ⇒ libera tudo, vai a `ERROR`, `last_error`, emite `"error"`; `cancel_pending_verification()` remove e zera o id; callback retorna `GLib.SOURCE_REMOVE`/`False`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "verification or cancel"`
  - Critério: testes de T-28 passam (GREEN); nenhum sinal quando o estado já é `off`.
  - Estimativa: 35min

- [ ] **T-30**: Escrever os testes RED de perda de tela (`handle_screen_lost`)
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_liveness_loss_preserves_child` — de `on`: `screen.release()` chamado, `systemd.stop()` **não** chamado, `error`, evento `"error"`, `last_error` com o motivo, `_recovering is True`.
    - `test_liveness_loss_ignored_when_not_on` — em `off`/`error` não age nem emite.
    - `test_liveness_loss_cancels_pending_verification` — `cancel` chamado.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "liveness_loss"`
  - Critério: falha (RED) porque `handle_screen_lost` ainda não existe.
  - Estimativa: 15min

- [ ] **T-31**: Implementar `handle_screen_lost()`
  - Arquivo: `core/state.py`
  - Contrato: só age em `ON`; cancela verificação; `screen.release()` best-effort; **não** para o filho; `ERROR`; `last_error = reason`; `_recovering = True`; emite `"error"`.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k liveness_loss`
  - Critério: testes de T-30 passam (GREEN).
  - Estimativa: 20min

- [ ] **T-32**: Escrever os testes RED do retorno de tela (`handle_screen_returned`)
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_liveness_return_single_attempt` — após perda com filho vivo: `screen.release()` do cookie antigo + `screen.acquire()` uma vez; volta a `on`; emite `"error"` → `"on"`; `_recovering is False`.
    - `test_liveness_return_starts_child_if_dead` — filho morreu durante o `error`; retorno chama `start()` antes de `acquire()`.
    - `test_liveness_return_failure_no_signal` — `acquire` falha; permanece `error`; **não** reemite `"error"`; `last_error` atualizado; para o filho apenas se iniciado nesta tentativa.
    - `test_liveness_return_ignored_when_not_recovering` — `error` de ativação (`_recovering is False`) ⇒ sem efeitos.
    - `test_explicit_activate_clears_recovering` — `activate()` explícito após perda zera `_recovering` e não deixa recuperação automática pendente.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "liveness_return or recovering"`
  - Critério: falha (RED) porque `handle_screen_returned` ainda não existe.
  - Estimativa: 20min

- [ ] **T-33**: Implementar `handle_screen_returned()`
  - Arquivo: `core/state.py`
  - Contrato: só age em `ERROR` **e** `_recovering`; uma tentativa por chamada: `screen.release()` (cookie antigo), `start()` se o filho morreu, `screen.acquire()`; sucesso ⇒ `ON`, limpa `last_error`, `_recovering = False`, agenda verificação se necessário, emite `"on"`; falha ⇒ permanece `ERROR`, atualiza motivo, sem sinal.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "liveness_return or recovering"`
  - Critério: testes de T-32 passam (GREEN); nenhum loop de retry.
  - Estimativa: 25min

- [ ] **T-34**: Escrever os testes RED de `handle_session_end()`
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_session_end_stops_child_without_dbus` — de `on`: `systemd.stop()` chamado, `screen.release()` **não** chamado (nenhuma D-Bus), vai a `off`, limpa `last_error`, `_recovering = False`, **nenhum** evento.
    - `test_session_end_from_error_is_safe` — de `error`, idem, sem sinal.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k session_end`
  - Critério: falha (RED) porque `handle_session_end` ainda não existe.
  - Estimativa: 10min

- [ ] **T-35**: Implementar `handle_session_end()`
  - Arquivo: `core/state.py`
  - Contrato: cancela verificação; `systemd.stop()`; nenhuma chamada `screen.release()`; `OFF`; limpa `last_error`; `_recovering = False`; não emite.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k session_end`
  - Critério: testes de T-34 passam (GREEN).
  - Estimativa: 15min

- [ ] **T-36**: Escrever os testes RED de consistência dos sinais
  - Arquivo: `tests/unit/test_state.py`
  - Testes:
    - `test_on_change_called_after_state_is_consistent` — no callback, `machine.state` já reflete o novo estado.
    - `test_activate_while_activating_returns_public_off` / `test_deactivate_while_deactivating_returns_public_on` — forçar `_state` interno e chamar o método; sem efeitos e retorno `public_state` (defensividade do design §4.2).
    - `test_no_signal_on_noop_transitions` — `activate()` em `on`, `deactivate()` em `off`, `toggle()` em estados internos não emitem.
  - Comando: `python3 -m pytest tests/unit/test_state.py -v -k "consistent or internal or noop"`
  - Critério: falha (RED) se a implementação emitir antes de consistir ou tratar os internos de forma diferente; se já estiver verde, registrar como regressão e seguir.
  - Estimativa: 10min

- [ ] **T-37**: Refatorar `core/state.py`
  - Arquivo: `core/state.py`
  - Critério: extrair helpers privados se necessário (`_emit`, `_schedule_verification`, `_enter_error`, `_acquire_screen`); sem `dbus`, `subprocess` ou `Gtk`; `GLib` só no agendador padrão; rodar `python3 -m pytest tests/unit/test_state.py -v` e `python3 -m compileall -q core/state.py` com exit 0.
  - Estimativa: 10min

### 5. Integração — fakes e harness

- [ ] **T-38**: Criar `fake_screensaver.py` com o backend FDO e o log JSONL
  - Arquivo: `tests/integration/fakes/fake_screensaver.py`
  - Conteúdo: `argparse` (`--fdo`, `--mate`, `--gsm`, `--kde`, `--log`); `DBusGMainLoop(set_as_default=True)`; `dbus.SessionBus()`; `set_exit_on_disconnect(False)`; objeto FDO em `/org/freedesktop/ScreenSaver` com `Inhibit(s,s)→u` e `UnInhibit(u)`; cada chamada grava uma linha JSONL (`backend`, `method`, `args`, `cookie`); registra `{"event": "bus_disconnected"}` ao receber `Local.Disconnected` (usado no teste de T-53); pid do processo é o do fake.
  - Comando:
    ```bash
    dbus-run-session -- bash -c 'python3 tests/integration/fakes/fake_screensaver.py --fdo --log /tmp/fake-fdo.jsonl & pid=$!; n=0; until gdbus introspect --session --dest org.freedesktop.ScreenSaver --object-path /org/freedesktop/ScreenSaver >/dev/null 2>&1; do sleep 0.05; n=$((n+1)); [ "$n" -gt 100 ] && exit 1; done; gdbus call --session --dest org.freedesktop.ScreenSaver --object-path /org/freedesktop/ScreenSaver --method org.freedesktop.ScreenSaver.Inhibit deskawake "DeskAwake active"; kill $pid; grep -q "\"method\": \"Inhibit\"" /tmp/fake-fdo.jsonl; rm -f /tmp/fake-fdo.jsonl'
    ```
  - Critério: `gdbus call` devolve um `uint32`; JSONL contém `Inhibit`; o processo encerra sem deixar filho. `python3 -m compileall -q tests/integration/fakes/fake_screensaver.py` exit 0.
  - Estimativa: 35min

- [ ] **T-39**: Adicionar MATE e GSM ao `fake_screensaver.py`
  - Arquivo: `tests/integration/fakes/fake_screensaver.py`
  - Conteúdo:
    - MATE em `/org/mate/ScreenSaver`: `Inhibit(s,s)→u`, `UnInhibit(u)`, `GetInhibitors()→as` devolvendo strings com `Application=deskawake; Reason=DeskAwake active;` por cookie ativo.
    - GSM em `/org/gnome/SessionManager`: `Inhibit(s,u,s,u)→u`, `Uninhibit(u)`, `IsInhibited(u)→b`; `flags=8` e `xid=0` registrados.
    - Quando MATE está ativo e o GSM também está no barramento, o `Inhibit` do MATE cria uma inibição GSM `IDLE=8` (proxy), refletida em `IsInhibited(8)` e removida pelo `UnInhibit`/`Uninhibit`.
    - Log JSONL de todas as chamadas, incluindo o proxy.
  - Comando:
    ```bash
    dbus-run-session -- bash -c 'python3 tests/integration/fakes/fake_screensaver.py --mate --gsm --log /tmp/fake-mate.jsonl & pid=$!; until gdbus introspect --session --dest org.mate.ScreenSaver --object-path /org/mate/ScreenSaver >/dev/null 2>&1; do sleep 0.05; done; gdbus call --session --dest org.mate.ScreenSaver --object-path /org/mate/ScreenSaver --method org.mate.ScreenSaver.Inhibit deskawake "DeskAwake active"; gdbus call --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager --method org.gnome.SessionManager.IsInhibited 8; kill $pid; grep -q "\"backend\": \"mate\"" /tmp/fake-mate.jsonl; rm -f /tmp/fake-mate.jsonl'
    ```
  - Critério: `IsInhibited(8)` devolve `true` após o `Inhibit` do MATE; JSONL tem `mate` e `gsm`; nenhum processo órfão.
  - Estimativa: 35min

- [ ] **T-40**: Criar `fake_policyagent.py`
  - Arquivo: `tests/integration/fakes/fake_policyagent.py`
  - Conteúdo: `argparse` (`--log`, `--debounce-ms` padrão 5000, `--fail`, `--no-active-inhibitions`, `--no-has-inhibition`); objeto em `/org/kde/Solid/PowerManagement/PolicyAgent`; `AddInhibition(u,s,s)` e `ReleaseInhibition(u)` para o fake FDO; `HasInhibition(u)→b`; propriedade `ActiveInhibitions` (`a(ssssu)`) exposta via `org.freedesktop.DBus.Properties.Get` com `out_signature="v"` e valor `dbus.Array([(4, who, why, 0, 3)], signature="(ssssu)")` após `--debounce-ms`; `--fail` mantém os mecanismos **disponíveis e negativos** (nunca confirmam) — rota (ii), não degradação para cookie; flags desligam cada mecanismo para simular PowerDevil antigo; JSONL por chamada; `set_exit_on_disconnect(False)` e marcador `bus_disconnected`.
  - Comando: `dbus-run-session -- bash -c 'python3 tests/integration/fakes/fake_policyagent.py --debounce-ms 50 --log /tmp/pa.jsonl & pa=$!; until gdbus introspect --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent >/dev/null 2>&1; do sleep 0.02; done; gdbus call --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent --method org.kde.Solid.PowerManagement.PolicyAgent.AddInhibition 4 deskawake "DeskAwake active"; gdbus call --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent --method org.kde.Solid.PowerManagement.PolicyAgent.HasInhibition 4; gdbus call --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent --method org.freedesktop.DBus.Properties.Get org.kde.Solid.PowerManagement.PolicyAgent ActiveInhibitions; kill $pa; grep -q AddInhibition /tmp/pa.jsonl; rm -f /tmp/pa.jsonl'`
  - Critério: `HasInhibition(4)` devolve `false` antes do debounce e `true` depois; `Get` devolve array com a entrada; JSONL registra as chamadas; `--fail` mantém `false`.
  - Estimativa: 30min

- [ ] **T-41**: Adicionar o modo KDE ao `fake_screensaver.py`
  - Arquivo: `tests/integration/fakes/fake_screensaver.py`
  - Conteúdo: com `--kde`, o `Inhibit` do FDO chama `org.kde.Solid.PowerManagement.PolicyAgent.AddInhibition(UInt32(4), who, why)` e guarda o cookie; `UnInhibit` chama `ReleaseInhibition(UInt32(4))`; o fake **não** chama o PolicyAgent quando `--kde` não foi passado; o log JSONL registra `AddInhibition`/`ReleaseInhibition` com o backend `policyagent`.
  - Comando: `dbus-run-session -- bash -c 'python3 tests/integration/fakes/fake_policyagent.py --log /tmp/pa.jsonl & pa=$!; python3 tests/integration/fakes/fake_screensaver.py --fdo --kde --log /tmp/fs.jsonl & fs=$!; until gdbus introspect --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent >/dev/null 2>&1; do sleep 0.05; done; gdbus call --session --dest org.freedesktop.ScreenSaver --object-path /org/freedesktop/ScreenSaver --method org.freedesktop.ScreenSaver.Inhibit deskawake "DeskAwake active"; kill $fs $pa; grep -q AddInhibition /tmp/pa.jsonl; rm -f /tmp/fs.jsonl /tmp/pa.jsonl'`
  - Critério: `AddInhibition` aparece no JSONL do PolicyAgent uma vez; `--kde` ausente não gera chamada ao PolicyAgent.
  - Estimativa: 20min

- [ ] **T-42**: Criar o harness de integração em `tests/conftest.py`
  - Arquivo: `tests/conftest.py`
  - Conteúdo (fixtures/funções auxiliares):
    - `wait_until(predicate, timeout=5.0)` sem `sleep` fixo (poll curto).
    - `session_bus()` — conexão de controle própria (`BusConnection` quando necessário) com `set_exit_on_disconnect(False)`.
    - `start_fake_screensaver(*flags, log_path=...)` e `start_fake_policyagent(*flags, log_path=...)` — sobem subprocessos com `DBUS_SESSION_BUS_ADDRESS` herdado, esperam os nomes, devolvem handle com `pid`, `log_path`, `terminate()`.
    - `start_daemon(**overrides, env_extra=None)` — `python3 -c "import core.daemon as d; raise SystemExit(d.main(verify_delay=..., debounce=..., confirm_delay=..., log_path=...))"` com `cwd` na raiz do repo, `HOME` temporário e `DBUS_SESSION_BUS_ADDRESS`/`PATH` mesclados de `env_extra`; espera `org.local.DeskAwake`; expõe `proc`, `pid`, `state()`, `last_error()`, `set_active(bool)`, `toggle()`, `quit()`, `signals`, `wait_exit(timeout)`.
    - `child_pids(pid)` via `ps --ppid`; `inhibit_pids()` parseando `systemd-inhibit --list --no-pager`; `read_jsonl(path)`.
    - `cleanup` em `finally`/teardown: terminar, esperar e matar fakes, daemon e filhos; nenhum processo vaza.
  - Comando: `python3 -m compileall -q tests/conftest.py && python3 -m pytest tests/unit -q`
  - Critério: compileall exit 0; unit da E1 verde; o harness será exercitado em T-43.
  - Estimativa: 40min

### 6. `core/daemon.py` — contrato D-Bus, liveness e ciclo de vida

- [ ] **T-43**: Escrever os testes RED do contrato básico e do log
  - Arquivo: `tests/integration/test_daemon_contract.py`
  - Testes:
    - `test_daemon_starts_off_and_registers_name` — daemon sobe, `NameHasOwner("org.local.DeskAwake") is True`; `GetState() == "off"`; `GetLastError() == ""`.
    - `test_daemon_writes_log_at_configured_path` — `log_path` temporário existe e contém a linha de início com PID.
    - `test_log_rotation_creates_backup` — pré-preencher `daemon.log` com > 256 KB; iniciar; `daemon.log.1` existe e `daemon.log` recomeçou.
    - `test_daemon_survives_unwritable_log_path` — `log_path` apontando para um diretório; o daemon continua, registra em stderr e `GetState` responde.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "starts_off or log"`
  - Critério: falha (RED) porque `core.daemon` ainda não existe.
  - Estimativa: 25min

- [ ] **T-44**: Implementar o esqueleto de `core/daemon.py` com logging, barramento, objeto e nome
  - Arquivo: `core/daemon.py`
  - Contrato: constantes `DBUS_NAME`, `OBJECT_PATH`, `INTERFACE`, `LOG_PATH`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`, `VERIFY_DELAY`, `DEBOUNCE`, `CONFIRM_DELAY`, `WATCHED_NAMES`; `main(*, verify_delay, debounce, confirm_delay, log_path)` na sequência 1–9 do design §4.3; `RotatingFileHandler(maxBytes=262144, backupCount=1)` com fallback para `basicConfig()` em `OSError`; `DBusGMainLoop`; `SessionBus`; `set_exit_on_disconnect(False)`; criar `SystemdInhibit`, `ScreenSaverInhibit`, `_Service`, `StateMachine`; exportar o objeto **antes** de `request_name(..., DO_NOT_QUEUE)`; aceitar `PRIMARY_OWNER`/`ALREADY_OWNER`, senão logar e retornar 0; registrar `NameOwnerChanged`, `Local.Disconnected`, SIGTERM/SIGINT; `loop.run()`; `finally` com `machine.deactivate()`/`handle_session_end()`.
  - Stubs explícitos nesta task: `_Service.SetActive`/`Toggle` ainda não implementados (podem levantar `NotImplementedError`); `GetState`/`GetLastError` funcionam.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "starts_off or log" && python3 -m compileall -q core/daemon.py`
  - Critério: testes de T-43 passam (GREEN); log rotaciona; `NameHasOwner` só é verdadeiro com o objeto exportado.
  - Estimativa: 50min

- [ ] **T-45**: Escrever os testes RED de `SetActive` e do lock do logind
  - Arquivo: `tests/integration/test_daemon_contract.py`
  - Testes:
    - `test_set_active_true_reports_on_and_creates_lock` — `SetActive(true)` devolve `"on"`; `GetState() == "on"`; `child_pids(daemon.pid)` tem um PID; `inhibit_pids()` contém esse PID.
    - `test_set_active_false_reports_off_and_removes_lock` — depois de `true`, `SetActive(false)` devolve `"off"`; `GetState() == "off"`; o PID sumiu de `inhibit_pids()` e do `ps --ppid`.
    - `test_set_active_true_is_idempotent` — segundo `true` não cria segundo filho (mesmo PID).
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "set_active"`
  - Critério: falha (RED) porque `SetActive` é stub.
  - Estimativa: 25min

- [ ] **T-46**: Implementar `_Service.SetActive` e o ciclo do filho
  - Arquivo: `core/daemon.py`
  - Contrato: `SetActive(b)` loga, delega a `machine.activate()`/`deactivate()` e retorna o estado resultante; sem erro D-Bus para falha operacional; o filho do `systemd-inhibit` sobe apenas no ON e morre no OFF.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "set_active"`
  - Critério: testes de T-45 passam (GREEN); `inhibit_pids()` reflete o filho do daemon de teste, não um DeskAwake real.
  - Estimativa: 20min

- [ ] **T-47**: Escrever os testes RED de `Toggle` e `StateChanged`
  - Arquivo: `tests/integration/test_daemon_contract.py`
  - Testes:
    - `test_toggle_matches_set_active_inverse` — `Toggle()` em `off` ⇒ `"on"`; de novo ⇒ `"off"`; mesmo retorno de `SetActive(not current)`.
    - `test_state_changed_only_public_states` — assinar `StateChanged`; `true` e `false`; sequência exatamente `["on", "off"]`, nunca `activating`/`deactivating`.
    - `test_get_last_error_empty_when_healthy` — após operação normal, `""`.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "toggle or state_changed"`
  - Critério: falha (RED) porque `Toggle` é stub e o sinal ainda não é emitido.
  - Estimativa: 20min

- [ ] **T-48**: Implementar `Toggle`, `GetLastError` e a emissão de `StateChanged`
  - Arquivo: `core/daemon.py`
  - Contrato: `Toggle()` delega a `machine.toggle()`; `_on_state_changed` emite o sinal `StateChanged(s)` e absorve/loga exceções de conexão morta; limpa `_lost` quando o estado vira `on`/`off`; `GetState`/`GetLastError` usam `public_state`/`last_error`.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "toggle or state_changed or last_error"`
  - Critério: testes de T-47 passam (GREEN); nenhum sinal para estados internos.
  - Estimativa: 20min

- [ ] **T-49**: Escrever os testes RED de segunda instância e prontidão do nome
  - Arquivo: `tests/integration/test_daemon_contract.py`
  - Testes:
    - `test_second_instance_exits_zero` — com o primeiro daemon dono do nome, um **segundo processo** rodando `main()` no mesmo `HOME`/barramento sai **0**, não assume o nome e não interfere no primeiro (`GetState` continua respondendo).
    - `test_name_visible_implies_object_ready` — assim que `NameHasOwner` fica verdadeiro, `GetState()` responde sem `UnknownMethod` (exportar antes de `request_name`).
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "second_instance or name_visible"`
  - Critério: falha (RED) se a ordem exportar/pedir nome ou o tratamento de `DO_NOT_QUEUE` estiver errado.
  - Estimativa: 15min

- [ ] **T-50**: Corrigir a aquisição do nome e a segunda instância (ADR-09)
  - Arquivo: `core/daemon.py`
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_daemon_contract.py -v -k "second_instance or name_visible"`
  - Critério: testes de T-49 passam (GREEN); segunda instância apenas loga “instância já ativa” e retorna 0; a primeira mantém o nome.
  - Estimativa: 15min

- [ ] **T-51**: Escrever os testes RED de `SIGTERM`, `SIGINT` e `Quit`
  - Arquivo: `tests/integration/test_lifecycle.py`
  - Testes:
    - `test_sigterm_releases_and_exits_zero` — `SetActive(true)`, enviar `SIGTERM`; exit 0; `inhibit_pids()` sem o filho; log registra o motivo.
    - `test_sigint_releases_and_exits_zero` — idem com `SIGINT`.
    - `test_quit_releases_and_name_disappears` — `SetActive(true)`, `Quit()`; exit 0; nome some do barramento; lock ausente; filho morto.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_lifecycle.py -v -k "sigterm or sigint or quit"`
  - Critério: falha (RED) porque os handlers e `Quit` ainda não existem.
  - Estimativa: 25min

- [ ] **T-52**: Implementar os handlers de sinal e `Quit`
  - Arquivo: `core/daemon.py`
  - Contrato: `GLibUnix.signal_add` (fallback `GLib.unix_signal_add`) com handler `try/finally` que chama `machine.deactivate()` e `loop.quit()`, retorna `GLib.SOURCE_REMOVE`; `Quit()` desativa e `GLib.idle_add(loop.quit)`; reply sai antes do encerramento; exit 0.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_lifecycle.py -v -k "sigterm or sigint or quit"`
  - Critério: testes de T-51 passam (GREEN); nenhum órfão; saída 0.
  - Estimativa: 30min

- [ ] **T-53**: Escrever o teste RED de `Local.Disconnected`
  - Arquivo: `tests/integration/test_lifecycle.py`
  - Teste: `test_local_disconnected_exits_zero_without_uninhibit` — subir um `dbus-daemon --session --nofork --print-address` dedicado, fakes e daemon com `DBUS_SESSION_BUS_ADDRESS` próprio; `SetActive(true)`; matar o barramento com SIGTERM; esperar o daemon sair **0**; o JSONL dos fakes não pode conter `UnInhibit`/`Uninhibit` depois do marcador `bus_disconnected`; o filho do `systemd-inhibit` morre (sem órfão).
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_lifecycle.py -v -k local_disconnected`
  - Critério: falha (RED) porque `set_exit_on_disconnect(False)`/handler ainda não estão implementados; o teste também usa conexão de controle própria para não morrer junto.
  - Estimativa: 35min

- [ ] **T-54**: Implementar `set_exit_on_disconnect(False)` e o handler de `Local.Disconnected`
  - Arquivo: `core/daemon.py`
  - Contrato: `bus.set_exit_on_disconnect(False)` logo após conectar; `add_signal_receiver` em `dbus.LOCAL_IFACE`/`dbus.LOCAL_PATH` com handler `*args`; no caminho, `machine.handle_session_end()`, marcar `_bus_dead = True`, `loop.quit()`, exit 0; o `finally` consulta `_bus_dead` para não chamar D-Bus.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_lifecycle.py -v -k local_disconnected`
  - Critério: teste de T-53 passa (GREEN); zero chamadas de liberação após o fechamento; exit 0.
  - Estimativa: 35min

- [ ] **T-55**: Escrever o teste RED de `PDEATHSIG`
  - Arquivo: `tests/integration/test_lifecycle.py`
  - Teste: `test_pdeathsig_no_orphan` — `SetActive(true)`, obter o PID do filho do `systemd-inhibit`; `SIGKILL` no daemon; `wait_until` o filho não existir (≤ 2 s); nenhum `sleep infinity` órfão.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_lifecycle.py -v -k pdeathsig`
  - Critério: falha (RED) se `_pdeathsig` não estiver sendo aplicado; se passar de primeira, registrar como verificação do contrato e seguir.
  - Estimativa: 15min

- [ ] **T-56**: Verificar/corrigir o `PDEATHSIG` (ADR-11)
  - Arquivo: `core/inhibitors.py` (somente se o teste falhar)
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_lifecycle.py -v -k pdeathsig`
  - Critério: `test_pdeathsig_no_orphan` verde; `Popen` recebe `preexec_fn` e `start_new_session=True`; nenhuma alteração de arquitetura (não mover o spawn para thread).
  - Estimativa: 15min

- [ ] **T-57**: Escrever os testes RED do KDE otimista, falha forçada e `GetLastError`
  - Arquivo: `tests/integration/test_kde_optimistic.py`
  - Testes:
    - `test_on_is_optimistic_before_confirmation` — `fake_policyagent --debounce-ms 3000`; daemon `verify_delay=0.5`, `debounce=0.1`; `SetActive(true)` devolve `"on"` e `GetState()` já é `"on"` antes da confirmação.
    - `test_confirmation_within_window_stays_on` — fake com debounce curto (ex.: 50 ms), `verify_delay=0.5`; após `wait_until` a janela passar, `GetState() == "on"`; nenhum `StateChanged("error")`.
    - `test_confirmation_failure_goes_error` — fake `--fail`, `verify_delay=0.3`, `debounce=0.05`; esperar `StateChanged("error")`; `GetState() == "error"`; `GetLastError() != ""`; lock ausente (all-or-nothing).
    - `test_set_active_false_during_window_cancels` — fake com debounce longo; `true` e imediatamente `false`; esperar > `verify_delay`; estado `off`; nenhum `"error"` na sequência de sinais.
    - `test_get_last_error_after_forced_failure` — `env_extra["PATH"]` com um `systemd-inhibit` falso (gerado em `tmp_path`, executável, imprime `"falha forçada do logind"` no stderr e sai 1); `SetActive(true)` ⇒ `"error"`; `GetLastError()` contém `"falha forçada do logind"`.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_kde_optimistic.py -v -k "optimistic or confirmation or window or forced"`
  - Critério: falha (RED) porque o daemon ainda não passa `verify_delay`/`debounce` corretamente ou não trata a falha forçada.
  - Estimativa: 40min

- [ ] **T-58**: Ajustar a fiação do KDE otimista e da falha forçada
  - Arquivo: `core/daemon.py` / `core/state.py` (somente o necessário)
  - Contrato: `main()` repassa `verify_delay`/`debounce`/`confirm_delay`; a `StateMachine` agenda a verificação; `SetActive(false)` cancela o timer; falha de ativação libera tudo e preenche `last_error`; `_on_state_changed` limpa `_lost` ao entrar em `on`/`off`.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_kde_optimistic.py -v -k "optimistic or confirmation or window or forced"`
  - Critério: testes de T-57 passam (GREEN); nenhuma espera bloqueante no `SetActive`.
  - Estimativa: 30min

- [ ] **T-59**: Escrever os testes RED de queda/retorno do PowerDevil, preservação do filho e queda do GSM
  - Arquivo: `tests/integration/test_kde_optimistic.py`
  - Testes:
    - `test_powerdevil_drop_and_return` — fake FDO+KDE + `fake_policyagent`; `SetActive(true)`; aguardar confirmação (`on` estável); matar o `fake_policyagent`; esperar `StateChanged("error")` e `GetState() == "error"`; capturar o PID do filho; reiniciar o `fake_policyagent`; esperar `StateChanged("on")`; **o mesmo PID** do filho continua vivo; o JSONL do `fake_screensaver` mostra **um** novo `Inhibit` (uma tentativa por esvaziamento, sem rajada).
    - `test_gsm_drop_with_gsm_backend_exits_zero` — fake só `--gsm` (barramento privado, sem marker `slow`); `SetActive(true)`; matar o fake (queda do GSM); esperar o daemon sair **0**; o filho do `systemd-inhibit` morre; nenhuma tentativa de `Uninhibit` (o serviço está morto).
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_kde_optimistic.py -v -k "powerdevil or gsm_drop"`
  - Critério: falha (RED) porque `NameOwnerChanged`/`_lost` ainda não estão ligados.
  - Estimativa: 40min

- [ ] **T-60**: Implementar a liveness restrita ao backend ativo (ADR-03/04)
  - Arquivo: `core/daemon.py`
  - Contrato: receiver por `WATCHED_NAMES`; `_lost: set[str]`; relevância por backend (`fdo` ⇒ FDO + PolicyAgent; `mate` ⇒ MATE + GSM; `gsm` ⇒ GSM; `None` ⇒ nada); queda relevante ⇒ `handle_screen_lost`; retorno ⇒ remove de `_lost` e chama `handle_screen_returned()` **somente** quando `_lost` esvazia; queda do GSM com backend `gsm` e estado público `on` ⇒ `handle_session_end()`, `loop.quit()`, exit 0 sem `Uninhibit` (ADR-04); filho nunca reiniciado por liveness.
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_kde_optimistic.py -v -k "powerdevil or gsm_drop"`
  - Critério: testes de T-59 passam (GREEN); nenhuma tentativa duplicada; o mesmo PID sobrevive.
  - Estimativa: 40min

- [ ] **T-61**: Escrever os testes RED da cadeia de backends com o daemon
  - Arquivo: `tests/integration/test_backend_chain.py`
  - Testes:
    - `test_chain_uses_fdo_when_available` — fake `--fdo`; `SetActive(true)` ⇒ `GetState() == "on"`; JSONL tem `Inhibit` FDO; nenhum `mate`/`gsm`.
    - `test_chain_uses_mate_when_fdo_absent` — fake `--mate --gsm`; JSONL tem `mate` e o proxy GSM; nenhum `fdo`.
    - `test_chain_uses_gsm_when_both_absent` — fake `--gsm`; JSONL tem `Inhibit` GSM com `flags=8` e `xid=0`; estado `on`.
    - `test_kde_forwards_to_policyagent_once` — fake `--fdo --kde` + policyagent; JSONL do policyagent tem **um** `AddInhibition` (feito pelo fake FDO, não pelo daemon).
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_backend_chain.py -v`
  - Critério: falha (RED) se o daemon/`ScreenSaverInhibit` escolher ou confirmar backend errado no barramento real.
  - Estimativa: 25min

- [ ] **T-62**: Ajustar a cadeia de backends no daemon
  - Arquivo: `core/daemon.py` / `core/inhibitors.py` (somente o necessário)
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration/test_backend_chain.py -v`
  - Critério: testes de T-61 passam (GREEN); ordem FDO → MATE → GSM; o daemon nunca chama `PolicyAgent.AddInhibition`/`ReleaseInhibition`.
  - Estimativa: 20min

- [ ] **T-63**: Refatorar `core/daemon.py`
  - Arquivo: `core/daemon.py`
  - Critério: extrair helpers privados (`_setup_logging`, `_on_name_owner_changed`, `_relevant_names`, `_on_state_changed`, `_shutdown`) se necessário; sem decisão de backend/transição no daemon; rodar `dbus-run-session -- python3 -m pytest tests/integration -v` e `python3 -m compileall -q core tests` com exit 0.
  - Estimativa: 15min

### 7. Validação final e entrega

- [ ] **T-64**: Rodar a suíte unitária do gate
  - Comando: `python3 -m pytest tests/unit/test_inhibitors.py tests/unit/test_state.py -v`
  - Critério: 0 failures, 0 errors, 0 skipped.
  - Estimativa: 5min

- [ ] **T-65**: Rodar a suíte de integração do gate
  - Comando: `dbus-run-session -- python3 -m pytest tests/integration -v`
  - Critério: 0 failures, 0 errors; o único `skip` permitido é o teste `slow` opt-in fora de KDE/PolicyAgent; nenhum teste vaza daemon, fake ou filho do `systemd-inhibit`; `ps --ppid` e `systemd-inhibit --list` não mostram sobras após a suíte.
  - Estimativa: 10min

- [ ] **T-66**: Criar e rodar o teste `slow` opt-in + validação manual no Kubuntu
  - Arquivo: `tests/integration/test_kde_optimistic.py` (teste adicional com `@pytest.mark.slow`)
  - Teste: `test_real_cycle_opt_in` — `pytest.skip` quando `detect_environment()` não for KDE com `PolicyAgent`; sobe o daemon **sem fakes** (barramento real, `HOME` temporário), `SetActive(true)`, aguarda ~6 s e confere `GetState() == "on"`; `SetActive(false)` ⇒ `"off"`; encerra o daemon.
  - Comandos:
    - `python3 -m pytest tests/integration -m slow -v`
    - `systemd-inhibit --what=idle --mode=block --who=DeskAwake --why=probe sleep 3` e, durante os 3 s, `systemd-inhibit --list | grep -i deskawake`
  - Critério: ciclo real de ~5–6 s fecha em `on` e depois `off` no Kubuntu; a linha aparece apenas durante os 3 s. Se a máquina Kubuntu não estiver disponível, registrar a pendência no corpo do PR (não bloqueia o gate automatizado).
  - Estimativa: 30min

- [ ] **T-67**: Auditar escopo, higiene e decisões
  - Comandos:
    - `grep -RInE "AC-[0-9]|T-[0-9]|design_e|tasks|spec\.md|DELIVERY_MAP" core tests` ⇒ sem saída
    - `grep -RInE "xdg-screensaver|CanSuspend|--what=sleep|shell=True" core/` ⇒ sem saída
    - `grep -RIn "AddInhibition\|ReleaseInhibition" core/` ⇒ sem saída (o `PolicyAgent` é somente leitura no produto)
    - `python3 -m compileall -q core tests` ⇒ exit 0
    - `find tests -name conftest.py` ⇒ só `tests/conftest.py`
    - `git status --short` ⇒ só arquivos da entrega + pré-existentes (`README.md`, `spec.md`, `DELIVERY_MAP.md`, `design_e2.md`, `tasks_e2.md`); nenhum `.tmp`, `.log`, JSONL ou fake gerado
    - `python3 -m pytest tests/unit -q` ⇒ verde (E1 + E2)
  - Critério: todos os comandos conforme acima; nenhuma dependência de runtime nova; nenhuma decisão da `spec.md` contrariada.
  - Estimativa: 15min

- [ ] **T-68**: Preparar commit e PR somente com a entrega
  - Comandos:
    - `git add core/inhibitors.py core/state.py core/daemon.py tests/conftest.py tests/unit/test_inhibitors.py tests/unit/test_state.py tests/integration/test_daemon_contract.py tests/integration/test_backend_chain.py tests/integration/test_kde_optimistic.py tests/integration/test_lifecycle.py tests/integration/fakes/fake_screensaver.py tests/integration/fakes/fake_policyagent.py`
    - `git diff --cached --name-only` ⇒ exatamente os arquivos acima
    - `python3 -m pytest tests/unit/test_inhibitors.py tests/unit/test_state.py -v` ⇒ gate unitário verde
    - `dbus-run-session -- python3 -m pytest tests/integration -v` ⇒ gate de integração verde
    - `git commit -m "feat(e2): inibidores, máquina de estados e daemon"`
    - `git push -u origin feat/e2-inibidores-estado-daemon`
    - `gh pr create --base feat/e1-esqueleto-ambiente-config --head feat/e2-inibidores-estado-daemon --title "feat(e2): inibidores, máquina de estados e daemon" --body "<corpo no template do DELIVERY_MAP §0.2>"`
    - `gh pr view --json baseRefName,headRefName,files --jq '{base: .baseRefName, head: .headRefName, files: [.files[].path]}'` ⇒ base `feat/e1-esqueleto-ambiente-config`, head `feat/e2-inibidores-estado-daemon` e apenas os 12 arquivos da entrega
  - Corpo do PR: gate com comando/resultado, checklist manual, fora de escopo e riscos residuais; **não** citar `spec.md`, `design_e2.md`, `tasks_e2.md` nem IDs `AC-*`/`T-*`.
  - Critério: PR contém apenas os 12 arquivos; base é a branch da E1 (empilhamento), não `main`; `docs/implementation/` e `README.md` fora do stage/PR de código.
  - Estimativa: 20min

## Mapeamento AC → Tasks

Os critérios vêm do `DELIVERY_MAP.md` §E2.4 (unitários, integração e opt-in) e do gate G-E2 do `design_e2.md` §8.5.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-U01 — comando do `SystemdInhibit` com `--what=idle`, `--mode=block`, `--who=DeskAwake`; sem `sleep` em `--what` | T-07, T-08, T-67 |
| AC-U02 — filho morre antes de 200 ms ⇒ `start()` levanta erro com `stderr` | T-07, T-08 |
| AC-U03 — `stop()` SIGTERM no grupo → 2 s → SIGKILL no grupo | T-09, T-10 |
| AC-U04 — cadeia FDO → MATE → GSM; GSM com `xid=0` e `flags=8` | T-12, T-13, T-61 |
| AC-U05 — MATE confirmado ⇒ nenhum `Inhibit` no GSM | T-12, T-13 |
| AC-U06 — MATE sem `IsInhibited(8)` ⇒ `UnInhibit` MATE + GSM | T-12, T-13 |
| AC-U07 — `release()` usa `UnInhibit` (FDO/MATE) e `Uninhibit` (GSM) | T-14, T-15 |
| AC-U08 — KDE: `ActiveInhibitions` ⇒ `True`; `HasInhibition(4)` ⇒ `True`; ambos ausentes ⇒ `True` + aviso; disponível e negativo ⇒ `False` | T-16, T-17 |
| AC-U09 — máquina: `off → activating → on`; falha ⇒ `error` + `last_error`; `error + deactivate` ⇒ `off`; `toggle` respeita `on`/`off`/`error` | T-20, T-22, T-23, T-24, T-25, T-26, T-27 |
| AC-U10 — verificação falha com `on` ⇒ `error`; com `off` ⇒ nenhum `StateChanged` | T-28, T-29 |
| AC-I01 — `SetActive(true)` ⇒ `on`; `systemd-inhibit --list` contém o filho | T-45, T-46, T-65 |
| AC-I02 — `SetActive(false)` ⇒ `off`; lock ausente | T-45, T-46, T-65 |
| AC-I03 — `Toggle()` retorna o novo estado e equivale a `SetActive(not current)` | T-47, T-48 |
| AC-I04 — `GetLastError()` vazio em operação normal; preenchido após falha forçada | T-47, T-57, T-58 |
| AC-I05 — `StateChanged` em cada transição, só `on/off/error` | T-47, T-48 |
| AC-I06 — ON otimista com debounce longo ⇒ `on` antes da confirmação | T-57, T-58 |
| AC-I07 — rota (i): confirmação dentro da janela ⇒ permanece `on` | T-57, T-58 |
| AC-I08 — rota (ii): confirmação falha ⇒ `error` + `StateChanged("error")` | T-57, T-58 |
| AC-I09 — rota (iii): `SetActive(false)` na janela ⇒ `off`, sem `error` | T-57, T-58 |
| AC-I10 — queda do PowerDevil com `on` ⇒ `error`; retorno ⇒ `on` com uma tentativa | T-59, T-60 |
| AC-I11 — filho do `systemd-inhibit` mantém o mesmo PID na queda/retorno | T-59, T-60 |
| AC-I12 — `SIGTERM`/`SIGINT` liberam os dois e saem 0 | T-51, T-52 |
| AC-I13 — `Quit()` libera, encerra e o nome some | T-51, T-52 |
| AC-I14 — `PDEATHSIG`: `SIGKILL` no daemon ⇒ nenhum filho órfão | T-55, T-56 |
| AC-I15 — `Local.Disconnected`: barramento fecha ⇒ exit 0 sem `Uninhibit` | T-53, T-54 |
| AC-I16 — segunda instância sai 0 sem tomar o nome | T-49, T-50 |
| AC-I17 — log > 256 KB ⇒ `daemon.log.1` e `daemon.log` recomeça | T-43, T-44 |
| AC-O01 — ciclo real de ~5–6 s no Kubuntu fecha em `on` e depois `off` | T-66 |
| AC-G01 — gate unitário verde | T-64 |
| AC-G02 — gate de integração verde | T-65 |
| AC-G03 — nenhum órfão (daemon, fake, `systemd-inhibit`) após a suíte | T-42, T-65, T-67 |
| AC-G04 — `systemd-inhibit --list` contém o filho só durante o ON e o PID sobrevive à queda | T-45, T-59, T-60, T-66 |
| AC-G05 — nenhuma decisão da spec contrariada; nenhuma dependência nova | T-02, T-67 |
| AC-G06 — nenhum artefato de spec em código/comentários/commits/PRs | T-67, T-68 |

## Cobertura das decisões do design (ADR)

| Decisão | Tasks que a fixam |
|---|---|
| ADR-01 — injeção keyword-only na `StateMachine`; `activate()` sem inibidores ⇒ `RuntimeError` | T-20, T-21 |
| ADR-02 — degradação do `confirm()` KDE só quando o mecanismo não existe | T-16, T-17 |
| ADR-03 — liveness restrita ao backend ativo + proxies; `_lost` e uma tentativa | T-59, T-60 |
| ADR-04 — queda do GSM com backend `gsm` = fim de sessão | T-59, T-60 |
| ADR-05 — `debounce` como guarda; `verify_delay` agendado pela máquina | T-28, T-29, T-57, T-58 |
| ADR-06 — `last_error` só em `error`; `Toggle` em `error` ativa; sem reemissão | T-24, T-25, T-26, T-27 |
| ADR-07 — `main()` com overrides keyword-only para testes | T-43, T-44, T-57 |
| ADR-08 — erro de liveness preserva o filho; ativação/verificação libera tudo | T-24, T-25, T-30, T-31, T-32, T-33 |
| ADR-09 — exportar o objeto antes do `request_name`; `DO_NOT_QUEUE`; segunda instância sai 0 | T-49, T-50 |
| ADR-10 — `set_exit_on_disconnect(False)` + `Local.Disconnected` | T-53, T-54 |
| ADR-11 — grupo de processos, `PDEATHSIG` e `stderr` | T-07, T-08, T-55, T-56 |
| ADR-12 — rotação de log com `RotatingFileHandler` e fallback | T-43, T-44 |
| ADR-13 — cadeia de backends e fallback | T-12, T-13, T-61, T-62 |
| ADR-14 — agendamento em milissegundos | T-21, T-28, T-29 |
| ADR-15 — fakes de integração e isolamento por PID do filho | T-38, T-39, T-40, T-41, T-42, T-45 |
| ADR-16 — `release()` limpa cookie e mantém o último backend | T-14, T-15, T-31, T-33 |
| ADR-17 — idempotência e ativação explícita a partir de `error` | T-22, T-24, T-25, T-26, T-27 |
| ADR-18 — mensagens em pt-BR; `who`/`why` fixos em inglês | T-07, T-13, T-17, T-44 |

## Notas de execução

1. **RED obrigatório:** em cada task de teste, rodar o comando e confirmar a falha esperada (import ausente, atributo ausente ou asserção). Se um teste passar antes da implementação, ele é regressão — registrar no comentário da task e não “implementar” o que já existe.
2. **Não vazar processos:** todo teste de integração precisa de `try/finally`/fixture que mate fakes, daemon e filho. O gate G-E2 reprova órfãos.
3. **Nunca usar `git add -A`/`git add .`:** `README.md`, `docs/implementation/` e artefatos gerados (`.log`, `.jsonl`, `.tmp`) ficam fora do PR de código; a documentação vai em PR/commit `docs:` separado.
4. **Sem artefatos de spec no código:** `core/` e `tests/` não podem citar `AC-*`, `T-*`, `design_e2.md`, `tasks_e2.md`, `spec.md` ou `DELIVERY_MAP.md` em código, comentários, commits ou corpo do PR.
5. **Estado sempre nasce `off`:** nenhum teste pode depender de `core/config.py`; o daemon não lê nem escreve `config.json`.
6. **PRs empilhados:** E2 → E1, E3 → E2, E4 → E3; E5 → E3 (paralela à E4); E6 só depois de E4 e E5 mergeadas. A branch da E2 nasce de `feat/e1-esqueleto-ambiente-config` e o PR tem essa branch como base; não retargetar para `main` sem confirmação. Depois do merge da E1, o PR da E2 pode ser rebaseado/retargetado conforme a política do repositório.
