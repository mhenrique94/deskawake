# Mapa de entregas — DeskAwake

> **Fonte única de verdade:** [`spec.md`](spec.md), aprovado em 2026-11-19 e hidratado para
> **Kubuntu 26.04.1 / KDE Plasma 6.6.7 (Wayland)** e **Linux Mint 22.3 “Zena” / MATE 1.26 (X11)**.
>
> Este documento **organiza a execução** e **não decide nada novo**. Toda decisão, valor, contrato,
> string e restrição vem da `spec.md` (decisões 1–38, “Fluxo alvo”, “Contratos”, “Notas ao
> implementador”, “Variações por distro” e apêndices de validação). Em caso de conflito entre este
> mapa e a spec, **a spec vence** — e o mapa é corrigido, não a spec.

> **Reprogramação (2026-11-21):** a antiga “E6 — instalador” foi dividida. **E6 = UI GTK/MATE**
> (ajustes, paridade visual e créditos), **E7 = instalação/desinstalação/verificação/testes/docs** e
> **E8 = empacotamento/distribuição** (placeholder). Onde as seções históricas de E1–E5 dizem “E6”
> para instalador, READMEs ou `.service`, leia **E7**; onde dizem “E6” para UI/validação MATE, leia
> **E6**. Os designs completos estão em [`design_e6.md`](design_e6.md), [`design_e7.md`](design_e7.md)
> e [`design_e8.md`](design_e8.md).

---

## 0. Como ler este mapa

- **E1 → E2 → E3 → E4** são estritamente sequenciais e **empilhadas**: a branch de cada entrega
  nasce da branch da anterior (`E2` sobre `E1`, `E3` sobre `E2`, `E4` sobre `E3`).
- **E5 (Plasmoid/KDE)** é **independente da E4**: empilha sobre a **E3** e consome apenas o contrato
  D-Bus do daemon. E4 e E5 podem ser feitas em paralelo ou em qualquer ordem.
- **E6 (UI GTK/MATE)** depende de E1–E5 e fecha a parte visual/funcional do MATE (A1–A7 na UI,
  créditos e versão). **E7 (instalação)** depende da E6 e instala artefatos reais. **E8
  (distribuição)** depende da E7 e está como placeholder decisório.
- Cada entrega termina com um **gate**: suíte da entrega verde + critérios de aceite abaixo.
  Nenhuma entrega “adiada para a próxima” — o que não pertence ao escopo é explicitamente listado
  como **fora de escopo**.
- **Definição de pronto (vale para todas):** `python3 -m pytest` verde no escopo da entrega;
  `shellcheck` limpo quando a ferramenta existir (ausente no Mint e no Kubuntu validados);
  nenhuma decisão da spec contrariada; nenhuma dependência nova além de `python3-gi`,
  `python3-dbus`, `systemd`, `kpackagetool6` (KDE), `libglib2.0-bin` e `pytest` (somente dev).

### 0.1 Regras herdadas do ambiente

- `pytest` é **dependência de desenvolvimento**, instalada por `apt install python3-pytest`
  (7.4.4 no Mint, 9.0.2 no Kubuntu) e executada como `python3 -m pytest`. **Nunca** instalada pelo
  `install.sh`.
- Nada de `sudo` em qualquer script entregue ao usuário.
- Sem empacotamento de distro na E7 (`.deb`, AUR, Flatpak). O `.deb` via GitHub Releases é a **E8**
  (placeholder); AUR/Flatpak/AppImage ficam fora. `pyproject.toml` existe **só** para configurar
  `pytest`.
- Sem suporte a Windows/macOS; sem testes de GUI automatizados (comportamento visual é checklist
  manual, conforme convenção da spec).

### 0.2 Fluxo de Git e PRs

Regra do projeto: **nunca** commitar nem pushar direto na `main`. Toda entrega entra por branch +
PR, e **uma entrega = um PR**.

- **Base:** entregas **empilhadas** `E1 → E2 → E3 → E4`: cada branch nasce da branch da entrega
  anterior e o PR aponta para ela (`E2` → `E1`, `E3` → `E2`, `E4` → `E3`). **E5** empilha sobre a
  **E3** (mesma base da E4; E4 e E5 podem ficar abertos ao mesmo tempo, em qualquer ordem).
  **E6** nasce da `main` após E4 e E5 mergeadas; **E7** nasce da `main` após a E6; **E8** nasce da
  `main` após a E7.
- **Merge:** merge commit pelo GitHub (`Merge pull request #N from ...`), como no histórico atual.
  Sem squash e sem reescrever branch de outra pessoa.
- **Gate antes do merge:** o gate da entrega (G-E1…G-E8) precisa estar verde **no PR** — comandos
  executados e resultado colados na descrição; checklists manuais exigidas pela entrega (E4/E5/E6/E7)
  precisam estar preenchidas. PR verde no gate não substitui o gate: é o mesmo critério.
- **Correção pós-merge:** abrir `fix(eN): ...` em novo PR (`fix/eN-<resumo>`). Nunca corrigir
  direto na `main`.
- **Higiene:** commits e PRs de entrega contêm apenas a entrega de código. A documentação de
  implementação (`spec.md`, `DELIVERY_MAP.md`, `design_e*.md`, `tasks_e*.md` e `visual/`) fica
  versionada em `docs/implementation/` e entra em PR/commit `docs:` separado. A **E7** é a exceção
  de documentação de usuário: entrega `README.md` e `README.en.md`. A E6 não entrega README.
- **Commits:** `feat(eN): <resumo em pt-BR, imperativo>` (ex.: `feat(e1): adiciona config e
  detecção de ambiente`). Commits intermediários são permitidos; o PR é que precisa fechar verde.

| Entrega | Branch sugerida | Título do PR |
|---|---|---|
| **E1** | `feat/e1-esqueleto-ambiente-config` | `feat(e1): esqueleto, ambiente e config` |
| **E2** | `feat/e2-inibidores-estado-daemon` | `feat(e2): inibidores, máquina de estados e daemon` |
| **E3** | `feat/e3-cli-launcher` | `feat(e3): CLI e launcher` |
| **E4** | `feat/e4-widget-gtk-mate` | `feat(e4): widget GTK3 para MATE/X11` |
| **E5** | `feat/e5-plasmoid-kde` | `feat(e5): Plasmoid para Plasma 6.6` |
| **E6** | `feat/e6-ui-gtk-mate` | `feat(e6): ajustes, paridade visual e créditos do GTK/MATE` |
| **E7** | `feat/e7-instalador-verificacao-docs` | `feat(e7): instalador, verificação e documentação` |
| **E8** | `feat/e8-distribuicao` | `feat(e8): empacotamento e distribuição` (placeholder) |

**Corpo do PR (template):**

```markdown
## E<n> — <título da entrega>

**Gate:** G-E<n> — `<comando>` → <resultado>
**Checklist manual:** <itens marcados / não se aplica>
**Fora de escopo:** <o que ficou de fora, conforme a seção da entrega>
**Riscos residuais:** <linhas aplicáveis do §5 ou "nenhum">
```

---

## 1. Restrições globais (valem para E1–E8)

| # | Restrição | Valor exato |
|---|---|---|
| G1 | Licença | MIT (`LICENSE` já presente no repo) |
| G2 | Python | ≥ 3.10 (validado em 3.12.3 no Mint e 3.14.4 no Kubuntu) |
| G3 | Nome D-Bus / objeto / interface | `org.local.DeskAwake` / `/org/local/DeskAwake` / `org.local.DeskAwake` |
| G4 | Estados públicos | `"on" \| "off" \| "error"` — **nunca** `activating`/`deactivating` no barramento |
| G5 | Escopo do ON | Tudo ou nada: inibidor de tela confirmado **e** `systemd-inhibit` confirmado |
| G6 | `systemd-inhibit` | `--what=idle --mode=block --who=DeskAwake --why=<motivo>`; **`sleep` nunca** |
| G7 | Backend de tela | Cadeia FDO → MATE → GSM, na **mesma conexão** D-Bus do daemon |
| G8 | `xdg-screensaver` | **Proibido** como backend |
| G9 | Persistência | Só tema e posição (GTK). Estado sempre nasce `off` |
| G10 | Log | `~/.local/state/deskawake/daemon.log`, rotação em **256 KB** para `daemon.log.1` |
| G11 | Pílula | **124×42** lógico, borda fina, sem gradiente/sombra, sem animação contínua |
| G12 | Cores de estado | menta `#80D9A4` (on), cinza `#929DA5` (off), vermelho `#E47F7F` (erro) |
| G13 | Fonte GTK | `"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif` |
| G14 | `@font-face` | **Proibido** (GTK 3.24.41 responde `unknown @ rule`) |
| G15 | Plasmoid | Transporte nativo `org.kde.plasma.workspace.dbus`; **sem** `Plasma5Support`, `gdbus`, polling |
| G16 | Plasma mínimo | ≥ 6.4 (`SignalWatcher`) |
| G17 | `CanSuspend` | **Nunca** usado como teste de inibição |
| G18 | Cookie | Só vale na conexão que o obteve; nunca abrir conexão nova para `UnInhibit` |
| G19 | Documentação | `README.md` (pt-BR) + `README.en.md`; spec/design internos em pt-BR |

---

## 2. Árvore do repositório (alvo)

Derivada de “Arquivos instalados” e das tarefas 1–15 da spec. Itens marcados `(derivado)` são
consequência direta desses contratos, não decisão nova.

```
deskawake/
├── LICENSE
├── README.md
├── README.en.md
├── docs/
│   └── implementation/
│       ├── spec.md
│       ├── DELIVERY_MAP.md
│       ├── design_e1.md … design_e4.md
│       ├── tasks_e1.md … tasks_e4.md
│       └── visual/                 # design aprovado + assets/preview
├── pyproject.toml                  # só [tool.pytest.ini_options] + marker "slow"
├── bin/
│   └── deskawake                   # launcher Python (calcula sys.path a partir de __file__)
├── core/
│   ├── __init__.py
│   ├── config.py                   # JSON atômico, defaults, .bak, validação de posição
│   ├── environment.py              # DE/sessão, backends, ferramentas
│   ├── inhibitors.py               # SystemdInhibit + ScreenSaverInhibit
│   ├── state.py                    # off/activating/on/deactivating/error
│   ├── daemon.py                   # barramento, objeto D-Bus, sinais, liveness
│   └── cli.py                      # on/off/toggle/status/daemon/ui
├── ui_gtk/
│   ├── __init__.py
│   ├── widget.py                   # janela 124×42, hints, drag, menu
│   └── theme.py                    # 3 variantes, auto, sinais notify::*
├── assets/
│   ├── deskawake.svg               # símbolo simbólico 22×22
│   └── spinner.svg                 # duas flechas circulares, cor herdada (derivado)
├── plasmoid/
│   ├── metadata.json               # KPackageStructure: "Plasma/Applet"
│   └── contents/
│       └── ui/
│           └── main.qml
├── data/                           # templates instalados (derivado da tarefa 11)
│   ├── org.local.DeskAwake.service
│   ├── deskawake-daemon.desktop
│   └── deskawake-widget.desktop    # só MATE
├── install.sh
├── uninstall.sh
├── verify.sh
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_config.py
    │   ├── test_environment.py
    │   ├── test_state.py
    │   ├── test_inhibitors.py
    │   ├── test_cli.py
    │   └── test_plasmoid_assets.py # estático (texto), não-GUI
    └── integration/
        ├── fakes/
        │   ├── fake_screensaver.py # FDO + MATE + GSM falsos
        │   └── fake_policyagent.py # ActiveInhibitions/HasInhibition + debounce configurável
        ├── test_daemon_contract.py
        ├── test_backend_chain.py
        ├── test_kde_optimistic.py
        └── test_lifecycle.py       # SIGTERM, Quit, PDEATHSIG, Local.Disconnected
```

