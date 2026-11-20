# Tasks: E1 — Esqueleto, Ambiente e Config
**Feature:** DeskAwake — E1 | **Data:** 2026-11-19 | **Estimativa:** ≈ 5 h (27 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 1–33 e “Contratos”) | [`design_e1.md`](design_e1.md) | [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E1

## Resumo
- Total de tasks: 27
- Estimativa total: ≈ 5 h
- Dependências externas: `pytest` de desenvolvimento (`python3-pytest` via apt, instalado pelo desenvolvedor); branch `feat/e1-esqueleto-ambiente-config` criada a partir da `main`; `gh` autenticado para o PR. Nenhuma migration, serviço ou dependência nova de runtime.
- Gate: **G-E1** — `python3 -m pytest tests/unit/test_config.py tests/unit/test_environment.py -v` verde.
- Fora de escopo (não criar nesta entrega): `core/inhibitors.py`, `core/state.py`, `core/daemon.py`, `core/cli.py`, `bin/`, `ui_gtk/`, `plasmoid/`, `install.sh`, `uninstall.sh`, `verify.sh`, `data/`, READMEs e `tests/conftest.py`.

**Sequência:** setup → `core/config.py` (TDD) → `core/environment.py` (TDD) → validação/entrega. Cada par RED/GREEN executa o teste antes da implementação; não pular o RED.

## Tasks

### 0. Setup e fundação

- [ ] **T-01**: Criar a branch da entrega a partir da `main`
  - Comando: `git switch -c feat/e1-esqueleto-ambiente-config`
  - Critério: `git branch --show-current` imprime `feat/e1-esqueleto-ambiente-config`; `README.md` e `docs/implementation/` pré-existentes permanecem intocados
  - Estimativa: 2min

- [ ] **T-02**: Garantir o `pytest` de desenvolvimento
  - Comando: `python3 -m pytest --version`
  - Critério: exit 0. Se ausente, instalar com `sudo apt install python3-pytest` (passo manual do desenvolvedor; não criar script nem adicionar ao `install.sh`) e repetir o comando
  - Estimativa: 2min

- [ ] **T-03**: Criar `pyproject.toml` mínimo
  - Arquivo: `pyproject.toml`
  - Conteúdo:
    ```toml
    [project]
    name = "deskawake"
    version = "0.1.0"
    requires-python = ">=3.10"

    [tool.pytest.ini_options]
    testpaths = ["tests"]
    markers = [
      "slow: testes opt-in de ciclo real (debounce/verificação de ~5-6 s)",
    ]
    ```
  - Comando: `python3 -c "import pathlib; t = pathlib.Path('pyproject.toml').read_text(encoding='utf-8'); assert 'requires-python = \">=3.10\"' in t; assert '[tool.pytest.ini_options]' in t; assert 'testpaths = [\"tests\"]' in t; assert '[build-system]' not in t"`
  - Critério: exit 0; sem `[build-system]`, sem `dependencies`, sem `setup.py`/`setup.cfg`
  - Estimativa: 5min

- [ ] **T-04**: Criar o pacote `core` e o diretório de testes
  - Arquivos: `core/__init__.py` (vazio) e `tests/unit/` (sem `__init__.py` e sem `conftest.py`)
  - Comando: `test -f core/__init__.py && test -d tests/unit && test -z "$(find tests -name conftest.py -print -quit)"`
  - Critério: exit 0
  - Estimativa: 2min

- [ ] **T-05**: Conferir o `LICENSE` existente (sem alteração)
  - Comando: `grep -q "MIT License" LICENSE && grep -q "Copyright (c) 2026 Marcelo Silva" LICENSE && git diff --quiet -- LICENSE`
  - Critério: exit 0; arquivo MIT de 2026 permanece sem modificação
  - Estimativa: 2min

### 1. `core/config.py` (TDD)

- [ ] **T-06**: Escrever o teste RED de `load_config()` sem arquivo
  - Arquivo: `tests/unit/test_config.py`
  - Teste: `test_load_missing_returns_defaults_without_creating_file` — `monkeypatch.setattr(core.config, "CONFIG_PATH", tmp_path / "deskawake" / "config.json")`; chama `load_config()`; espera `{"version": 1, "theme": "auto"}` e nenhum arquivo/diretório criado
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k load_missing`
  - Critério: falha (RED) por `core.config`/`load_config` ausente; nenhum arquivo criado em `tmp_path`
  - Estimativa: 10min

- [ ] **T-07**: Implementar `load_config()` mínimo para arquivo ausente
  - Arquivo: `core/config.py`
  - Contrato: constantes `CONFIG_PATH`, `CONFIG_VERSION = 1`, `DEFAULT_THEME = "auto"`, `MARGIN = 24`, `PILL_WIDTH = 124`, `PILL_HEIGHT = 42`, `VALID_THEMES`, `Position` e `WorkArea`; `load_config()` lê o global `CONFIG_PATH` em tempo de chamada (não capturado em default de função) e retorna um dict novo. Para arquivo existente, apenas `json.loads` e retorno do dict bruto, **sem** tratamento de corrupção/normalização ainda
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k load_missing`
  - Critério: T-06 passa (GREEN); `python3 -m compileall -q core/config.py` exit 0
  - Estimativa: 15min

- [ ] **T-08**: Escrever os testes RED de `save_config()`
  - Arquivo: `tests/unit/test_config.py`
  - Testes:
    - `test_save_load_roundtrip` — `{"version": 1, "theme": "dark", "position": {"x": 10, "y": 20}}` sobrevive ao save + load; diretório criado
    - `test_save_leaves_no_tmp` — após o save, nenhum `*.tmp` no diretório
    - `test_save_config_whitelists_keys` — chaves extras (`active`, `extra`) não vão para o disco
    - `test_save_config_normalizes_invalid_theme` — `theme="blue"` vira `"auto"` no disco
    - `test_save_config_accepts_position_tuple` — `position=(10, 20)` vira `{"x": 10, "y": 20}`
    - `test_save_failure_removes_tmp` — `os.replace` levantando `OSError` propaga o erro e remove o `.tmp` (best effort)
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k save`
  - Critério: falha (RED) por `save_config` ausente
  - Estimativa: 15min

- [ ] **T-09**: Implementar `save_config()` com escrita atômica
  - Arquivo: `core/config.py`
  - Contrato: grava somente `version` (sempre `1`), `theme` e `position`; normaliza `theme` inválido para `DEFAULT_THEME`; aceita `{"x": int, "y": int}` ou sequência de 2 inteiros (rejeitando `bool`), gravando sempre como objeto; posição malformada é omitida; `mkdir(parents=True, exist_ok=True)`; grava `config.json.tmp` no **mesmo diretório** e usa `os.replace()`; em erro, remove o `.tmp` em best effort e propaga `OSError`
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k save`
  - Critério: todos os testes de T-08 passam (GREEN); nenhum `.tmp` remanescente
  - Estimativa: 20min

- [ ] **T-10**: Escrever os testes RED de corrupção e recuperação
  - Arquivo: `tests/unit/test_config.py`
  - Testes:
    - `test_corrupt_json_quarantines_and_recovers` — conteúdo `"{oops"` vira `config.json.bak` com os bytes originais; defaults retornados; `config.json` novo é válido
    - `test_invalid_theme_quarantines` — `{"version": 1, "theme": "blue"}` gera `.bak` e defaults
    - `test_non_dict_root_quarantines` — raiz `[]`/`"x"` gera `.bak`
    - `test_unknown_version_quarantines` — `version: 2` gera `.bak`
    - `test_missing_theme_or_version_quarantines` — `{"version": 1}`, `{"theme": "auto"}` e `{}` (parametrizado) geram `.bak`
    - `test_read_oserror_returns_defaults_without_bak` — `CONFIG_PATH` apontando para um diretório (leitura levanta `OSError`) retorna defaults, sem `.bak` e sem exceção
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k "quarantine or oserror"`
  - Critério: falha (RED) nos casos de corrupção
  - Estimativa: 15min

- [ ] **T-11**: Implementar a quarentena `.bak` e a recuperação
  - Arquivo: `core/config.py`
  - Regras: `JSONDecodeError`/`UnicodeDecodeError`, raiz não-objeto, `version` ausente ou ≠ `1`, e `theme` ausente ou fora de `VALID_THEMES` são corrupção; renomear para `config.json.bak` (sobrescrevendo o anterior), gravar defaults e retornar defaults; `OSError` de leitura retorna defaults sem renomear nem levantar
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k "quarantine or oserror"`
  - Critério: todos os testes de T-10 passam (GREEN); `.bak` contém o conteúdo original; `config.json` recriado é válido
  - Estimativa: 20min

- [ ] **T-12**: Escrever os testes RED de normalização sem `.bak`
  - Arquivo: `tests/unit/test_config.py`
  - Testes:
    - `test_malformed_position_is_dropped_without_bak` — `position` não-objeto ou com `x`/`y` não-inteiro é descartada; `theme` é preservado; sem `.bak`; arquivo reescrito sem `position`
    - `test_extra_keys_are_dropped_without_bak` — chave extra na raiz (`active`) e dentro de `position` (`z`) são removidas; sem `.bak`; `theme` e `position` válidos preservados; arquivo reescrito só com chaves conhecidas
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k "malformed or extra"`
  - Critério: falha (RED) porque `load_config` ainda retorna o dict bruto
  - Estimativa: 15min

- [ ] **T-13**: Implementar a normalização do JSON válido
  - Arquivo: `core/config.py`
  - Regras: após leitura válida, manter apenas `version`, `theme` e `position`; validar `position` como objeto com `x`/`y` inteiros (rejeitar `bool`); se inválida, omitir; reescrever atomicamente **somente** se o normalizado diferir do bruto; nunca criar `.bak` nesse caminho
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k "malformed or extra"`
  - Critério: testes de T-12 passam (GREEN); `.bak` ausente; JSON em disco exatamente normalizado
  - Estimativa: 20min

- [ ] **T-14**: Escrever os testes RED de `default_position()`
  - Arquivo: `tests/unit/test_config.py`
  - Testes:
    - `test_default_position_primary_monitor` — workarea `(0, 0, 1920, 1050)` ⇒ `(1772, 24)`
    - `test_default_position_empty_workareas` — lista vazia ⇒ `(24, 24)`
    - `test_default_position_narrow_workarea` — workarea `(0, 0, 100, 100)` ⇒ `(24, 24)` (proteção do `max`, ADR-03)
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k default_position`
  - Critério: falha (RED) por `default_position` ausente
  - Estimativa: 10min

- [ ] **T-15**: Implementar `default_position()`
  - Arquivo: `core/config.py`
  - Contrato: primeira workarea é o monitor primário; `x = max(wx + MARGIN, wx + ww - PILL_WIDTH - MARGIN)`; `y = wy + MARGIN`; lista vazia ⇒ `(MARGIN, MARGIN)`; retorna tupla, sem importar `Gtk`/`Gdk`
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k default_position`
  - Critério: testes de T-14 passam (GREEN)
  - Estimativa: 5min

- [ ] **T-16**: Escrever os testes RED de `validate_position()`
  - Arquivo: `tests/unit/test_config.py`
  - Testes:
    - `test_validate_position_inside_keeps` — `(100, 100)` dentro de `(0, 0, 1920, 1050)` ⇒ `(100, 100)`
    - `test_validate_position_outside_falls_back` — fora de todos os monitores ⇒ `default_position(...)`
    - `test_validate_position_accepts_secondary_monitor` — segundo monitor (inclusive com coordenada negativa) aceito
    - `test_validate_position_accepts_position_mapping` — `{"x": 100, "y": 100}` ⇒ `(100, 100)`
    - `test_validate_position_invalid_input_falls_back` — `None`, string, sequência curta, `x` string e `x` booleano ⇒ default
    - `test_validate_position_boundary_is_half_open` — `(1919, 1049)` válido; `(1920, 1049)` e `(1919, 1050)` ⇒ default (ADR-07)
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k validate_position`
  - Critério: falha (RED) por `validate_position` ausente
  - Estimativa: 15min

- [ ] **T-17**: Implementar `validate_position()`
  - Arquivo: `core/config.py`
  - Contrato: aceita `{"x": int, "y": int}` ou tupla/lista de 2 inteiros (rejeitar `bool`); mantém o ponto se cair em `[wx, wx+ww) × [wy, wy+wh)` de qualquer workarea; caso contrário, `default_position(workareas)`
  - Comando: `python3 -m pytest tests/unit/test_config.py -v -k validate_position`
  - Critério: testes de T-16 passam (GREEN)
  - Estimativa: 15min

- [ ] **T-18**: Refatorar `core/config.py` mantendo a suíte verde
  - Arquivo: `core/config.py`
  - Critério: extrair helpers privados se necessário (`_defaults`, `_read`, `_quarantine`, `_normalize`, `_atomic_write`); garantir que `CONFIG_PATH` é lido em tempo de chamada; sem `Gtk`/`Gdk` e sem `sys.exit`; rodar `python3 -m pytest tests/unit/test_config.py -v` e `python3 -m compileall -q core/config.py` com exit 0
  - Estimativa: 10min

### 2. `core/environment.py` (TDD)

- [ ] **T-19**: Escrever os testes RED de ambiente e ferramentas
  - Arquivo: `tests/unit/test_environment.py`
  - Fake local de barramento: `name_has_owner(nome) -> bool` e `call_blocking(...)` que registra a chamada e levanta `AssertionError` se usado (verificação feita também por uma lista de chamadas, sem engolir a asserção)
  - Testes:
    - `test_empty_env_defaults` — `env={}` ⇒ `desktop=""`, `session_type=""`, `wayland_display=None`, `is_wayland() is False`, backends todos `False`
    - `test_injected_env_does_not_mix_os_environ` — com `XDG_CURRENT_DESKTOP=KDE` no processo, `env={}` continua produzindo `desktop=""`
    - `test_desktop_is_raw_value` — `"ubuntu:MATE"` permanece bruto
    - `test_session_type_is_lowercased` — `"X11"` ⇒ `"x11"`
    - `test_mate_x11_detection` — `MATE`/`x11` ⇒ `desktop="MATE"`, `session_type="x11"`, `is_wayland() is False`
    - `test_wayland_detection` — `wayland` + `WAYLAND_DISPLAY=wayland-0` ⇒ `is_wayland() is True`
    - `test_wayland_display_empty_is_none` — `WAYLAND_DISPLAY=""` ⇒ `None`
    - `test_is_wayland_ignores_wayland_display` — `session_type="x11"` + `WAYLAND_DISPLAY` definido ⇒ `False` (ADR-04)
    - `test_tools_detection` — `which` injetado marcando `gdbus`/`systemd-inhibit` e omitindo `kpackagetool6`
    - `test_kpackagetool6_absent_is_false_without_exception` — `which` sem `kpackagetool6` ⇒ `False`, sem exceção
  - Comando: `python3 -m pytest tests/unit/test_environment.py -v`
  - Critério: falha (RED) por `core.environment` ausente
  - Estimativa: 20min

- [ ] **T-20**: Implementar `Environment`, `detect_environment()` (parte sem barramento) e `is_wayland()`
  - Arquivo: `core/environment.py`
  - Contrato: dataclass `frozen=True` com `desktop`, `session_type`, `wayland_display`, `backends`, `tools`; `BACKEND_BUS_NAMES` e `TOOL_NAMES`; `env=None` lê `os.environ`, `env` injetado é usado integralmente; `desktop` bruto; `session_type` minúsculo; `WAYLAND_DISPLAY` vazio/ausente ⇒ `None`; `tools[nome] = which(nome) is not None`; backends iniciam todos `False` (preenchidos em T-22); `is_wayland()` olha somente `session_type`; `from __future__ import annotations`; sem `Gtk`/`Gdk`/`sys.exit`
  - Comando: `python3 -m pytest tests/unit/test_environment.py -v`
  - Critério: todos os testes de T-19 passam (GREEN); `python3 -m compileall -q core/environment.py` exit 0
  - Estimativa: 20min

- [ ] **T-21**: Escrever os testes RED de backends via `NameHasOwner`
  - Arquivo: `tests/unit/test_environment.py`
  - Testes:
    - `test_backends_by_name_owner` — fake com dono de `org.mate.ScreenSaver` e `org.gnome.SessionManager` ⇒ `mate=True`, `gsm=True`, `fdo=False`, `policyagent=False`
    - `test_detection_only_uses_name_has_owner` — após `detect_environment`, `name_has_owner` foi chamado para os 4 nomes de `BACKEND_BUS_NAMES` e `call_blocking` nunca foi chamado
    - `test_no_session_bus_marks_all_backends_false` — `monkeypatch` em `core.environment.dbus.SessionBus` levantando `dbus.DBusException`; `bus=None` ⇒ todos `False`, sem exceção
  - Comando: `python3 -m pytest tests/unit/test_environment.py -v -k "backends or name_has_owner or session_bus"`
  - Critério: falha (RED) em `test_backends_by_name_owner`; `call_blocking` permanece sem chamadas
  - Estimativa: 15min

- [ ] **T-22**: Implementar a detecção de backends
  - Arquivo: `core/environment.py`
  - Contrato: `bus=None` tenta `dbus.SessionBus()`; falha (`dbus.DBusException`, `OSError`, `KeyError`) mantém `bus=None` e todos os backends `False`; cada backend usa exclusivamente `bus.name_has_owner(BACKEND_BUS_NAMES[nome])`, com falha por backend virando `False`; nenhum método de backend é chamado; a conexão não é fechada
  - Comando: `python3 -m pytest tests/unit/test_environment.py -v -k "backends or name_has_owner or session_bus"`
  - Critério: testes de T-21 passam (GREEN); nenhum `call_blocking` executado
  - Estimativa: 15min

- [ ] **T-23**: Refatorar `core/environment.py` mantendo a suíte verde
  - Arquivo: `core/environment.py`
  - Critério: sem duplicar a regra combinada de Wayland (pertence à E3); `is_wayland()` estável; sem `sys.exit`; rodar `python3 -m pytest tests/unit/test_environment.py -v` e `python3 -m compileall -q core/environment.py` com exit 0
  - Estimativa: 5min

### 3. Validação final e entrega

- [ ] **T-24**: Rodar a suíte completa
  - Comando: `python3 -m pytest -v`
  - Critério: 0 failures, 0 errors, 0 skipped; `find . -name '*.tmp' -not -path './.git/*'` sem saída
  - Estimativa: 5min

- [ ] **T-25**: Executar as verificações manuais rápidas
  - Config, com `HOME` isolado:
    ```bash
    tmp=$(mktemp -d)
    HOME="$tmp" python3 -c "from core.config import load_config; print(load_config())"
    test ! -e "$tmp/.config/deskawake/config.json"
    rm -rf "$tmp"
    ```
    Saída esperada: `{'version': 1, 'theme': 'auto'}` e nenhum arquivo criado.
  - Ambiente:
    ```bash
    python3 -c "from core.environment import detect_environment as d, is_wayland; e=d(); print(e); print('wayland:', is_wayland(e))"
    ```
    Mint 22.3 MATE/X11: `desktop='MATE'`, `session_type='x11'`, `is_wayland` falso, `backends['mate']=True`, `backends['fdo']=False`, `tools['kpackagetool6']=False`. Kubuntu 26.04/Plasma 6.6: `desktop='KDE'`, `session_type='wayland'`, `wayland_display='wayland-0'`, `backends['fdo']=True`, `backends['policyagent']=True`, `tools['kpackagetool6']=True`.
  - Critério: executar nas duas máquinas; se uma não estiver disponível, registrar a pendência no corpo do PR (não bloqueia o gate automatizado)
  - Estimativa: 10min

- [ ] **T-26**: Auditar escopo e higiene
  - Comandos:
    - `grep -RInE "Gtk|Gdk|xdg-screensaver|sys\.exit" core/` ⇒ sem saída
    - `grep -RInE "AC-[0-9]|T-[0-9]|design_e|tasks\.md" core tests pyproject.toml` ⇒ sem saída
    - `python3 -m compileall -q core tests` ⇒ exit 0
    - `find tests -name conftest.py -print -quit` ⇒ sem saída
    - `git status --short` ⇒ só arquivos da entrega (+ `docs/implementation/` já versionada, fora do stage); nenhum `.tmp`
  - Critério: todos os comandos conforme acima; nenhuma dependência de runtime nova
  - Estimativa: 10min

- [ ] **T-27**: Preparar commit e PR somente com a entrega
  - Comandos:
    - `git add pyproject.toml core/__init__.py core/config.py core/environment.py tests/unit/test_config.py tests/unit/test_environment.py`
    - `git diff --cached --name-only` ⇒ exatamente os 6 arquivos acima
    - `python3 -m pytest tests/unit/test_config.py tests/unit/test_environment.py -v` ⇒ gate G-E1 verde
    - `git commit -m "feat(e1): esqueleto, ambiente e config"`
    - `git push -u origin feat/e1-esqueleto-ambiente-config`
    - `gh pr create --base main --head feat/e1-esqueleto-ambiente-config --title "feat(e1): esqueleto, ambiente e config" --body "<corpo no template do DELIVERY_MAP §0.2>"`
    - `gh pr view --json files --jq '.files[].path'` ⇒ apenas os 6 arquivos da entrega
  - Corpo do PR: gate com comando/resultado, checklist manual, fora de escopo e riscos residuais; **não** citar `spec.md`, `design_e1.md`, `tasks.md` nem IDs `AC-*`/`T-*`
  - Critério: PR contém apenas os 6 arquivos; `docs/implementation/` e `README.md` fora do stage/PR de código
  - Estimativa: 15min

## Mapeamento AC → Tasks

AC-01…AC-10 vêm de `DELIVERY_MAP.md` §E1.4; AC-11…AC-13 vêm da definição de pronto do `design_e1.md` §6.3.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-01 — `load_config()` sem arquivo ⇒ defaults, sem criar arquivo | T-06, T-07 |
| AC-02 — round-trip de `save_config()`/`load_config()`; nenhum `.tmp` | T-08, T-09, T-24 |
| AC-03 — JSON corrompido ⇒ `.bak`, defaults, `config.json` novo válido | T-10, T-11 |
| AC-04 — `theme` inválido ⇒ corrupção com `.bak` | T-10, T-11 |
| AC-05 — `validate_position` dentro/fora/múltiplos monitores | T-16, T-17 |
| AC-06 — `default_position` com `(0,0,1920,1050)` ⇒ `(1772, 24)` | T-14, T-15 |
| AC-07 — `MATE/x11` ⇒ detecção correta e `is_wayland() is False` | T-19, T-20 |
| AC-08 — `wayland` + `WAYLAND_DISPLAY` ⇒ `is_wayland() is True` | T-19, T-20 |
| AC-09 — `which` sem `kpackagetool6` ⇒ `False`, sem exceção | T-19, T-20 |
| AC-10 — `bus` fake com/sem dono; nenhum `call_blocking` de backend | T-21, T-22 |
| AC-11 — nenhum `.tmp` remanescente após a suíte | T-08, T-09, T-24 |
| AC-12 — nenhuma decisão da spec contrariada; nenhuma dependência nova | T-23, T-26 |
| AC-13 — nenhum artefato de spec em código/comentários/commits/PRs | T-26, T-27 |

## Cobertura das decisões do design (ADR)

| Decisão | Tasks que a fixam |
|---|---|
| ADR-01 — `pyproject.toml` sem build backend | T-03 |
| ADR-02 — quarentena `.bak` × normalização sem `.bak` | T-10, T-11, T-12, T-13 |
| ADR-03 — primeira workarea é a primária; lista vazia ⇒ margem | T-14, T-15 |
| ADR-04 — `is_wayland()` olha somente `session_type` | T-19, T-20 |
| ADR-05 — detecção read-only via `NameHasOwner` | T-21, T-22 |
| ADR-06 — costuras de teste (monkeypatch de `CONFIG_PATH`; `env`/`bus`/`which` injetados) | T-06, T-19, T-21 |
| ADR-07 — validação do ponto âncora, não do retângulo | T-16, T-17 |
| ADR-08 — `save_config` com whitelist e normalização | T-08, T-09 |

Todos os testes nomeados no `design_e1.md` §6.1 estão distribuídos entre T-06 e T-22; os testes extras (`save_failure_removes_tmp`, `read_oserror_returns_defaults_without_bak`, `default_position_narrow_workarea`, `validate_position_boundary_is_half_open`, `session_type_is_lowercased`, `injected_env_does_not_mix_os_environ`, `is_wayland_ignores_wayland_display`) fixam contratos das ADRs e das tabelas do design.