Instalado no usuário (produzido pela E7, não versionado em `~/.local`):

```
~/.local/share/deskawake/{core,ui_gtk,assets,bin}
~/.local/bin/deskawake                 # wrapper com caminho absoluto
~/.local/share/dbus-1/services/org.local.DeskAwake.service
~/.config/autostart/deskawake-daemon.desktop
~/.config/autostart/deskawake-widget.desktop   # só MATE
~/.config/deskawake/config.json                # 1º uso
~/.local/state/deskawake/daemon.log (+ .log.1)
~/.local/share/plasma/plasmoids/org.local.deskawake/   # via kpackagetool6
```

---

## 3. Matriz de variação por ambiente

Consolidada da tabela “Variações por distro”. **Cada entrega abaixo cita apenas as linhas que a
afetam**, mas a matriz completa fica aqui como referência de aceite.

| Ponto | Kubuntu 26.04.1 / Plasma 6.6.7 (Wayland) | Mint 22.3 / MATE 1.26 (X11) |
|---|---|---|
| Backend de tela | `org.freedesktop.ScreenSaver` (dono `kwin_wayland`); `kscreenlocker` traduz para `PolicyAgent.AddInhibition(4)`; **sem** `GetInhibitors` | FDO **ausente** no `mate-screensaver` 1.26.2; usar `org.mate.ScreenSaver` (proxy GSM `IDLE=8`), fallback GSM |
| Confirmação do ON | `ActiveInhibitions` com `who="deskawake"`/`why="DeskAwake active"` → fallback `HasInhibition(4)` → cookie + log; **após ~5 s** | `GetInhibitors` + `IsInhibited(8)`; se o proxy MATE falhar, libera cookie MATE e cai para GSM |
| Suspensão | `--what=idle`; suspensão automática do PowerDevil é bloqueada via `ChangeScreenSettings`→`InterruptSession`; tampa/manual continuam | `--what=idle`; tampa/manual continuam; idle/DPMS cobertos pelo proxy GSM |
| Cookie | Sem ownership; inibição morre com a conexão do daemon | Sem ownership; cookie morre com a conexão; teste condicional ao backend |
| Tema | Plasmoid via `Kirigami.Theme`; cores de estado fixas | `gtk-theme` contém “dark” **ou** `gtk-application-prefer-dark-theme=true`; sem `color-scheme` |
| Fonte | Noto Sans 10 na UI; Inter/Cantarell ausentes; `fonts-inter` 4.1+ds-1 | Ubuntu 10 na UI; fallback Noto Sans; `fonts-inter` 4.0+ds-1 (opcional) |
| Instalador | `kpackagetool6` 2.0 presente; `--all` instala daemon+GTK+Plasmoid | `kpackagetool6` **ausente** nos repos; `--all` degrada com aviso; `--only-kde` falha |
| Janela | N/A (Plasmoid na camada do desktop) | EWMH `SKIP_TASKBAR`, `SKIP_PAGER`, `STICKY`, `BELOW` presentes; Marco compõe |
| GUI | Plasmoid: checklist manual | Widget: checklist manual |

---

# E1 — Esqueleto, Ambiente e Config

## E1.1 Objetivo e escopo exato

Criar a base do repositório e as duas primeiras peças puras do núcleo, **sem nenhum processo
residente**: o repo precisa passar `pytest` e conseguir responder “onde estou?” e “qual é a
configuração?” sem tocar no barramento além de consultas de leitura.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `LICENSE` | MIT (já existe; conferir conteúdo e ano) |
| `pyproject.toml` | mínimo: `requires-python = ">=3.10"`, `[tool.pytest.ini_options]` com `testpaths` e marker `slow`; **sem** build backend de distro |
| `core/__init__.py` | pacote vazio |
| `core/config.py` | leitura/escrita **atômica** de `~/.config/deskawake/config.json`; defaults; fallback `.bak`; validação de posição |
| `core/environment.py` | detecção de DE/sessão; disponibilidade de FDO/MATE/GSM/`PolicyAgent`; presença de `kpackagetool6`, `gdbus`, `systemd-inhibit` |
| `tests/unit/test_config.py` | testes de config |
| `tests/unit/test_environment.py` | testes de detecção |

**Contratos que a E1 fixa (e as demais consomem)**

```python
# core/config.py
CONFIG_PATH = Path("~/.config/deskawake/config.json").expanduser()
DEFAULT_THEME = "auto"          # "auto" | "light" | "dark"
MARGIN = 24                     # px, canto superior direito do monitor primário

def load_config() -> dict: ...
    # {"version": 1, "theme": "auto", "position": {"x": int, "y": int} | ausente}
def save_config(cfg: dict) -> None: ...          # tmp no mesmo diretório + os.replace
def default_position(workareas: list[tuple[int, int, int, int]]) -> tuple[int, int]: ...
def validate_position(pos, workareas) -> tuple[int, int]: ...
    # ponto dentro da área útil de algum monitor; senão default_position(...)

# core/environment.py
@dataclass(frozen=True)
class Environment:
    desktop: str          # XDG_CURRENT_DESKTOP (ex.: "MATE", "KDE")
    session_type: str     # XDG_SESSION_TYPE ("x11" | "wayland")
    wayland_display: str | None
    backends: dict[str, bool]     # {"fdo", "mate", "gsm", "policyagent"}
    tools: dict[str, bool]        # {"kpackagetool6", "gdbus", "systemd-inhibit"}

def detect_environment(env: Mapping[str, str] | None = None,
                       bus: "dbus.Connection" | None = None,
                       which: Callable[[str], str | None] = shutil.which) -> Environment: ...
def is_wayland(env: Environment) -> bool: ...
```

**Explicitamente fora da E1**

- `core/inhibitors.py`, `core/state.py`, `core/daemon.py`, `core/cli.py` (E2/E3).
- Qualquer UI (E4/E5).
- `install.sh`/`uninstall.sh`/`verify.sh`, `data/`, READMEs e checklists (E6).
- Criação do `config.json` no primeiro uso **pela UI**: a E1 só fornece `load_config()`/`save_config()`;
  o gatilho de primeiro uso é da E4.
- Posição do Plasmoid: **não** é persistida em `config.json` (é do Plasma, `ItemGeometries-<W>x<H>`
  no `appletsrc`). A E1 não cria campo para isso.

## E1.2 Dependências prévias

- Nenhuma. É a primeira entrega.
- Pré-requisito de ambiente: `python3`, `python3-gi`, `python3-dbus` instalados; `pytest` instalado
  **pelo desenvolvedor** via `apt` (não pelo repo).

## E1.3 Pontos críticos e armadilhas

1. **Escrita atômica de verdade:** gravar em `config.json.tmp` no **mesmo diretório** e
   `os.replace()`. Não usar `NamedTemporaryFile` em `/tmp` (cross-device falha ou não é atômico).
   Criar `~/.config/deskawake/` com `mkdir(parents=True, exist_ok=True)`.
2. **Corrupção → `.bak`, não exceção:** JSON inválido, raiz não-dict, `version` desconhecida ou
   `theme` fora de `{auto, light, dark}` ⇒ renomear para `config.json.bak` (sobrescrevendo `.bak`
   anterior) e recriar com defaults. A UI nunca deve ver stack trace por config quebrada.
3. **Defaults nunca incluem estado:** o JSON tem só `version`, `theme`, `position`. Estado sempre
   nasce `off` (decisão 5). Não adicionar `"active": true` nem similar.
4. **Validação de posição é pura:** `config.py` **não importa Gdk**. Recebe `workareas` (lista de
   `(x, y, w, h)`) da UI. Isso mantém a E1 testável sem display e evita acoplar o núcleo ao GTK.
   Regra: posição restaurada **somente** se o ponto cair dentro da área útil de algum monitor;
   caso contrário, `default_position()` (canto superior direito, margem 24 px).
5. **Detecção não pode acordar serviços:** verificar backend com `NameHasOwner` (leitura barata).
   **Não** chamar método do backend na detecção — isso pode auto-startar `mate-screensaver` ou
   `kscreenlocker`. Mesma regra do `status` da CLI (decisão 6).
6. **Wayland é detectado, não julgado:** `environment.py` só informa `session_type`/`wayland_display`.
   O bloqueio de `ui` é da E3. Não colocar a regra de recusa aqui.
7. **`kpackagetool6` ausente é normal** (Mint 22.3): `tools["kpackagetool6"] is False` é resultado
   válido, não erro. Nada de `sys.exit` em `environment.py`.
8. **`systemd-inhibit` é ferramenta, não backend:** pertence a `tools`, nunca a `backends`.
9. **`pytest` mínimo:** não declarar dependências de runtime no `pyproject.toml`; não criar
   `setup.py`/`setup.cfg`; não usar `hatchling`/`setuptools` como build backend. O arquivo existe
   para `[tool.pytest.ini_options]` e `requires-python`.

## E1.4 Critérios de aceite e verificação

**Automático**

```bash
python3 -m pytest tests/unit/test_config.py tests/unit/test_environment.py -v
```

Deve cobrir, no mínimo:

- [ ] `load_config()` sem arquivo ⇒ defaults (`version=1`, `theme="auto"`, sem `position`), **sem**
      criar arquivo em disco.
- [ ] `save_config()` + `load_config()` round-trip; nenhum `.tmp` remanescente no diretório.
- [ ] JSON corrompido (`"{oops"`) ⇒ `config.json.bak` criado, defaults retornados, `config.json`
      novo válido.
- [ ] `theme` inválido (`"blue"`) ⇒ tratado como corrupção/`auto` conforme regra do item 2, com
      `.bak`.
- [ ] `validate_position` dentro da área útil ⇒ mantém; fora (monitor desconectado) ⇒
      `default_position`; múltiplos monitores ⇒ aceita se cair em qualquer um.
- [ ] `default_position` com workarea `(0, 0, 1920, 1050)` ⇒ `x = 1920 - 124 - 24`,
      `y = 24` (124×42 é a pílula; margem 24).
- [ ] `detect_environment` com `XDG_CURRENT_DESKTOP=MATE`, `XDG_SESSION_TYPE=x11` ⇒
      `desktop="MATE"`, `session_type="x11"`, `is_wayland() is False`.
- [ ] `detect_environment` com `XDG_SESSION_TYPE=wayland` + `WAYLAND_DISPLAY=wayland-0` ⇒
      `is_wayland() is True`.
- [ ] `which` injetado sem `kpackagetool6` ⇒ `tools["kpackagetool6"] is False` e **nenhuma**
      exceção.
- [ ] `bus` fake sem dono de `org.mate.ScreenSaver` ⇒ `backends["mate"] is False`; com dono ⇒ `True`.
      Nenhum `call_blocking` de método de backend é executado (asserção sobre o fake).

**Manual (rápido)**

- [ ] `python3 -c "from core.config import load_config; print(load_config())"` roda no Mint e no Kubuntu.
- [ ] `python3 -c "from core.environment import detect_environment as d; print(d())"` mostra
      `MATE/x11` no Mint e `KDE/wayland` no Kubuntu.

---

# E2 — Núcleo de inibição, máquina de estados e daemon

## E2.1 Objetivo e escopo exato

Entregar o **coração funcional**: os dois inibidores, a máquina de estados all-or-nothing e o
daemon D-Bus que as orquestra. Ao fim da E2 existe um processo que pode ser iniciado, recebe
`SetActive(true/false)`, emite `StateChanged` e libera tudo ao sair — **sem** CLI e **sem** UI.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `core/inhibitors.py` | `SystemdInhibit` e `ScreenSaverInhibit` (cadeia FDO → MATE → GSM + confirmação KDE) |
| `core/state.py` | máquina `off/activating/on/deactivating/error`, all-or-nothing, `last_error` |
| `core/daemon.py` | barramento, objeto D-Bus, sinais, liveness, shutdown, log rotativo |
| `tests/unit/test_inhibitors.py` | inibidores com fakes |
| `tests/unit/test_state.py` | máquina de estados |
| `tests/integration/fakes/fake_screensaver.py` | FDO/MATE/GSM falsos |
| `tests/integration/fakes/fake_policyagent.py` | `ActiveInhibitions`/`HasInhibition` com debounce configurável |
| `tests/integration/test_daemon_contract.py` | contrato D-Bus |
| `tests/integration/test_backend_chain.py` | ordem e fallback |
| `tests/integration/test_kde_optimistic.py` | ON otimista, verificação, cancelamento |
| `tests/integration/test_lifecycle.py` | SIGTERM/SIGINT/`Quit`/`PDEATHSIG`/`Local.Disconnected` |

**Contratos que a E2 fixa**

```python
# core/inhibitors.py
class SystemdInhibit:
    def __init__(self, reason: str = "DeskAwake active", who: str = "DeskAwake",
                 confirm_delay: float = 0.2) -> None: ...
    def start(self) -> None: ...   # levanta InhibitError com stderr se o filho morrer
    def stop(self) -> None: ...    # SIGTERM no grupo → espera 2 s → SIGKILL no grupo
    @property
    def alive(self) -> bool: ...

class ScreenSaverInhibit:
    def __init__(self, bus, *, who: str = "deskawake",
                 why: str = "DeskAwake active",
                 debounce: float = 5.0, verify_delay: float = 6.0) -> None: ...
    def acquire(self) -> None: ...     # define backend/path/cookie
    def confirm(self) -> bool: ...     # confirmação síncrona do backend escolhido
    def release(self) -> None: ...     # UnInhibit (FDO/MATE) ou Uninhibit (GSM)
    backend: str | None                # "fdo" | "mate" | "gsm"
    cookie: int | None

# core/state.py
class State(Enum): OFF, ACTIVATING, ON, DEACTIVATING, ERROR
class StateMachine:
    def __init__(self, on_change: Callable[[str], None],
                 verify_delay: float = 6.0) -> None: ...
    state: str            # "off" | "activating" | "on" | "deactivating" | "error"
    last_error: str
    def activate(self) -> str: ...
    def deactivate(self) -> str: ...
    def toggle(self) -> str: ...
    def cancel_pending_verification(self) -> None: ...
```

**D-Bus exposto (exatamente)**

| Membro | Assinatura | Semântica |
|---|---|---|
| `SetActive` | `b → s` | Aplica e retorna o estado resultante |
| `Toggle` | `→ s` | Inverte e retorna |
| `GetState` | `→ s` | Estado atual, não altera nada |
| `GetLastError` | `→ s` | Motivo do último erro; vazio se não houver |
| `Quit` | `→ ()` | Desativa e encerra |
| `StateChanged` | `s` | Emitido a cada mudança de estado |

**Explicitamente fora da E2**

- `core/cli.py`, `bin/deskawake` (E3).
- Widget GTK, tema, assets (E4); Plasmoid (E5).
- `data/*.service` e autostart: templates e instalação são da E6. O daemon **deve** funcionar
  quando iniciado por ativação D-Bus, mas o arquivo que a habilita não é entregue aqui.
- `install.sh`/`uninstall.sh`/`verify.sh`, READMEs (E6).

## E2.2 Dependências prévias

- **E1 concluída** (`core/config.py` não é usado pelo daemon — o estado não persiste —, mas
  `core/environment.py` informa DE/sessão e disponibilidade inicial; a árvore e o `pytest`
  configurado vêm da E1).
- Ambiente: `systemd-inhibit` presente; barramento de sessão acessível; `dbus-run-session` presente
  (validado nas duas máquinas).

## E2.3 Pontos críticos e armadilhas

1. **Ordem interna do `activate()`:** (a) sobe `systemd-inhibit`; (b) espera **200 ms** e confirma
   que o filho continua vivo — se saiu, lê `stderr` e falha; (c) adquire o inibidor de tela na ordem
   FDO → MATE → GSM, na **mesma conexão** do daemon, guardando backend/path/cookie. Inverter (b) e
   (c) deixa o sistema com inibidor de tela sem backstop.
2. **`--what=idle`, nunca `sleep`.** `sleep` bloquearia tampa e suspensão manual — comportamento
   explicitamente proibido (decisões 1, 11, 25).
3. **Grupo de processos + `PR_SET_PDEATHSIG`:** o filho roda em grupo próprio (`start_new_session`
   ou `setsid` no `preexec_fn`) e recebe `prctl(PR_SET_PDEATHSIG, SIGTERM)`. Matar só o PID deixa
   `sleep infinity` órfão. `stop()` = SIGTERM **no grupo** → até **2 s** → SIGKILL **no grupo**.
4. **Confirmação MATE:** `GetInhibitors` contém a aplicação **e**, se o GSM existir,
   `IsInhibited(8) == true` (o MATE cria proxy GSM `IDLE=8`). Se o proxy não confirmar: libera o
   cookie MATE e tenta o GSM **diretamente**. Nunca adquirir GSM adicionalmente quando o MATE foi
   confirmado (duplicaria cookies).
5. **GSM:** `Inhibit(app, 0, reason, 8)` — `toplevel_xid=0`, `flags=IDLE (8)`. O método de liberação
   é **`Uninhibit` com “i” minúsculo**; FDO e MATE usam `UnInhibit`.
6. **FDO não tem `GetInhibitors`:** no MATE/FDO puro, o cookie retornado é a confirmação disponível.
   No KDE o cookie é imediato mas **não** é confirmação real — ver item 7.
7. **KDE — nunca chamar `PolicyAgent` para inibir.** `org.freedesktop.ScreenSaver.Inhibit` já vira
   `AddInhibition(ChangeScreenSettings=4)` no `kscreenlocker`; chamar o `PolicyAgent` duplicaria
   cookies. O `PolicyAgent` é **somente leitura**: `ActiveInhibitions` (`a(ssssu)` =
   `(what, who, why, mode, flags)`, casar `who="deskawake"`/`why="DeskAwake active"` e
   `flags & 3 == 3`), fallback `HasInhibition(4)`, senão cookie + **aviso em log**.
8. **Debounce de ~5 s é real:** o PowerDevil só aplica o `AddInhibition` após ~5 s. O ON é
   **otimista**: entra em `on` com cookie + filho vivo e agenda `GLib.timeout_add_seconds(6, ...)`.
   Não bloquear o `SetActive` esperando 6 s.
9. **Cancelamento da verificação:** `SetActive(false)` durante a janela de ~6 s **cancela o timer**
   e segue a desativação normal, sem passar por `error`. `cancel_pending_verification()` deve ser
   idempotente.
10. **Verificação que falha só rebaixa se ainda estiver `on`:** se o usuário já desligou, não emitir
    `StateChanged("error")`.
11. **`active`/`deactivating` são internos:** o barramento só conhece `on/off/error`. Não adicionar
    estado de verificação (decisão 33).
12. **Liveness sem rajada:** `NameOwnerChanged` de `org.freedesktop.ScreenSaver`,
    `org.mate.ScreenSaver`, `org.gnome.SessionManager` **e** `org.kde.Solid.PowerManagement`.
    Queda com `on` ⇒ `error` + `StateChanged`. Retorno ⇒ descarta cookie antigo, re-adquire
    (`ScreenSaver.Inhibit` novo) e agenda nova verificação de ~6 s ⇒ `on`. Falha repetida
    **permanece em `error`** com motivo em `GetLastError()`; **não** reiniciar em loop.
13. **Preservar o filho do `systemd-inhibit`:** queda/retorno do PowerDevil **não** reinicia o filho.
    Só `SetActive(false)`, `Quit()` e shutdown o encerram.
14. **`Local.Disconnected`:** no logout do Plasma o barramento morre. **Não fazer nenhuma chamada
    D-Bus** nesse caminho (nem `UnInhibit`): encerrar o filho (SIGTERM → 2 s → SIGKILL no grupo),
    `loop.quit()`, sair **0**. `org.kde.Shutdown`/`plasma-login-session` são opcionais, nunca
    requisito.
15. **`DO_NOT_QUEUE`:** adquirir `org.local.DeskAwake` com `DBUS_NAME_FLAG_DO_NOT_QUEUE`; se já
    houver dono, **sair 0** (segunda instância não é erro).
16. **`error` é recuperável:** `SetActive(false)` a partir de `error` limpa de forma **idempotente**
    (descarta cookie antigo, remove filho se existir) e vai para `off`.
17. **All-or-nothing:** falha em qualquer passo libera o que já foi adquirido, grava `last_error`,
    vai para `error`, emite `StateChanged("error")`. Nunca deixar inibidor de tela órfão sem filho
    ou vice-versa.
18. **Timeout injetável:** `debounce`/`verify_delay`/`confirm_delay` são parâmetros com padrão
    **5 s / 6 s / 0,2 s**; testes restauram no teardown (`monkeypatch`) para não vazar estado entre
    testes. O ciclo real só roda com `@pytest.mark.slow`.
19. **`PDEATHSIG` é Linux-only e não testável por unit test:** o teste é de integração (matar o pai
    com `SIGKILL` e verificar que o filho desaparece).
20. **Log:** abrir `~/.local/state/deskawake/daemon.log`; antes de escrever, se > **256 KB**,
    rotacionar para `daemon.log.1` (sobrescrevendo o anterior). Não logar credenciais (não há).

## E2.4 Critérios de aceite e verificação

**Automático — unitário**

```bash
python3 -m pytest tests/unit/test_inhibitors.py tests/unit/test_state.py -v
```

- [ ] Comando do `SystemdInhibit` contém exatamente `--what=idle`, `--mode=block`,
      `--who=DeskAwake` e **não** contém `sleep` em `--what`.
- [ ] Filho que morre antes de 200 ms ⇒ `start()` levanta erro contendo o `stderr`.
- [ ] `stop()` envia SIGTERM ao **grupo** e, se não morrer em 2 s, SIGKILL ao grupo (fake de
      processo registra a sequência).
- [ ] Cadeia: FDO disponível ⇒ backend `fdo`; FDO ausente + MATE disponível ⇒ `mate`; ambos ausentes
      ⇒ `gsm` com `xid=0` e `flags=8`.
- [ ] MATE confirmado ⇒ **nenhuma** chamada de `Inhibit` no GSM.
- [ ] MATE cujo `IsInhibited(8)` permanece `false` ⇒ `UnInhibit` do cookie MATE e aquisição GSM.
- [ ] `release()` usa `UnInhibit` em FDO/MATE e `Uninhibit` em GSM (asserção sobre o fake).
- [ ] KDE: `ActiveInhibitions` com `who`/`why` corretos ⇒ `confirm() is True`; ausente +
      `HasInhibition(4) == True` ⇒ `True`; ambos ausentes ⇒ `True` com aviso de log (cookie).
- [ ] Máquina de estados: `off → activating → on`; falha no meio ⇒ `error` + `last_error`;
      `error + deactivate` ⇒ `off`; `toggle` respeita `on`/`off`/`error`.
- [ ] Verificação agendada que falha com estado ainda `on` ⇒ `error`; com estado já `off` ⇒
      **nenhum** `StateChanged` novo.

**Automático — integração (barramento privado)**

```bash
dbus-run-session -- python3 -m pytest tests/integration -v
```

- [ ] `SetActive(true)` ⇒ `GetState() == "on"`; `systemd-inhibit --list` contém `deskawake`.
- [ ] `SetActive(false)` ⇒ `GetState() == "off"`; lock ausente.
- [ ] `Toggle()` retorna o novo estado e é idêntico a `SetActive(not current)`.
- [ ] `GetLastError()` vazio em operação normal; preenchido após falha forçada.
- [ ] `StateChanged` é emitido em cada transição, com apenas `on|off|error`.
- [ ] ON otimista: com fake de `PolicyAgent` em debounce longo, `GetState()` já é `on` **antes** da
      confirmação.
- [ ] Rota (i): confirmação dentro da janela ⇒ permanece `on`, sem `error`.
- [ ] Rota (ii): confirmação falha ⇒ `error` + `StateChanged("error")`.
- [ ] Rota (iii): `SetActive(false)` durante a janela ⇒ `off`, timer cancelado, **sem** `error`.
- [ ] Queda do fake `org.kde.Solid.PowerManagement` com `on` ⇒ `error`; retorno ⇒ `on` após nova
      verificação, **sem** mais de uma tentativa por evento (contador do fake).
- [ ] Filho do `systemd-inhibit` continua o **mesmo PID** durante a queda/retorno do PowerDevil.
- [ ] `SIGTERM` libera os dois inibidores e sai 0; `SIGINT` idem.
- [ ] `Quit()` libera, encerra e o nome some do barramento.
- [ ] `PDEATHSIG`: `SIGKILL` no daemon ⇒ nenhum `systemd-inhibit` órfão.
- [ ] `Local.Disconnected`: fechar o barramento ⇒ processo sai 0 **sem** tentativa de `UnInhibit`
      (fake registra zero chamadas após o fechamento).
- [ ] Segunda instância com o nome ocupado ⇒ sai **0** sem tomar o nome.
- [ ] Rotação: escrever > 256 KB ⇒ existe `daemon.log.1` e `daemon.log` recomeçou.

**Opcional (opt-in)**

```bash
python3 -m pytest tests/integration -m slow -v
```

- [ ] Ciclo real de ~5–6 s com `PolicyAgent` de verdade (Kubuntu) fecha em `on` e depois `off`.

**Manual rápido (Kubuntu)**

```bash
systemd-inhibit --what=idle --mode=block --who=DeskAwake --why=probe sleep 3
systemd-inhibit --list | grep -i deskawake   # aparece durante os 3 s
```

## E2.5 Decisões de design confirmadas (2026-11-20)

A spec e este mapa deixavam pontos abertos que mudavam contratos da E2. Eles foram resolvidos com
o usuário antes do design e **não alteram o produto** da `spec.md` — apenas fixam a leitura
adotada. O design completo está em `design_e2.md` (versionado em `docs/implementation/`),
**aprovado em 2026-11-20**.

| # | Tema | Decisão confirmada |
|---|---|---|
| 1 | Injeção no `StateMachine` | acrescentar parâmetros **keyword-only opcionais** `systemd`, `screen`, `schedule`, `cancel`; `on_change`/`verify_delay` continuam posicionais. `activate()` sem inibidores injetados é erro de programação (`RuntimeError`). |
| 2 | Degradação do `confirm()` no KDE | degradar para cookie (`True` + aviso) **somente** quando o mecanismo não existir (propriedade/método/interface indisponível). `ActiveInhibitions`/`HasInhibition` disponíveis e negativos ⇒ `confirm() is False` (rota ii); se `ActiveInhibitions` existe sem a entrada, ela é autoritativa e o resultado é `False` mesmo sem `HasInhibition`. `PolicyAgent` ausente do barramento ⇒ cookie (não é KDE). |
| 3 | Liveness | reagir apenas ao backend ativo e aos proxies relevantes: GSM quando o backend é MATE; `org.kde.Solid.PowerManagement` quando o backend é FDO. Os quatro nomes continuam observados; os demais eventos são ignorados. O daemon mantém `_lost` e só tenta re-adquirir quando **todos** os nomes relevantes que caíram voltarem: **uma** tentativa por esvaziamento, sem rajada. |
| 4 | Queda do GSM com backend `gsm` | tratar como fim de sessão (somente com estado público `on`): parar só o filho do `systemd-inhibit`, `loop.quit()`, exit **0**, sem `Uninhibit` (o serviço morreu). Em `error`, não encerra; o `Local.Disconnected` cobre o logout. |
| 5 | `debounce` × `verify_delay` | o `StateMachine` agenda a verificação em `verify_delay`; `ScreenSaverInhibit.confirm()` é a checagem síncrona; `debounce` é a idade mínima desde o acquire para aceitar um negativo (antes disso, otimista `True`). A verificação só é agendada quando `needs_verification` (FDO + `PolicyAgent`). |
| 6 | `last_error` / `Toggle` / reemissão | `last_error` existe só em `error` e é limpo ao ir para `on`/`off`; `GetLastError()` devolve `""` fora de `error`. `Toggle` em `error` tenta **ativar**. Falha repetida atualiza o motivo sem reemitir `StateChanged("error")` (o estado não mudou). |
| 7 | Testes em subprocesso | `core.daemon.main(*, verify_delay=..., debounce=..., confirm_delay=..., log_path=...)` com defaults de produção; os testes usam um runner `python3 -c`. Sem flags de CLI nem env vars novas. |
| 8 | `Local.Disconnected` | `bus.set_exit_on_disconnect(False)` é obrigatório logo após conectar (o default do dbus-python chama `_exit(1)`); no caminho do sinal, **nenhuma** chamada D-Bus, apenas parar o filho, `loop.quit()` e exit 0. |
| 9 | Erro de liveness × all-or-nothing | queda de backend com `on` ⇒ `error` **preservando** o filho do `systemd-inhibit`; falha de ativação/verificação ⇒ `error` **liberando tudo** (all-or-nothing). Só `SetActive(false)`, `Quit`, fim de sessão ou shutdown param o filho. |
| 10 | `release()` e liveness | `release()` limpa o `cookie` e mantém `backend`/`path` como “último backend conhecido”, para o filtro de liveness continuar sabendo o que observar. `acquire()` sobrescreve os três. |
| 11 | Testes do `systemd-inhibit --list` | filtrar pelo **PID do filho** do daemon de teste (obtido por `ps --ppid`), não pelo `WHO` global, para não colidir com um DeskAwake real da máquina. |
| 12 | Mensagens | `last_error` e log em **pt-BR**; `who="deskawake"`/`why="DeskAwake active"` (tela) e `--who=DeskAwake` (`systemd-inhibit`) permanecem fixos em inglês, como na spec. |

**Efeito nos gates:** nenhum critério novo. Os critérios da E2.4 passam a ser lidos com as
decisões acima; em particular, a rota (ii) do KDE exige mecanismo disponível e negativo, a
recuperação de liveness tenta uma vez por esvaziamento e `Local.Disconnected` só sai 0 com
`exit_on_disconnect` desativado.

---

# E3 — CLI e Launcher

## E3.1 Objetivo e escopo exato

Dar ao usuário e aos scripts um ponto de entrada único (`deskawake`) que fala com o daemon da E2,
com códigos de saída estáveis, guarda de Wayland e instância única da UI. A E3 **não** desenha
nada: entrega o roteamento e a política de acesso.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `core/cli.py` | subcomandos, códigos de saída, guarda Wayland, single-instance da UI, `main()` |
| `bin/deskawake` | launcher executável; resolve `sys.path` a partir de `__file__` |
| `tests/unit/test_cli.py` | testes com daemon/barramento falsos |

**Contrato da CLI (exato)**

```
deskawake on|off|toggle|status
deskawake daemon
deskawake ui [--force]
```

| Comando | Comportamento | Saída |
|---|---|---|
| `on` / `off` / `toggle` | `SetActive(true/false)` / `Toggle()` | imprime o estado resultante |
| `status` | `NameHasOwner` **antes** de `GetState`; **não** dispara auto-start | imprime `on\|off\|error`; exit **0** = on, **1** = off, **3** = daemon inacessível (neste caso imprime `off` e a mensagem “daemon inacessível” em `stderr`, sem chamar `GetState`) |
| `daemon` | inicia o daemon em foreground (delega a `core.daemon`) | exit 0 em saída limpa |
| `ui [--force]` | recusa Wayland salvo `--force`/`DESKAWAKE_FORCE_UI=1`; single-instance via `org.local.DeskAwake.Ui` | segunda invocação sai **0** |

**Explicitamente fora da E3**

- Implementação da janela GTK (E4) e do Plasmoid (E5). A E3 entrega o **guard + orquestração +
  single-instance** e chama `ui_gtk.widget.main()`; o teste da E3 usa um fake/monkeypatch e **não
  abre janela**. Até a E4 existir, `ui` só é aceitável em teste.
- Instalação do launcher em `~/.local/bin` e do `.service` (E6). `bin/deskawake` no repo é o
  artefato-fonte; o wrapper absoluto é gerado pelo `install.sh`.
- Qualquer regra de tema/aparência.

## E3.2 Dependências prévias

- **E2 concluída**: métodos `SetActive`/`Toggle`/`GetState`/`GetLastError`/`Quit` e sinal
  `StateChanged` funcionando; nome `org.local.DeskAwake` adquirível.
- **E1**: `core/environment.py` para detectar Wayland.

## E3.3 Pontos críticos e armadilhas

1. **`status` nunca acorda o daemon.** `NameHasOwner` primeiro; só chamar `GetState` se houver dono.
   Sem dono ⇒ exit **3**, `stdout` `off` (não há inibição ativa) e aviso “daemon inacessível” em
   `stderr`, **sem** `StartServiceByName` — o `.service` de D-Bus existe para ativação sob demanda e
   `status` não deve usá-la (decisão 6).
2. **Códigos de saída são contrato:** `0` on, `1` off, `3` inacessível — **nunca** reutilizar `3`
   para estado `error`. A spec não fixa código para `error`; a escolha local (documentada no
   `--help` e fixada em teste) é **exit 1**, imprimindo `error` em `stdout`: `error` não é `on`, e o
   código `1` continua significando “não ligado”. Não introduzir `2` nem um quarto código.
3. **Guarda Wayland:** recusar se `XDG_SESSION_TYPE=wayland` **ou** `WAYLAND_DISPLAY` definido.
   Escape: `--force` **ou** `DESKAWAKE_FORCE_UI=1`. Mensagem clara apontando o Plasmoid no KDE.
   A checagem usa `environment.py`, não `os.environ` espalhado.
4. **Single-instance da UI:** `RequestName("org.local.DeskAwake.Ui", DO_NOT_QUEUE)`; se já houver
   dono, sair **0** silenciosamente (não é erro para o usuário clicar duas vezes).
5. **Launcher portátil:** `bin/deskawake` deve funcionar tanto no repo (`./bin/deskawake`) quanto
   instalado (`~/.local/share/deskawake/bin/deskawake`). Calcular o pai do pai de `__file__` e
   inserir no `sys.path`; **não** depender do CWD nem de `PYTHONPATH`. Shebang `#!/usr/bin/env python3`.
6. **`daemon` em foreground:** não daemonizar (sem double-fork). O daemon é residente de sessão e o
   autostart cuida do resto; daemonizar quebraria `systemd --user`/logs.
7. **Sem `argparse` exagerado:** subcomandos fixos; `--force` só em `ui`. Não inventar flags.
8. **Falha de conexão não é stack trace:** barramento indisponível ⇒ mensagem em `stderr` e exit
   ≠ 0 (para `on/off/toggle`), nunca traceback cru.

## E3.4 Critérios de aceite e verificação

**Automático**

```bash
python3 -m pytest tests/unit/test_cli.py -v
```

- [ ] `status` com daemon ausente (fake `NameHasOwner=false`) ⇒ exit **3** e **zero** chamadas a
      `GetState` e a `StartServiceByName` (asserção sobre o fake).
- [ ] `status` com `GetState()=="on"` ⇒ exit **0**, stdout `on`; `"off"` ⇒ exit **1**, stdout `off`;
      `"error"` ⇒ exit **1**, stdout `error`.
- [ ] `on`/`off`/`toggle` chamam o método certo e imprimem o retorno.
- [ ] `ui` com `XDG_SESSION_TYPE=wayland` ⇒ exit ≠ 0, mensagem menciona `--force`, e
      `ui_gtk.widget.main` **não** é chamado.
- [ ] `ui` com `WAYLAND_DISPLAY` definido e sem `--force` ⇒ recusa.
- [ ] `ui --force` ⇒ chama `main()` (fake), sem abrir janela.
- [ ] `DESKAWAKE_FORCE_UI=1` equivale a `--force`.
- [ ] Segunda instância da UI (`RequestName` retorna `EXISTS`) ⇒ exit **0**, `main()` não chamado.
- [ ] `python3 bin/deskawake --help` roda a partir da raiz e a partir de `/tmp` (caminho absoluto),
      sem `PYTHONPATH`.

**Manual (rápido, Mint)**

```bash
deskawake status; echo $?        # 3 se o daemon não estiver rodando
deskawake daemon &               # em foreground em outro terminal
deskawake on; deskawake status; echo $?
deskawake off; deskawake status; echo $?
deskawake ui                     # abre (após E4); no Kubuntu deve recusar
```

---

# E4 — UI GTK3 (MATE / X11)

## E4.1 Objetivo e escopo exato

Entregar o widget GTK3 que vive na área de trabalho do MATE: pílula 124×42 sem decoração, atrás das
janelas, fora de `Alt+Tab`/barra/pager, arrastável, com menu completo e tema reativo. É a única UI
do Mint e a única forma de validar visualmente o núcleo no X11.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `ui_gtk/widget.py` | janela, hints EWMH, arrasto, toggle, menu, tooltip, posição, conexão D-Bus |
| `ui_gtk/theme.py` | CSS das 3 variantes, `auto`, sinais `notify::*`, fallback opaco |
| `assets/deskawake.svg` | símbolo simbólico 22×22 (“círculo aberto com ponto de luz”) |
| `assets/spinner.svg` | duas flechas circulares, cor herdada do texto (derivado) |

**Comportamento exigido**

- **Geometria:** 124×42, cantos arredondados, borda fina, sem gradiente/sombra; símbolo 22×22 com
  9 px de respiro; nome `DeskAwake` 12 px semibold; toggle 32×18. Símbolo e nome **neutros**;
  o toggle é o único indicador de estado.
- **Camada Z:** `keep_below` + `skip_taskbar` + `skip_pager` + `stick()` aplicados **antes** de
  `show_all()` e reforçados em `realize`/`map`. **Nunca** `WindowTypeHint.DESKTOP` (quebra
  clique/arrasto no Marco).
- **Arrasto:** superfície inteira, threshold **5 px**; alterna só se o `press` começou no toggle;
  movimento > 5 px suprime `state-set`/`activate` **até o release**.
- **Menu:** `Ativar/Desativar` (rótulo dinâmico) · `Tema ▸` (`auto`/`light`/`dark`) ·
  `Iniciar com o sistema ☑` · `Sair`.
- **Tema:** `auto` = dark se `gtk-theme` contiver “dark” (**case-insensitive**) **ou**
  `gtk-application-prefer-dark-theme=true`; sinais `notify::gtk-theme-name` e
  `notify::gtk-application-prefer-dark-theme`; **nunca** alterar o `prefer-dark` global.
- **Fonte:** stack única com aspas e `sans-serif` no fim; **sem** `@font-face`.
- **Translucidez:** só se `Gdk.Screen.is_composited()`; sem compositor, superfície **opaca** e
  legível.
- **Progresso:** spinner de duas flechas neutro **apenas** durante `Toggle`/`SetActive` em voo,
  bloqueando o toggle; sem âmbar, sem animação contínua.
- **Erro:** tooltip com `GetLastError()`; estado vermelho.
- **Posição:** lida/gravada via `core/config.py`, validada contra as workareas atuais do Gdk.
- **Daemon ausente:** `NameOwnerChanged` de `org.local.DeskAwake` ⇒ estado visual `off` imediato;
  próxima ação reativa via `.service`.

**Explicitamente fora da E4**

- Wayland (bloqueado pela E3; `--force` é só depuração).
- Plasmoid e qualquer QML (E5).
- Instalação/autostart/`.desktop` (E6).
- Persistência da posição do Plasmoid (não existe; é do Plasma).
- Testes automatizados de GUI (a spec proíbe; validação é checklist manual).

## E4.2 Dependências prévias

- **E2** (contrato D-Bus, `StateChanged`, `GetLastError`).
- **E3** (`bin/deskawake ui`, guarda Wayland, single-instance).
- **E1** (`core/config.py`, `core/environment.py`).
- Ambiente Mint: GTK 3.24.41, PyGObject 3.48.2, Marco compondo, Caja com ícones na área de trabalho.

## E4.3 Pontos críticos e armadilhas

1. **Ordem dos hints é o bug nº 1:** `keep_below`/`skip_taskbar`/`skip_pager`/`stick()` **antes**
   de `show_all()`; reforçar em `realize`/`map`. Aplicar depois faz o WM ignorar.
2. **`DESKTOP` hint proibido no Marco:** quebra clique e arrasto. Usar `UTILITY`/janela normal com
   os hints acima.
3. **`Gtk.Switch` + drag:** conectar `state-set` e retornar `True` enquanto `dragged == True`;
   resetar a flag **somente** no `button-release`. Sem isso o switch alterna ao soltar o mouse.
   O mesmo vale para `activate` (teclado/clique).
4. **Threshold de 5 px medido do `press`:** guardar o ponto inicial no `button-press` da superfície;
   ao passar de 5 px, marcar `dragged=True` e iniciar `begin_move_drag`. Clique curto no toggle
   alterna; clique curto fora do toggle não faz nada.
5. **`stick()` e workspaces:** a máquina Mint de validação tem 1 workspace; o teste real exige criar
   um segundo. Não substituir `stick()` por `set_workspace`.
6. **Tema `auto` sem efeito colateral:** ler `Gtk.Settings.get_default().props.gtk_theme_name` e
   `gtk_application_prefer_dark_theme`; **jamais** escrever `prefer-dark` no settings global.
   MATE 1.26 não tem `color-scheme` — não consultar.
7. **Sinais de tema:** conectar `notify::gtk-theme-name` e
   `notify::gtk-application-prefer-dark-theme` e reaplicar o CSS; alternar `Mint-Y` ↔ `Mint-Y-Dark`
   deve atualizar sem reiniciar.
8. **`@font-face` não existe em GTK3:** tentar embutir fonte gera `unknown @ rule` (GTK 3.24.41).
   Usar a stack com aspas e `sans-serif` no fim; Inter é opcional.
9. **Compositor:** `is_composited()` decide entre `rgba()` translúcido (82–90%) e cor sólida.
   Não usar `set_opacity()` na janela inteira (apaga o texto).
10. **Spinner só na chamada em voo:** ao clicar, desabilitar o toggle e iniciar o spinner; ao
    receber a resposta (ou erro), parar e reabilitar. Não animar em repouso. Sem âmbar (decisão 33).
11. **`Sair` = kill switch:** `SetActive(false)` → `Quit()` → fechar a UI. Se o daemon já caiu, não
    travar: o `NameOwnerChanged` já levou o visual para `off`; apenas fechar.
12. **Menu dinâmico:** rótulo `Desativar` quando `on`, `Ativar` quando `off`/`error`. `Tema ▸` marca
    o item ativo. `Iniciar com o sistema` lê/escreve o `.desktop` de autostart — se o arquivo ainda
    não existe (E6), criar/remover de forma idempotente **sem** falhar.
13. **Tooltip de erro:** usar `GetLastError()` no `StateChanged("error")`; limpar ao sair de `error`.
14. **Não bloquear o loop GTK:** chamadas D-Bus síncronas curtas são aceitáveis, mas a UI nunca pode
    esperar os 6 s de verificação. O spinner da UI é local; o estado `on` chega otimista.
15. **Posição:** salvar no `button-release` do arrasto (não a cada movimento) e somente se a posição
    validar contra as workareas; ao restaurar, se o ponto não cair em nenhum monitor, voltar ao
    padrão (canto superior direito, 24 px).

## E4.4 Critérios de aceite e verificação

**Automático (o que é possível sem GUI)**

```bash
python3 -m pytest tests/unit -q
python3 -c "import ui_gtk.widget, ui_gtk.theme"   # importa sem display? usar GDK_BACKEND=dummy se necessário
```

- [ ] `theme.py` expõe uma função pura de decisão `resolve_variant(theme, gtk_theme_name,
      prefer_dark) -> "light"|"dark"` coberta por testes: `"Mint-Y-Dark"` ⇒ dark;
      `"my-darkish"` ⇒ dark (case-insensitive); `prefer_dark=True` com tema claro ⇒ dark;
      `theme="light"` força light; `theme="dark"` força dark.
- [ ] CSS gerado **não** contém `@font-face`; contém a stack com `sans-serif` no fim.
- [ ] CSS não escreve `gtk-application-prefer-dark-theme` (asserção textual).
- [ ] `assets/deskawake.svg` é SVG válido e usa `currentColor`/`fill` simbólico (sem cores fixas de
      estado).
- [ ] Nenhum import de `Gdk` em `core/`.

**Manual — Mint 22.3 MATE/X11 (obrigatório; da spec)**

- [ ] Abre no canto superior direito, 24 px de margem, sem decoração.
- [ ] Não aparece em `Alt+Tab`, barra de tarefas nem pager; aparece em todos os workspaces
      (criar um segundo workspace).
- [ ] Fica atrás de janelas normais e visível com a área de trabalho à mostra; “Mostrar área de
      trabalho” do Caja não o quebra.
- [ ] Arrasta de qualquer ponto, inclusive sobre o toggle; arrastar > 5 px **não** alterna.
- [ ] Clique no toggle alterna; clique fora não altera.
- [ ] Durante `Toggle`/`SetActive`: spinner de duas flechas, toggle bloqueado, sem âmbar.
- [ ] Compositor do Marco desligado ⇒ superfície sólida e legível; ligado ⇒ translucidez.
- [ ] Posição sobrevive a logout; desconectar monitor externo volta ao padrão.
- [ ] Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sair`.
- [ ] `Sair` com ON libera imediatamente (`systemd-inhibit --list` sem `deskawake`;
      `GetInhibitors` vazio; `IsInhibited(8)` falso).
- [ ] `kill -9` no daemon não deixa `systemd-inhibit` órfão nem tela presa.
- [ ] Com idle/lock do `mate-screensaver` habilitados, ON impede blanking/bloqueio; OFF restaura.
- [ ] `Mint-Y` ↔ `Mint-Y-Dark` atualiza o tema sem reiniciar.
- [ ] Com Inter ausente, usa Ubuntu/Noto Sans sem erro.
- [ ] `error` (ex.: matar `mate-screensaver`) mostra tooltip e libera o `systemd-inhibit`.
- [ ] Suspensão manual funciona com ON (teste destrutivo, opcional).
- [ ] Fechar a tampa suspende com ON (requer notebook; a máquina Mint é desktop).

---

# E5 — Plasmoid KDE Plasma 6.6

## E5.1 Objetivo e escopo exato

Entregar o Plasmoid nativo do Plasma 6.6 que substitui o widget GTK no Kubuntu/Wayland: mesma pílula,
mesmo contrato D-Bus, transporte nativo, arrasto nativo e menu enxuto. Nenhuma linha de QML pode
depender de `Plasma5Support`, `gdbus` ou polling.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `plasmoid/metadata.json` | metadados do pacote e requisito de Plasma |
| `plasmoid/contents/ui/main.qml` | UI, transporte D-Bus, spinner, menu, arrasto nativo |
| `tests/unit/test_plasmoid_assets.py` | verificação estática (não-GUI) de metadados e proibições |

**`metadata.json` — exigências**

- `KPackageStructure: "Plasma/Applet"`.
- `KPlugin.Id`: `org.local.deskawake`; `Name`, `Description`, `Icon`, `Category`, `License` (MIT).
- Requisito **Plasma ≥ 6.4** (por causa de `SignalWatcher`) declarado no campo de versão mínima de
  API do applet (chave padrão `X-Plasma-API-Minimum-Version`).
- Prefixo `package/` **não** é usado (é convenção de repo-fonte do KDE, não do pacote instalado).

**`main.qml` — exigências**

- **Tamanho fixo:** `Layout.minimumWidth = Layout.preferredWidth = Layout.maximumWidth = 124` e as
  três de altura `= 42` no `PlasmoidItem`; conteúdo interno contido (`implicitWidth/Height`) e
  `elide` em textos curtos (escala fracionária 125%/150%).
- **Posição:** 100% gerenciada pelo Plasma (`ItemGeometries-<W>x<H>` no `appletsrc`); **nada** de
  `config.json` para posição.
- **Transporte:** `org.kde.plasma.workspace.dbus` com `SessionBus.asyncCall` para ações,
  `SignalWatcher` para `StateChanged` e `DBusServiceWatcher` para liveness. **Registrar watchers
  antes** de `GetState`/`GetLastError` no `Component.onCompleted`.
- **Tema:** `Kirigami.Theme.backgroundColor`, `textColor`, `defaultFont`; forma/opacidade da pílula
  preservadas; **não** fixar grafite/texto claro no QML.
- **Cores de estado fixas:** menta `#80D9A4`, cinza `#929DA5`, vermelho `#E47F7F`.
- **Spinner de duas flechas:** na chamada em voo (`Toggle`/`SetActive`) anima e **bloqueia** o
  toggle; durante a verificação de ~6 s mantém `on` (menta) + spinner **sem** bloquear clique;
  `SetActive(false)` cancela a verificação. Sem âmbar.
- **Arrasto:** nativo por press-and-hold (`AfterPressAndHold`); clique rápido no toggle alterna e
  não move; widgets travados ⇒ não move.
- **Menu:** `Ativar/Desativar` (rótulo dinâmico) + `Sair` + itens nativos do Plasma
  (`Remover widget`, `Configurar`). **Sem** `Tema ▸` e **sem** `Iniciar com o sistema`.
- **`Sair`:** `SetActive(false)` → `Quit()`; se o daemon já caiu, apenas fecha (o
  `DBusServiceWatcher` já levou o visual para `off`).

**Explicitamente fora da E5**

- GTK, MATE, X11 (E4).
- Instalação do pacote (`kpackagetool6 -t Plasma/Applet -i/-u`), autostart e `.service` (E7).
- Backend KDE (já entregue na E2).
- Testes de GUI (checklist manual).
- `config.json`/posição persistida pelo app.

## E5.2 Dependências prévias

- **E2** (contrato D-Bus, ON otimista, `GetLastError`, `StateChanged`).
- **E3** (opcional para o Plasmoid — ele fala direto com o daemon; útil para diagnóstico).
- Ambiente Kubuntu: Plasma 6.6.7, `plasma-workspace` 6.6.7, `kpackagetool6` 2.0, Wayland.

## E5.3 Pontos críticos e armadilhas

1. **Não existe dataengine `dbus` no Plasma 6.** Usar `org.kde.plasma.workspace.dbus`; qualquer
   `Plasma5Support.DataSource` quebra no 6.6.
2. **Registrar watchers antes de consultar:** `SignalWatcher` e `DBusServiceWatcher` no
   `Component.onCompleted` **antes** de `GetState`/`GetLastError`, senão o `StateChanged` inicial
   se perde e o widget nasce com estado errado.
3. **`asyncCall` é assíncrono:** o retorno de `Toggle`/`SetActive` chega por callback. O spinner
   começa no clique e termina no callback; nunca usar `callBlocking` (travaria a UI).
4. **Tamanho fixo com escala fracionária:** `Layout.minimum/preferred/maximum` nas **duas**
   dimensões; conteúdo com `elide`. Não usar `width: 124` solto no `PlasmoidItem` (o containment
   sobrescreve).
5. **Cores de estado são fixas, tema não:** fundo/texto/fonte do `Kirigami.Theme`; menta/cinza/
   vermelho literais. Se o tema for claro, o contraste vem das cores fixas — não clarear o cinza.
6. **Spinner em duas fases diferentes:** chamada (bloqueia toggle) × verificação de ~6 s (não
   bloqueia). Um único `busy` booleano não serve; são dois flags (`callPending`, `verifying`).
7. **Cancelamento visual:** `SetActive(false)` durante a verificação deve parar o spinner de
   verificação imediatamente, sem esperar o daemon responder — o estado `off` chega por
   `StateChanged`.
8. **Menu do Plasmoid é enxuto:** adicionar `Tema ▸` ou `Iniciar com o sistema` é erro de escopo.
   Itens nativos vêm do containment; não recriar.
9. **`Sair` com daemon morto:** `SetActive` pode falhar; capturar o erro, fechar o menu e não exibir
   diálogo.
10. **Arrasto:** não implementar `MouseArea` de drag manual — o nativo por press-and-hold é o
    contrato. Um `MouseArea` que consome o press quebra o arrasto do containment.
11. **Widgets travados:** se `Plasmoid.immutable`, press-and-hold não move; documentar no README e
    não tentar contornar.
12. **`ActiveInhibitions` é `a(ssssu)`:** se o QML precisar exibir diagnóstico, lembrar
    `(what, who, why, mode, flags)` e `flags & 3 == 3`. Não confundir com `HasInhibition(4)`.
13. **Não usar `CanSuspend`** em nenhum diagnóstico do widget.

## E5.4 Critérios de aceite e verificação

**Automático (estático, não-GUI)**

```bash
python3 -m pytest tests/unit/test_plasmoid_assets.py -v
```

- [ ] `metadata.json` é JSON válido com `KPackageStructure == "Plasma/Applet"`,
      `KPlugin.Id == "org.local.deskawake"` e versão mínima de API ≥ 6.4.
- [ ] `main.qml` **não** contém `Plasma5Support`, `gdbus`, `DataSource`, `callBlocking`, `setInterval`
      de polling, `config.json`.
- [ ] `main.qml` contém `org.kde.plasma.workspace.dbus`, `SessionBus.asyncCall`, `SignalWatcher`,
      `DBusServiceWatcher`.
- [ ] `main.qml` contém as três cores exatas `#80D9A4`, `#929DA5`, `#E47F7F`.
- [ ] `main.qml` contém `124` e `42` aplicados a `Layout.minimum/preferred/maximumWidth/Height`.
- [ ] A ordem textual de `SignalWatcher`/`DBusServiceWatcher` precede `GetState` no arquivo (teste
      heurístico documentado como tal).

**Manual — Kubuntu 26.04 / Plasma 6.6 Wayland (da spec)**

- [ ] `kpackagetool6 -t Plasma/Applet -i ./plasmoid` instala em `~/.local/share/plasma/plasmoids/org.local.deskawake/`;
      `--upgrade` atualiza; reexecutar `./install.sh --all` não falha.
- [ ] Plasmoid na área de trabalho mostra 124×42, atrás das janelas, visível com a área à mostra.
- [ ] Press-and-hold move; clique rápido no toggle alterna e não move; com “Widgets travados” não
      move.
- [ ] Toggle reflete `on/off/error` em tempo real, sem polling; remover o Plasmoid não desliga o
      estado de outros clientes.
- [ ] Menu: `Ativar/Desativar`, `Sair` e itens nativos; `Sair` com ON libera imediatamente
      (`ActiveInhibitions` sem `deskawake`; `systemd-inhibit --list` sem `deskawake`).
- [ ] Spinner na chamada (toggle bloqueado) e na verificação de ~6 s (toggle `on`, clique aceito);
      desligar antes dos 6 s cancela sem `error`; falha após ~6 s vira `error` + tooltip.
- [ ] `deskawake ui` recusa Wayland com mensagem; `--force` abre para depuração.
- [ ] PowerDevil/idle: com ON, suspensão automática bloqueada; `ActiveInhibitions` contém a entrada
      **após ~6 s**; `HasInhibition(4)` vira `true`. **Não** usar `CanSuspend`.
- [ ] Tampa e suspensão manual continuam suspendendo (teste destrutivo, notebook).
- [ ] Cookie: outra conexão consegue `UnInhibit`; derrubar o daemon libera a inibição. Teste de
      isolamento **não** se aplica ao KDE.
- [ ] `systemctl --user restart plasma-powerdevil` com ON ⇒ `error` + `StateChanged`; ao voltar,
      re-adquire e volta a `on` após ~6 s, sem rajada.
- [ ] Tema BreezeDark ↔ claro: superfície/texto/fonte acompanham; cores de estado permanecem fixas.

---

# E6 — UI GTK/MATE: Ajustes, Paridade e Créditos

## E6.1 Objetivo e escopo exato

Fechar a diferença de acabamento entre o widget GTK e o Plasmoid repaginado, resolver os achados
A1–A7 que pertencem à UI e entregar os créditos no widget — **sem** copiar o que é específico do
Plasma e sem tocar no QML do KDE. Esta entrega é a antiga “parte de UI” que faltava na E4; o
instalador virou E7 e o empacotamento virou E8.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `ui_gtk/widget.py` | A1 com fallback documentado, tooltip estruturado, ciclo do `last_error`, retry de assinatura D-Bus, acessibilidade, item `Sobre` e `Gtk.AboutDialog` (autor/empresa no corpo, link do repositório, sem botão Créditos) |
| `ui_gtk/theme.py` | knob `#20252B` fixo, hover/pressed/cursor e `format_error_tooltip` puro |
| `core/__init__.py` | `__version__ = "0.1.0"` (fonte única) |
| `tests/unit/test_version.py` | sincronia `core.__version__` × `pyproject.toml` × `plasmoid/metadata.json` |
| `tests/unit/test_theme.py` / `test_ui_assets.py` | tokens, tooltip, menu `Sobre`, ausência de `DESKTOP` e do observador de A1 |
| `spec.md` / docs | emendas das decisões 8, 14, 16, 19 e 34–38 |

**Diferenças intencionais que permanecem:** 124×42 fixo, menu completo (`Tema ▸`, autostart,
`Sobre`), sem hamburguer, sem resize, sem sampling de wallpaper e sem spinner de verificação de ~6 s.
O GTK é a UI do MATE; o Plasmoid continua a referência de qualidade visual, não de layout.

**Explicitamente fora da E6**

- Instalador, `verify.sh`, autostart instalado, `.service` e READMEs (E7).
- `.deb`, GitHub Releases e CI (E8).
- Qualquer mudança de QML, backend, daemon, CLI, contrato D-Bus ou `config.json`.
- Testes automatizados de GUI; teclado como requisito; traduções `.po`.

## E6.2 Dependências prévias

- **E1–E5 mergeadas** (PRs #4, #5, #7, #8 e #10); o Plasmoid repaginado é a referência visual.
- **Mint 22.3 MATE/X11** disponível para a checklist manual; a máquina desta sessão é
  Ubuntu/Plasma/Wayland e não substitui a validação física.

## E6.3 Pontos críticos e armadilhas

1. **Paridade não é cópia:** não adicionar resize, hamburguer, sombra ou chip de wallpaper ao GTK;
   o contrato GTK continua 124×42 e menu completo.
2. **A1 com fallback:** o spike de 21/11/2026 mostrou que o Marco reoculta o widget e que
   `present()` cancela o modo “mostrar área de trabalho”; o observador foi removido e a limitação
   será documentada no README (E7). **Nunca** usar `WindowTypeHint.DESKTOP`.
3. **Knob fixo:** `#20252B` nas duas variantes; o trilho mantém as cores de estado.
4. **Tooltip escapado:** `set_tooltip_markup` + `GLib.markup_escape_text`; nunca interpolar o erro
   cru em markup.
5. **`last_error` limpo:** sair de `error` zera o motivo e o tooltip; entrar em `error` relê
   `GetLastError()`.
6. **Retry de D-Bus é só de assinatura:** no máximo 5 tentativas, canceladas no `destroy`; não é
   polling de estado.
7. **Acessibilidade mínima:** `get_accessible().set_name(...)` na janela e no switch; não habilitar
   foco de teclado.
8. **A6 com mouse real:** XTest não é prova; se o submenu `Tema` fechar, investigar o consumo de
   `button-release` pelo arrasto.
9. **About sem ©/CNPJ:** o símbolo © e a linha legal ficam no `LICENSE`; o About mostra
   autor/empresa e licença MIT no corpo e os links do repositório e do site, sem botão “Créditos”.
10. **Versão única:** `core.__version__` é a fonte; o teste de sincronia falha se
    `pyproject.toml`/`metadata.json` divergirem.
11. **KDE intocado:** nenhum QML; mudanças em `metadata.json`/`assets/` são da E7 e passam por
    `test_plasmoid_assets.py`.

## E6.4 Critérios de aceite e verificação

**Automático**

```bash
python3 -m pytest tests/unit -q
dbus-run-session -- python3 -m pytest tests/integration -q
python3 -m pytest tests/unit/test_version.py tests/unit/test_theme.py tests/unit/test_ui_assets.py -v
```

- [ ] Baseline preservado (267 unit + 34 integração/1 skip) sem regressões.
- [ ] Sincronia de versão verde.
- [ ] Tokens do knob/hover e `format_error_tooltip` cobertos.
- [ ] Menu com `Sobre`, ausência de `WindowTypeHint.DESKTOP` e do observador de A1, `pointer`,
      `get_accessible().set_name` e `markup_escape_text`.
- [ ] Nenhum teste de GUI; nenhuma dependência nova.

**Manual — Mint 22.3 MATE/X11 (obrigatório)**

- [ ] 124×42, canto superior direito, 24 px, sem decoração; fora de `Alt+Tab`/barra/pager; todos os
      workspaces.
- [ ] **A1:** Ctrl+Alt+D esconde o widget e restaurar o traz de volta; limitação documentada no
      README (E7).
- [ ] Arrasto de qualquer ponto; clique no toggle alterna; knob legível no tema claro/escuro.
- [ ] Hover/pressed e cursor `pointer`; spinner na chamada; compositor sólido/translúcido.
- [ ] Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sobre o DeskAwake…`, `Sair`.
- [ ] `Sobre`: `0.1.0`, autor/empresa e licença MIT no corpo, links do repositório e do site; sem
      botão “Créditos”, sem ©/CNPJ.
- [ ] `Sair`/`kill -9` sem órfãos; idle/lock; tema `Mint-Y` ↔ `Mint-Y-Dark`; fallback de fonte.
- [ ] `error` com tooltip e preservação do filho do `systemd-inhibit`; **A6** com mouse real;
      **A7** registrado no PR/README.

---

# E7 — Instalação, Desinstalação, Verificação, Testes e Documentação

## E7.1 Objetivo e escopo exato

Fechar o produto para o usuário final: instalar de forma idempotente e tolerante a ambiente
incompleto, desinstalar sem resíduos, verificar em um comando, consolidar a suíte de testes e
documentar uso, diagnóstico e limitações — incluindo as duas checklists manuais e os créditos. Sem
empacotamento de distro, sem `sudo` e sem instalar `pytest` para o usuário final.

**Inclui**

| Arquivo | Responsabilidade |
|---|---|
| `data/org.local.DeskAwake.service` | ativação D-Bus (`Exec=@EXEC@ daemon`) |
| `data/deskawake-daemon.desktop` | autostart do daemon (os dois DEs) |
| `data/deskawake-widget.desktop` | autostart do widget GTK (**só MATE**) |
| `install.sh` | cópia, launcher, `.service`, autostart, Plasmoid, flags, deps |
| `uninstall.sh` | `Quit()` + fallback por PID, remoção idempotente, `--purge` |
| `verify.sh` | liga/desliga e inspeciona locks, estado D-Bus e órfãos |
| `tests/unit/test_scripts.py` | contrato estático dos scripts/templates/READMEs/créditos |
| `tests/integration/test_installer_scripts.py` | smoke em `HOME` isolado |
| `README.md` + `README.en.md` | uso, instalação, diagnóstico, checklists, limitações e créditos |
| `LICENSE` | razão social + CNPJ |
| `plasmoid/metadata.json` | `Authors`/`Website`/`Copyright` (sem ©), aditivo |

**Flags e contratos dos scripts**

| Flag | Comportamento exato |
|---|---|
| `--all` | Instala **todos os alvos disponíveis**. Kubuntu: daemon+GTK+Plasmoid. Mint: daemon+GTK, avisa “KDE indisponível: `kpackagetool6` ausente” e deixa explícito que daemon+GTK foram instalados. Exit 0. |
| `--only-kde` | Só daemon+Plasmoid. Se `kpackagetool6` faltar ⇒ **exit ≠ 0** com mensagem. |
| `--only-mate` | Só daemon+GTK. Nunca falha por ausência de `kpackagetool6`. |
| `--install-deps` | **Opt-in.** **Nunca** usa `sudo`. Imprime os comandos `apt` separando obrigatórios (`python3-gi`, `python3-dbus`, `systemd`, `kpackagetool6`, `libglib2.0-bin`) de opcional (`fonts-inter`); ao final verifica `python3`, `gi`, `dbus`, `systemd-inhibit`, `kpackagetool6`, `gdbus`. |
| `--purge` (`uninstall.sh`) | Remove também `~/.config/deskawake/`. |
| (sem flag) | Idempotente: reexecutar não falha. |

**Instalação idempotente do Plasmoid:** se já registrado, `kpackagetool6 -t Plasma/Applet --upgrade`;
senão `-i`. Nunca remover/reinstalar cegamente.

**`verify.sh`** (contrato de saída legível, exit ≠ 0 em falha):

- Liga (`on`) e confirma `systemd-inhibit --list` contendo `DeskAwake` + `GetState()=="on"`.
- Desliga (`off`) e confirma lock ausente + `GetState()=="off"`.
- Não deixa órfãos (`systemd-inhibit --list` limpo após `off`).
- **MATE:** `GetInhibitors` contém `deskawake`; `mate-screensaver-command -q` quando existir;
  **não** exige `IsInhibited(8)`.
- **KDE:** aguarda ~6 s e confere `ActiveInhibitions`/`HasInhibition(4)`; confirma que `UnInhibit`
  do `ScreenSaver` libera. **Nunca** `CanSuspend`.

**`tests/` — consolidação final**

- Unitários: config/posição, parser de ambiente, seleção de backend, comando do `systemd-inhibit`,
  máquina de estados, falhas parciais, liberação de locks, CLI, assets do Plasmoid, versão.
- Integração: `dbus-run-session` + ScreenSaver/PolicyAgent falsos; contrato D-Bus; cadeia de
  backends; ON otimista e as três rotas rápidas; queda/retorno do PowerDevil; `SIGTERM`;
  `PDEATHSIG`; `Quit()`; `Local.Disconnected`; scripts em sandbox.
- **Cookie:** teste **condicional ao backend** — no MATE e no KDE/kwin verificar que o cookie morre
  com a conexão e que outra conexão consegue `UnInhibit`; **sem** teste universal de ownership.
- **`@pytest.mark.slow`** opt-in para o ciclo real de 5–6 s; padrão da suíte **não** roda slow.

**Explicitamente fora da E7**

- Qualquer mudança em `core/`, `ui_gtk/`, `plasmoid/contents/` ou `bin/deskawake`.
- Empacotamento `.deb`/AUR/Flatpak; instalação system-wide; `sudo` — **E8**.
- Testes de GUI automatizados.
- Persistência de estado entre sessões; `config.json` criado pelo instalador.
- Instalar `pytest` para o usuário final.

## E7.2 Dependências prévias

- **E6 concluída** (UI GTK/MATE congelada, versão e créditos).
- **E1–E5** para aceite final: os scripts instalam e verificam artefatos reais.
- Mint 22.3 (sem `kpackagetool6`, sem `shellcheck`) e Kubuntu 26.04.1 (`kpackagetool6` 2.0, sem
  `shellcheck`, `python3-pytest` 9.0.2 no apt) disponíveis para validação.
- `dbus-run-session`, `gdbus`, `xprop`/`wmctrl` presentes no Mint.

## E7.3 Pontos críticos e armadilhas

1. **Detectar alvo por ferramenta, não por distro:** a decisão é `command -v kpackagetool6`, nunca
   `lsb_release`/`/etc/os-release`. Mint pode ganhar `kpackagetool6` no futuro; Kubuntu pode perdê-lo.
2. **`--all` no Mint não é erro:** degradar com aviso e **deixar claro** que daemon+GTK foram
   instalados. Exit 0. Já `--only-kde` sem a ferramenta é erro explícito (exit ≠ 0).
3. **`uninstall.sh` tolera `kpackagetool6` ausente:** remover o diretório do Plasmoid se existir e
   **não** falhar se a ferramenta não existir.
4. **`--install-deps` nunca chama `sudo`:** imprime comandos para o usuário executar. Separar
   obrigatórios de `fonts-inter` e verificar ao final.
5. **Idempotência do Plasmoid:** `kpackagetool6 -i` na segunda execução pode falhar com “already
   installed”; detectar e usar `--upgrade`/`-u` com `-t Plasma/Applet`.
6. **Caminhos absolutos no `.service` e nos `.desktop`:** `Exec=` aponta para
   `$SHARE/bin/deskawake`, nunca para o CWD do repo.
7. **Launcher wrapper absoluto:** não symlink; remover o repo não pode quebrar a instalação.
8. **`Quit()` + fallback por PID:** nunca `pkill -f deskawake` cego.
9. **Não remover `~/.config/deskawake/` sem `--purge`** (decisão 18).
10. **`verify.sh` no KDE espera ~6 s:** conferir imediatamente sempre falha pelo debounce; **não**
    usar `CanSuspend`.
11. **`verify.sh` no MATE não usa `IsInhibited(8)`:** `GetInhibitors` + `mate-screensaver-command`.
12. **`shellcheck` ausente:** `bash -n` sempre; shellcheck quando disponível.
13. **Testes de integração não podem vazar processos:** `dbus-run-session` e fixture de limpeza.
14. **Docs não prometem o que não existe:** tampa/suspensão manual, debounce de ~5 s, Plasmoid
    manual, `kpackagetool6` ausente no Mint, A1 conforme a E6.
15. **Créditos nos quatro lugares:** LICENSE (razão social + CNPJ), README (linha legal), metadata
    (`Authors`/`Website`/`Copyright` sem ©) e About do GTK (E6).
16. **Versão única:** README e `.deb` (E8) leem `core.__version__`; não duplicar `0.1.0`.

## E7.4 Critérios de aceite e verificação

**Sintaxe e lint**

```bash
bash -n install.sh uninstall.sh verify.sh
shellcheck install.sh uninstall.sh verify.sh    # quando disponível
```

- [ ] `bash -n` limpo nos três scripts.
- [ ] `shellcheck` limpo ou desvio documentado.

**Instalação — Mint 22.3 MATE**

- [ ] `./install.sh --only-mate` instala daemon+GTK, `.service`, autostart do daemon/widget e
      launcher.
- [ ] `./install.sh --all` no Mint: exit 0, aviso de KDE indisponível e mensagem de que daemon+GTK
      foram instalados.
- [ ] `./install.sh --only-kde` no Mint: exit ≠ 0.
- [ ] `./install.sh --install-deps` sem `sudo` no output.
- [ ] Reexecutar `--all` duas vezes: exit 0, sem estado quebrado.
- [ ] `./uninstall.sh` preserva `~/.config/deskawake/`; idempotente; `--purge` remove.
- [ ] `./verify.sh`: `on`/`off`, `GetInhibitors`, sem órfãos; sem `IsInhibited(8)`.
- [ ] Autostart em login novo (ou limitação registrada).

**Instalação — Kubuntu 26.04.1 / Plasma 6.6**

- [ ] `./install.sh --all` instala daemon+GTK+Plasmoid via `kpackagetool6 -t Plasma/Applet -i`.
- [ ] Reexecutar usa `-u` e não falha.
- [ ] `./install.sh --only-kde` funciona com `kpackagetool6` 2.0.
- [ ] Plasmoid aparece em “Adicionar widgets”; “Sobre” mostra autor/site/linha legal.
- [ ] `./verify.sh` espera ~6 s e confirma `ActiveInhibitions`/`HasInhibition(4)`.
- [ ] `./uninstall.sh` remove o Plasmoid e o restante.

**Suíte completa**

```bash
python3 -m pytest tests/unit -q
dbus-run-session -- python3 -m pytest tests/integration -q
python3 -m pytest tests/integration -m slow -q      # opt-in
python3 -m pytest tests/unit/test_scripts.py -v
python3 -m pytest tests/integration/test_installer_scripts.py -v
```

- [ ] Unitários verdes nas duas máquinas.
- [ ] Integração verde em `dbus-run-session`.
- [ ] Slow verde quando habilitado; **não** roda por padrão.
- [ ] Scripts verdes; nenhum teste universal de ownership; nenhum teste de GUI.

**Documentação**

- [ ] READMEs cobrem instalação, flags, CLI, diagnóstico, limitações, testes, checklists e créditos.
- [ ] Nenhuma afirmação contradiz a `spec.md`; os dois idiomas são equivalentes.
- [ ] LICENSE e metadata com a linha legal; About do GTK sem ©/CNPJ.

---

# E8 — Empacotamento e Distribuição (placeholder)

## E8.1 Objetivo e escopo

Registrar o canal de distribuição e os pontos a especificar depois da E7. **Não** há implementação
nesta rodada.

| # | Decisão | Valor |
|---|---|---|
| 1 | Canal | **GitHub Releases + `.deb`** (CI gera pacote, tarball e checksums) |
| 2 | Per-user | `install.sh` continua como alternativa sem `sudo` |
| 3 | Versão | `0.1.0` (`core.__version__`) |
| 4 | Fora de escopo | AUR, Flatpak, AppImage, Snap |
| 5 | Layout | `.deb` system-wide (`/usr/lib/deskawake`, `/usr/bin/deskawake`, `/usr/share/...`); config/autostart por usuário |
| 6 | CI | GitHub Actions/`ubuntu-latest`; build com `dpkg-deb` |
| 7 | Assinatura | Sem GPG nesta rodada; checksums SHA-256 |
| 8 | Spec | Emendar a restrição “sem empacotamento de distro” quando a E8 for especificada |

## E8.2 Pontos a especificar depois da E7

- Nome do pacote e conflito com o wrapper per-user; detecção de instalação prévia.
- `control`: maintainer (e-mail ainda não definido), dependências e `Recommends`.
- Paths system-wide do `.service`, autostart, Plasmoid e assets; como o `@EXEC@` aponta para
  `/usr/bin/deskawake`.
- `postinst`/`prerm`; nada de iniciar daemon no install.
- Workflow de tag `v*`, anexos do release e checksums.
- Teste em container `ubuntu:24.04`/`26.04` (`dpkg -i`, `deskawake status`, remoção).
- Update manual (sem auto-update).

## E8.3 Critérios para iniciar

- [ ] E7 mergeada e layout per-user congelado.
- [ ] E6 mergeada com `core.__version__` e About.
- [ ] E-mail do maintainer definido.
- [ ] Workflow/CI e nomes de artefatos aprovados.

---

## 4. Rastreabilidade

### 4.1 Tarefas da spec → entrega

| Tarefa da spec | Entrega |
|---|---|
| 1. Esqueleto do repo (`LICENSE`, `pyproject.toml`, árvore) | **E1** |
| 2. `core/config.py` | **E1** |
| 3. `core/environment.py` | **E1** |
| 4. `core/inhibitors.py` | **E2** |
| 5. `core/state.py` | **E2** |
| 6. `core/daemon.py` | **E2** |
| 7. `core/cli.py` + `bin/deskawake` | **E3** |
| 8. `ui_gtk/widget.py` | **E4** + **E6** (A1, tooltip, retry, acessibilidade, `Sobre`) |
| 9. `ui_gtk/theme.py` + `assets/` | **E4** + **E6** (knob/hover/cursor e `format_error_tooltip`) |
| 10. `plasmoid/` | **E5** |
| 11. `install.sh` | **E7** |
| 12. `uninstall.sh` | **E7** |
| 13. `verify.sh` | **E7** |
| 14. `tests/` | **E1–E3/E5** (por módulo) + **E6** (versão/tema/UI estática) + **E7** (consolidação, scripts, slow) |
| 15. `README.md` + `README.en.md` | **E7** |

### 4.2 Decisões da spec → entrega que as materializa

| Decisão | Entrega |
|---|---|
| 1 (escopo do ON), 11, 25 (suspensão/tampa) | **E2** (implementação), **E7** (verify/docs) |
| 2 (daemon), 3 (ciclo de vida), 4 (Sair) | **E2** (núcleo), **E4/E5** (kill switch na UI) |
| 5 (persistência) | **E1** (config), **E4** (posição), **E5** (posição é do Plasma) |
| 6 (CLI) | **E3** |
| 7 (transporte Plasmoid), 16 (UI Plasmoid), 17 (arrasto) | **E5** (Plasmoid) / **E4** (GTK) |
| 8 (camada Z GTK) | **E4** + **E6** (A1) |
| 9, 10 (instalador/autostart) | **E7** |
| 12 (sucesso/erro), 21 (`SetActive`), 29 (confirmação KDE), 30 (verificação), 31 (liveness), 32 (fim de sessão), 33 (progresso) | **E2** (núcleo), **E4/E5** (spinner) |
| 13 (tema), 14 (menu GTK), 15 (fonte) | **E4** + **E6** (`Sobre`, knob, tooltip), **E5** (Kirigami) |
| 18 (uninstall) | **E7** |
| 19 (testes) | **E2/E3/E5** (por módulo) + **E6** (versão/UI) + **E7** (consolidação) |
| 20 (meta) | **E1** (MIT/pyproject), **E7** (READMEs/créditos) |
| 22 (layout Plasmoid) | **E5** |
| 23 (drag × `Gtk.Switch`) | **E4** |
| 24, 26, 27, 28 (backends/cookie) | **E2** |
| 29 (hierarquia de confirmação) | **E2** |
| 34 (créditos) | **E6** (About) + **E7** (LICENSE/metadata/README) |
| 35 (versão `0.1.0`) | **E6** (fonte/teste) + **E7** (docs) + **E8** (`.deb`) |
| 36 (paridade E6) | **E6** |
| 37 (E7 instalação) | **E7** |
| 38 (E8 distribuição) | **E8** |

### 4.3 Gates

| Gate | Condição de passagem |
|---|---|
| **G-E1** | `pytest tests/unit/test_config.py tests/unit/test_environment.py` verde; `detect_environment` correto nas duas máquinas |
| **G-E2** | Unit + `dbus-run-session` de integração verdes; `SIGTERM`/`Quit`/`PDEATHSIG`/`Local.Disconnected` comprovados; nenhum órfão |
| **G-E3** | `test_cli.py` verde; `status` 0/1/3 sem auto-start; guarda Wayland e single-instance comprovadas |
| **G-E4** | Testes puros de tema/CSS verdes; checklist manual MATE executada (itens não-destrutivos obrigatórios; destrutivos opcionais) |
| **G-E5** | Teste estático do Plasmoid verde; `kpackagetool6 -t Plasma/Applet -i` instala; checklist manual Kubuntu executada (backend + visual) |
| **G-E6** | Testes de versão/tema/UI estática verdes; baseline preservado; checklist MATE §9.2 preenchida (A1–A7 na parte de UI) |
| **G-E7** | `bash -n` limpo; `install.sh`/`uninstall.sh` idempotentes nas duas máquinas; `verify.sh` verde nos dois backends; suíte completa verde; READMEs completos com créditos |
| **G-E8** | Placeholder: só fecha quando o `.deb` instalar/remover em container e o release tiver checksums |

---

## 5. Riscos residuais (fecham só com máquina física)

| Risco | Onde fecha |
|---|---|
| Empilhamento/hints do Marco (`keep_below`, `stick`, `Alt+Tab`) | Checklist manual MATE (E4) |
| Arrasto do Plasmoid por press-and-hold e “Widgets travados” | Checklist manual Kubuntu (E5) |
| Spinner visual e escala fracionária (125%/150%) | Checklist manual (E4/E5) |
| Tema claro/escuro em runtime (MATE e Breeze) | Checklist manual (E4/E5/E6) |
| Debounce real de ~5 s do PowerDevil | `@pytest.mark.slow` (E7) + checklist Kubuntu (E5) |
| Tampa e suspensão manual continuam suspendendo | Teste destrutivo manual no Kubuntu (E5/E7) |
| `mate-screensaver` com idle/lock habilitados | Checklist manual MATE (E4/E6) |
| `kpackagetool6` ausente no Mint | `install.sh --all` (E7) + checklist Mint |
| A1 (“mostrar área de trabalho”) | Spike da E6 + checklist MATE; fallback documentado na E7 |
| Contraste do knob no tema claro | Checklist MATE (E6) |
| Créditos no “Sobre” do Plasma | Checklist Kubuntu (E7) + `test_plasmoid_assets.py` |
| `.deb` system-wide | Container da E8 (placeholder) |

> **Limite de validação declarado na spec:** o backend/UI MATE foi validado por leitura de ambiente;
> o backend KDE foi validado por D-Bus e código-fonte do PowerDevil/kscreenlocker; a **GUI do
> Plasmoid, o arrasto e os testes destrutivos de tampa/suspensão** permanecem manuais. Nenhuma
> entrega acima pode declarar esses itens “prontos” sem a checklist correspondente.
