# Tasks: E5 — Plasmoid KDE Plasma 6.6

**Feature:** DeskAwake — E5 | **Data:** 2026-11-20 | **Estimativa:** ≈ 8 h (27 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 1–33, “Fluxo alvo”, “Contratos”, “Aparência”, “Notas ao implementador” e “Variações por distro”) | [`design_e5.md`](design_e5.md) | [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E5 | [`design_e2.md`](design_e2.md) (contrato D-Bus/liveness) | [`visual/design_visual_aprovado.md`](visual/design_visual_aprovado.md)

## Resumo

- Total de tasks: 27
- Estimativa total: ≈ 8 h (~1 dia de trabalho focado, incluindo a checklist manual)
- Dependências externas: branch `feat/e5-plasmoid-kde` **já existente** e empilhada sobre a E3; Plasma 6.6.7 / `plasma-workspace` 6.6.7; `kpackagetool6` 2.0; `plasmawindowed`; assets aprovados em `docs/implementation/visual/assets/`; máquina Ubuntu 26.04.1 + Plasma 6.6.7/Wayland para a checklist manual. **Nenhuma** migration, serviço, `.service`, autostart, dependência nova de runtime ou alteração em `core/`.
- Gate: **G-E5** — `tests/unit/test_plasmoid_assets.py` verde; `tests/unit` sem regressão (baseline **192 passed** nesta branch; **233** se a E4 estiver mergeada); `kpackagetool6 -t Plasma/Applet -i ./plasmoid` instala em `~/.local/share/plasma/plasmoids/org.local.deskawake/`; `plasmawindowed org.local.deskawake` carrega sem erro de QML; checklist manual da §9.2 do design executada e colada no PR; `git diff -- core/` vazio.
- Fora de escopo (não criar nesta entrega): qualquer arquivo em `core/`; GTK/MATE/X11 (E4); `install.sh`/`uninstall.sh`/`verify.sh`/`.service`/autostart/READMEs (E6); `config.json`, posição persistida, `config.qml`/KConfigXT, `Messages.sh`/`.po`; qualquer membro novo no contrato D-Bus; testes automatizados de GUI; redesenho dos SVGs aprovados.
- Referência de comportamento: em conflito, a `spec.md` vence o `design_e5.md`; a ordem completa é `spec.md` > `design_e5.md` > `visual/design_visual_aprovado.md` (apenas forma/movimento). As quatro decisões fechadas em 2026-11-20 estão na §1.1 do design.
- Este arquivo é versionado em `docs/implementation/`; **não** entra no PR de código nem é citado em código.

**Sequência:** setup → testes estáticos de metadados (TDD) → `metadata.json` → testes estáticos do QML (TDD) → esqueleto/watchers/visual → menu/funções/onCompleted → assets + testes (TDD) → gate automatizado → smoke de pacote → checklist manual → auditoria e PR.

**Regras de teste que valem para todas as tasks:**

- A suíte da E5 é **estática e headless**: lê `metadata.json`, `main.qml` e os SVGs como texto/JSON/XML; não executa QML, não abre display, não fala com o barramento real e não depende de `kpackagetool6`/Plasma instalados.
- `tests/unit/test_plasmoid_assets.py` usa somente stdlib (`json`, `re`, `hashlib`, `pathlib`, `xml.etree.ElementTree`) + `pytest`; **não** importa `gi`, `dbus` nem `PyQt`/`PySide`.
- `tests/conftest.py` **não** é alterado; os testes E1–E4 permanecem intactos.
- Os testes de QML são **heurísticos e documentados como tal** no docstring: verificam tokens/ordem textual, não execução. Falso positivo de token é aceitável; comportamento real é a checklist manual (§9.2 do design).
- TDD: os testes vêm antes da implementação e o RED esperado deve ser confirmado (arquivo ausente ou teste falhando) antes de criar o artefato.
- `main.qml` segue a ordem da §4.9 do design: pragma/imports → propriedades → `Layout.*`/`Plasmoid.*` → `SignalWatcher` → `DBusServiceWatcher` → `Timer` → árvore visual → `contextualActions` → funções → `Component.onCompleted`.
- Assets são cópias **byte a byte** dos aprovados; a comparação com `docs/` é `pytest.skip` quando o diretório não existir, mas o SHA-256 do pacote é sempre exigido.
- Mensagens da UI em pt-BR; tokens públicos sempre `on|off|error`; nenhuma referência a `AC-*`, `T-*`, `design_e5.md`, `tasks_e5.md`, `spec.md`, `DELIVERY_MAP.md` ou `visual/` em código/comentários/commits/PR.

## Priorização

Score = (Impacto × Confiança) / Esforço (H=3, M=2, L=1).

| Grupo | Impacto | Confiança | Esforço | Score | Execução |
|---|---|---|---|---|---|
| Fundação, testes estáticos e metadata (T-01–T-09) | 3 | 3 | 2 | 4,5 | Primeiro — destrava todo o resto |
| Núcleo QML: visual, D-Bus, menu e estado (T-10–T-18) | 3 | 2 | 3 | 2,0 | Neste ciclo — é a entrega em si |
| Assets e gate automatizado (T-19–T-22) | 3 | 3 | 1 | 9,0 | Assim que o QML existir; smoke de pacote em seguida |
| Checklist manual e entrega (T-23–T-27) | 3 | 2 | 2 | 3,0 | Fecha o G-E5 após a implementação |

Nenhuma task cai em backlog (< 2): a E5 é uma entrega única e o gate só fecha com todas.

## Tasks

### 0. Setup e fundação

- [ ] **T-01**: Confirmar a branch da E5 empilhada sobre a E3
  - Comandos:
    - `git branch --show-current` ⇒ `feat/e5-plasmoid-kde`
    - `git merge-base --is-ancestor feat/e3-cli-launcher HEAD` ⇒ exit 0
    - `git status --short` ⇒ apenas `docs/implementation/design_e5.md` modificado (artefato transitório; fica fora do commit)
  - Critério: branch correta e E3 já contida no histórico. **Não** recriar a branch e **não** rebasear a partir da `main`; se a E4 for mergeada antes, o baseline de testes passa de 192 para 233.
  - Estimativa: 5min

- [ ] **T-02**: Conferir o toolchain do Plasma e o pytest de desenvolvimento
  - Comandos:
    - `plasmashell --version` ⇒ `plasmashell 6.6.7`
    - `kpackagetool6 --version` ⇒ `kpackagetool6 2.0`
    - `command -v plasmawindowed` ⇒ caminho absoluto
    - `python3 -m pytest --version` ⇒ pytest disponível
    - `command -v qmllint || true` ⇒ vazio é esperado
  - Critério: Plasma ≥ 6.6, `kpackagetool6` 2.0 e `plasmawindowed` presentes; `qmllint` ausente **não** bloqueia e não vira dependência. Nenhum pacote novo é instalado.
  - Estimativa: 5min

- [ ] **T-03**: Rodar a linha de base e conferir os assets aprovados
  - Comandos:
    - `python3 -m pytest tests/unit -q` ⇒ **192 passed** nesta branch (ou **233** com a E4 mergeada), 0 failures
    - `test -f docs/implementation/visual/assets/deskawake.svg && test -f docs/implementation/visual/assets/spinner.svg`
    - `sha256sum docs/implementation/visual/assets/deskawake.svg docs/implementation/visual/assets/spinner.svg` ⇒ `2c35dd2469253e0ebac24ff25f5bdd08fb0d17508c10ac98c80a09ee09fbc7d1` e `fc7746a98c78983b17cace66a975428b4febc08986168516cc6d592d53b8eb64`
  - Critério: baseline conforme acima; os dois SVGs existem e batem com os hashes aprovados. Se o baseline falhar, parar e resolver antes da E5.
  - Estimativa: 5min

### 1. `metadata.json` (TDD)

- [ ] **T-04**: Escrever os testes RED de metadados
  - Arquivo: `tests/unit/test_plasmoid_assets.py` (novo)
  - Estrutura: constantes `REPO_ROOT = Path(__file__).resolve().parents[2]`, `PLASMOID = REPO_ROOT / "plasmoid"`, `METADATA = PLASMOID / "metadata.json"`, `MAIN_QML = PLASMOID / "contents/ui/main.qml"`, `ASSETS = PLASMOID / "contents/ui/assets"`; helpers `_text(path)` e `_json(path)`.
  - Testes (nomes canônicos):
    - `test_metadata_is_valid_json` — `metadata.json` existe e `json.loads` não levanta.
    - `test_metadata_structure` — `KPackageStructure == "Plasma/Applet"`; `KPlugin.Id == "org.local.deskawake"`; `X-Plasma-API-Minimum-Version` no topo, parse `(6, 4)` ou maior; ausência da chave exata `X-Plasma-API` (legado); ausência de `plasmoid/package/`.
    - `test_metadata_required_fields` — `KPlugin.Name == "DeskAwake"`; `Description`, `Icon`, `Category`, `License` e `Version` não vazios; `License == "MIT"`.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "metadata"`
  - Critério: falha (RED) — `FileNotFoundError` para `plasmoid/metadata.json`.
  - Estimativa: 15min

- [ ] **T-05**: Criar `plasmoid/metadata.json`
  - Arquivo: `plasmoid/metadata.json`
  - Contrato: `design_e5.md` §4.1 — `KPackageStructure: "Plasma/Applet"`; `KPlugin` com `Id: "org.local.deskawake"`, `Name: "DeskAwake"`, descrição pt-BR (“Impede que a tela bloqueie ou a máquina suspenda por inatividade.”), `Icon: "preferences-system-power-management"`, `Category: "System Information"`, `License: "MIT"`, `Version: "0.1.0"`; `X-Plasma-API-Minimum-Version: "6.4"`. **Sem** `X-Plasma-API` legado, **sem** `X-Plasma-NotificationArea`, **sem** `package/`.
  - Comandos:
    - `python3 -m json.tool plasmoid/metadata.json > /dev/null` ⇒ exit 0
    - `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "metadata"` ⇒ GREEN
  - Critério: JSON válido e os três testes de metadados verdes; nenhum campo além do contrato.
  - Estimativa: 10min

### 2. Testes estáticos de `main.qml` (TDD)

- [ ] **T-06**: Escrever os testes RED de proibições, transporte, tamanho e slots
  - Arquivo: `tests/unit/test_plasmoid_assets.py` (append)
  - Testes:
    - `test_main_qml_has_no_forbidden_dependencies` — ausência de `Plasma5Support`, `gdbus`, `DataSource`, `callBlocking`, `setInterval`, `config.json`, `StartServiceByName`/`startServiceByName`, `Gtk`/`GTK`.
    - `test_main_qml_uses_native_transport` — contém `import org.kde.plasma.workspace.dbus as DBus`, `SessionBus.asyncCall`, `SignalWatcher {`, `DBusServiceWatcher {`; `busType: DBus.BusType.Session` pelo menos 2 vezes; regex `busType:\s*Session\b` ausente.
    - `test_main_qml_fixes_plasmoid_size` — as seis restrições `Layout.minimum/preferred/maximumWidth: 124` e `...Height: 42` (regex tolerante a espaços); `Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground`; ausência de `width: 124` solto no `PlasmoidItem`.
    - `test_main_qml_fixes_inner_slots` — min/pref/max iguais para símbolo `22×22`, nome `58` de largura e toggle `32×18` (contagens/regex no texto; sem exigir posição exata das declarações).
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "forbidden or native_transport or plasmoid_size or inner_slots"`
  - Critério: falha (RED) — `FileNotFoundError` para `plasmoid/contents/ui/main.qml`.
  - Estimativa: 20min

- [ ] **T-07**: Escrever os testes RED de tema, estado, D-Bus, tooltip, spinner, menu e pílula/célula
  - Arquivo: `tests/unit/test_plasmoid_assets.py` (append)
  - Testes:
    - `test_main_qml_uses_theme_surface` — `Kirigami.Theme.backgroundColor`, `Kirigami.Theme.textColor`, `0.88`, `0.18`, `0.28`, `pillToolTip.containsMouse`, `radius: 12`, `border.width: 1`; ausência de `#20252B`/`#F0F3F5`.
    - `test_main_qml_uses_theme_font` — `Kirigami.Theme.defaultFont`, `pixelSize: 10`, `Font.DemiBold`, `elide: Text.ElideRight`.
    - `test_main_qml_state_colors` — contém exatamente as três cores `#80D9A4`, `#929DA5`, `#E47F7F`.
    - `test_main_qml_toggle_contract` — `acceptedButtons: Qt.LeftButton`, `enabled: !root.callPending`, `cursorShape: Qt.PointingHandCursor`, `requestActive(root.state !== "on")`, knob `14×14`/`radius: 7`.
    - `test_main_qml_spinner_contract` — `spinner.svg`, `RotationAnimator`, `duration: 960`, `easing.type: Easing.Linear`, `loops: Animation.Infinite`, `running: root.callPending || root.verifying`, `visible: root.callPending || root.verifying`.
    - `test_main_qml_tooltip_contract` — `PlasmaCore.ToolTipArea`, `mainText: "DeskAwake"`, `textFormat: Text.PlainText`, `active: root.state === "error"`, `pillToolTip.containsMouse`; `toolTipMainText`/`toolTipSubText` **sem** o prefixo `Plasmoid.` (regex `Plasmoid\.toolTip` ausente).
    - `test_main_qml_menu_contract` — `Plasmoid.contextualActions`, `PlasmaCore.Action`, `"Ativar"`, `"Desativar"`, `"Sair"`, `enabled: !root.callPending`; ausência de `removeInternalAction`, de `"Tema"` e de `"Iniciar com o sistema"`.
    - `test_main_qml_dbus_contract` — `member: "GetState"`, `member: "GetLastError"`, `verifyWindowMs: 6000`; ausência de `member: "Toggle"`, `Toggle()` e `StartServiceByName`.
    - `test_main_qml_set_active_contract` — `member: "SetActive"`, `signature: "(b)"`, `new DBus.bool(`.
    - `test_main_qml_verification_lifecycle` — `function startVerification`, `function stopVerification`, `function invalidateCalls`, `verifyTimer.restart()`, `verifyTimer.stop()`, `running: root.verifying`, `interval: root.verifyWindowMs`.
    - `test_main_qml_quit_contract` — `function quitDaemon`, guarda por `daemonWatcher.registered`, `stopVerification()` antes de `member: "Quit"`, `SetActive(false)` antes de `Quit`.
    - `test_main_qml_state_model_contract` — `property string state: "off"`, `property string lastError`, `property bool callPending`, `property bool verifying`, `property int callToken`; declarações de `syncFromDaemon`, `applyState`, `requestLastError`, `requestActive`, `quitDaemon`, `startVerification`, `stopVerification`, `invalidateCalls`; `Component.onCompleted`.
    - `test_main_qml_watchers_precede_getstate` — `SignalWatcher` e `DBusServiceWatcher` aparecem antes de `GetState`; `Component.onCompleted` aparece depois das funções. Docstring marca o teste como heurístico.
    - `test_main_qml_keeps_pill_compact_inside_containment_cell` — pílula visível 124×42 centrada na célula do containment (`anchors.centerIn`, `root.pillWidth`/`pillHeight`, propriedades readonly 124/42).
    - `test_main_qml_normalizes_signal_payload` — `applyState` normaliza `String(newState)` antes de comparar.
    - `test_main_qml_error_state_refreshes_last_error` — handler normaliza `String(state)` e pede `requestLastError()` em `error`.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "theme or state or toggle or spinner or tooltip or menu or dbus or verification or quit or watchers or pill or normalizes"`
  - Critério: falha (RED) — `FileNotFoundError` para `main.qml`.
  - Estimativa: 25min

### 3. `main.qml` — esqueleto, watchers e visual

- [ ] **T-08**: Criar o esqueleto de `main.qml` com raiz, estado e tamanho fixo
  - Arquivo: `plasmoid/contents/ui/main.qml` (novo)
  - Contrato: `design_e5.md` §4.2 e §4.9 — `pragma ComponentBehavior: Bound`; imports `QtQuick`, `QtQuick.Layouts`, `org.kde.plasma.plasmoid`, `org.kde.plasma.core as PlasmaCore`, `org.kde.kirigami as Kirigami`, `org.kde.plasma.workspace.dbus as DBus`; `PlasmoidItem { id: root }`; constantes `serviceName`, `objectPath`, `ifaceName`, `verifyWindowMs: 6000`; propriedades `state: "off"`, `lastError`, `callPending`, `verifying`, `callToken`; seis restrições `Layout.*` (124/42); `Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground`; `toolTipMainText: "DeskAwake"`, `toolTipSubText: root.state === "error" ? root.lastError : ""`, `toolTipTextFormat: Text.PlainText`. Sem watchers, visual, menu ou funções ainda.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "forbidden or plasmoid_size"`
  - Critério: os dois testes ficam verdes (GREEN); `grep -n "PlasmoidItem" plasmoid/contents/ui/main.qml` presente; nenhuma referência a `config.json`/`StartServiceByName`; ordem do arquivo respeitada.
  - Estimativa: 20min

- [ ] **T-09**: Declarar `SignalWatcher`, `DBusServiceWatcher` e o Timer de verificação
  - Arquivo: `plasmoid/contents/ui/main.qml` (seções 4–6 da §4.9)
  - Contrato: `design_e5.md` §2.6 e §4.3 — `DBus.SignalWatcher { id: signalWatcher; busType: DBus.BusType.Session; service: root.serviceName; path: root.objectPath; iface: root.ifaceName }`; `DBus.DBusServiceWatcher { id: daemonWatcher; busType: DBus.BusType.Session; watchedService: root.serviceName }`; `Timer { id: verifyTimer; interval: root.verifyWindowMs; repeat: false; onTriggered: root.stopVerification() }`. Os dois watchers vêm **antes** do Timer e de qualquer função/`GetState`.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "native_transport"`
  - Critério: `test_main_qml_uses_native_transport` verde (GREEN); os dois `busType` qualificados; nenhuma forma `busType: Session`.
  - Estimativa: 20min

- [ ] **T-10**: Montar `PlasmaCore.ToolTipArea`, a pílula e os três slots fixos
  - Arquivo: `plasmoid/contents/ui/main.qml` (seção 7, parte 1)
  - Contrato: `design_e5.md` §2.3–§2.5 — `PlasmaCore.ToolTipArea { id: pillToolTip; anchors.centerIn: parent; width: root.pillWidth; height: root.pillHeight; mainText: "DeskAwake"; subText: root.state === "error" ? root.lastError : ""; textFormat: Text.PlainText; active: root.state === "error"; location: Plasmoid.location }`; dentro, `Rectangle { id: pill; anchors.fill: parent; radius: 12; border.width: 1; color: Qt.rgba(Kirigami.Theme.backgroundColor.r, ..., 0.88); border.color: Qt.rgba(Kirigami.Theme.textColor.r, ..., pillToolTip.containsMouse ? 0.28 : 0.18) }`; `RowLayout { anchors.fill: parent; anchors.leftMargin: 1; anchors.rightMargin: 1; spacing: 4 }`; slot do símbolo `Item` 22×22 com as seis `Layout.*` = 22; `Text` do nome com min/pref/maxWidth 58 e `text: "DeskAwake"`; slot do toggle `Item` 32×18 com as seis `Layout.*` (32/18). A pílula visível é fixada em 124×42 centrada no `PlasmoidItem` (`pillWidth`/`pillHeight`), porque o `AppletsLayout` do desktop reserva uma célula maior (128×96); a raiz mantém as seis `Layout.*`. Conteúdo dos slots vem nas tasks seguintes.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "theme_surface or tooltip_contract or inner_slots"`
  - Critério: os três testes ficam verdes (GREEN); geometria externa continua 124×42; nenhuma cor de superfície fixa.
  - Estimativa: 20min

- [ ] **T-11**: Inserir o símbolo e o nome no layout
  - Arquivo: `plasmoid/contents/ui/main.qml` (slot 22×22 e `Text` do nome)
  - Contrato: `design_e5.md` §2.3, §2.5 e §4.7 — no slot do símbolo, `Kirigami.Icon { source: Qt.resolvedUrl("assets/deskawake.svg"); Layout.preferredWidth/Height: 22; isMask: true; color: Kirigami.Theme.textColor; visible: !(root.callPending || root.verifying) }`; no nome, `font.family: Kirigami.Theme.defaultFont.family`, `font.pixelSize: 10`, `font.weight: Font.DemiBold`, `elide: Text.ElideRight`, `horizontalAlignment: Text.AlignHCenter`, `verticalAlignment: Text.AlignVCenter`, `Layout.alignment: Qt.AlignVCenter`.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "theme_font"`
  - Critério: `test_main_qml_uses_theme_font` verde (GREEN); o nome permanece no slot de 58 px; nenhuma cor de estado no símbolo/nome.
  - Estimativa: 20min

- [ ] **T-12**: Implementar o toggle 32×18 e a `MouseArea` restrita
  - Arquivo: `plasmoid/contents/ui/main.qml` (slot do toggle)
  - Contrato: `design_e5.md` §2.3, §4.4 e ADR-05 — `Rectangle` trilho 32×18, raio 9, cor `#80D9A4` em `on`/`verifying`, `#E47F7F` em `error`, `#929DA5` em `off`; `Rectangle` botão 14×14, raio 7, cor `Kirigami.Theme.backgroundColor`, `y: 2`, `x: 1` (off/error) ou `17` (on); `MouseArea { acceptedButtons: Qt.LeftButton; enabled: !root.callPending; cursorShape: Qt.PointingHandCursor; onClicked: root.requestActive(root.state !== "on") }`; opacidade 0,6 no conjunto durante `callPending`.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "state_colors or toggle"`
  - Critério: `test_main_qml_state_colors` e `test_main_qml_toggle_contract` verdes (GREEN); nenhum `MouseArea` na pílula inteira; botão direito não consumido.
  - Estimativa: 20min

- [ ] **T-13**: Implementar o spinner com `RotationAnimator`
  - Arquivo: `plasmoid/contents/ui/main.qml` (slot do símbolo)
  - Contrato: `design_e5.md` §4.7 — `Kirigami.Icon { source: Qt.resolvedUrl("assets/spinner.svg"); Layout.preferredWidth/Height: 22; isMask: true; color: Kirigami.Theme.textColor; visible: root.callPending || root.verifying }`; `RotationAnimator on rotation { from: 0; to: 360; duration: 960; easing.type: Easing.Linear; loops: Animation.Infinite; running: root.callPending || root.verifying; transformOrigin: Item.Center }`; sem animação em repouso.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "spinner"`
  - Critério: `test_main_qml_spinner_contract` verde (GREEN); geometria do slot/nome/toggle inalterada.
  - Estimativa: 15min

### 4. `main.qml` — menu, D-Bus e estado

- [ ] **T-14**: Implementar o menu enxuto via `Plasmoid.contextualActions`
  - Arquivo: `plasmoid/contents/ui/main.qml` (seção 8)
  - Contrato: `design_e5.md` §4.6 e ADR-08 — dois `PlasmaCore.Action`: `Ativar/Desativar` com `text: root.state === "on" ? "Desativar" : "Ativar"`, `enabled: !root.callPending`, `onTriggered: root.requestActive(root.state !== "on")`; `Sair` com `text: "Sair"`, `enabled: !root.callPending`, `onTriggered: root.quitDaemon()`. Não recriar itens nativos, não chamar `removeInternalAction`, não incluir `Tema`/`Iniciar com o sistema`.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "menu"`
  - Critério: `test_main_qml_menu_contract` verde (GREEN); rótulos em pt-BR; ações desabilitadas apenas durante `callPending`.
  - Estimativa: 15min

- [ ] **T-15**: Implementar `syncFromDaemon`, `applyState` e `requestLastError`
  - Arquivo: `plasmoid/contents/ui/main.qml` (seção 9, parte 1)
  - Contrato: `design_e5.md` §4.2, §4.4, §6.1 e §6.6 —
    - `syncFromDaemon()`: sem dono ⇒ `applyState("off")`; com dono ⇒ incrementa geração, `GetState` uma vez (`SessionBus.asyncCall`), descarta callback de geração antiga, aplica o estado e, se `"error"`, chama `requestLastError()`; falha mantém o último estado e apenas `console.warn`.
    - `applyState(state)`: aceita somente `on|off|error`; atualiza `state`; limpa `lastError` ao sair de `error`; para a verificação em `off`/`error`.
    - `requestLastError()`: só com dono; `GetLastError` uma vez; preenche `lastError`; nunca abre diálogo.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "dbus_contract"`
  - Critério: `test_main_qml_dbus_contract` verde (GREEN); nenhuma chamada `Toggle`/`StartServiceByName`; nenhuma consulta sem dono.
  - Estimativa: 25min

- [ ] **T-16**: Implementar `requestActive`, verificação e `invalidateCalls`
  - Arquivo: `plasmoid/contents/ui/main.qml` (seção 9, parte 2)
  - Contrato: `design_e5.md` §4.2, §4.5, §6.2 e ADR-04 — `requestActive(active)` ignora se `callPending`; incrementa `callToken`, liga `callPending`, chama `stopVerification()`, envia `SetActive` com `signature: "(b)"` e `arguments: [new DBus.bool(active)]`; no sucesso, aplica o estado retornado e, se `active && estado == "on"`, chama `startVerification()`; em `"error"`, chama `requestLastError()`; no erro, se houver dono ressincroniza uma vez, senão `applyState("off")`, com `console.warn` e sem diálogo. `startVerification()` liga `verifying` e reinicia o Timer; `stopVerification()` desliga e para o Timer (idempotente); `invalidateCalls()` incrementa o token e zera `callPending`/`verifying`/Timer.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "set_active_contract or verification_lifecycle"`
  - Critério: os dois testes ficam verdes (GREEN); `SetActive(false)` durante a verificação para o spinner antes do reply; nenhum estado de verificação no barramento.
  - Estimativa: 25min

- [ ] **T-17**: Implementar `quitDaemon` como kill switch
  - Arquivo: `plasmoid/contents/ui/main.qml` (seção 9, parte 3)
  - Contrato: `design_e5.md` §4.2, §6.5 e ADR-08 — sem dono, retorna imediatamente (o menu só fecha); senão chama `stopVerification()`, envia `SetActive(false)` e, ao terminar (sucesso ou erro), se o daemon ainda estiver registrado, envia `Quit`; falhas são silenciosas para o usuário e apenas `console.warn`; não remove o widget e não abre diálogo.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "quit_contract"`
  - Critério: `test_main_qml_quit_contract` verde (GREEN); `stopVerification` antes de `Quit`; `SetActive(false)` antes de `Quit`; guarda por `registered`.
  - Estimativa: 10min

- [ ] **T-18**: Implementar handlers de watcher e `Component.onCompleted`
  - Arquivo: `plasmoid/contents/ui/main.qml` (seções 9–10)
  - Contrato: `design_e5.md` §4.9 e §6.6 — `dbusStateChanged(state)` normaliza `String(state)`, chama `applyState(value)` e, se `value === "error"`, `requestLastError()`; `onRegisteredChanged` chama `syncFromDaemon()` se `registered`, senão `invalidateCalls()` + `applyState("off")` + `lastError = ""`; `Component.onCompleted` (último bloco do arquivo) chama `syncFromDaemon()` se `registered`, senão `applyState("off")`. Nenhuma chamada D-Bus em `Component.onDestruction`; nenhum `GetState` sem dono.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "state_model or watchers_precede"`
  - Critério: os dois testes ficam verdes (GREEN); `Component.onCompleted` é o último bloco; ordem heurística dos watchers antes de `GetState` confirmada.
  - Estimativa: 20min

### 5. Assets e testes estáticos (TDD)

- [ ] **T-19**: Escrever os testes RED dos assets e do escopo do pacote
  - Arquivo: `tests/unit/test_plasmoid_assets.py` (append)
  - Testes:
    - `test_assets_are_valid_xml` — `plasmoid/contents/ui/assets/deskawake.svg` e `spinner.svg` existem, são XML válido (`xml.etree.ElementTree.parse`), com `width/height="22"` e `viewBox="0 0 22 22"`.
    - `test_assets_are_verbatim` — bytes idênticos a `docs/implementation/visual/assets/*.svg`; `pytest.skip` se o diretório de docs não existir.
    - `test_assets_sha256` — SHA-256 do pacote igual aos hashes aprovados gravados no teste: `deskawake.svg` = `2c35dd2469253e0ebac24ff25f5bdd08fb0d17508c10ac98c80a09ee09fbc7d1`; `spinner.svg` = `fc7746a98c78983b17cace66a975428b4febc08986168516cc6d592d53b8eb64`.
    - `test_package_excludes_config_and_translations` — não existe `plasmoid/contents/config/`, `config.qml`, `Messages.sh` nem diretório `po/`; o pacote contém somente `metadata.json`, `contents/ui/main.qml` e os dois SVGs.
  - Comando: `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "assets or excludes"`
  - Critério: falha (RED) — `FileNotFoundError` para `plasmoid/contents/ui/assets/deskawake.svg`.
  - Estimativa: 15min

- [ ] **T-20**: Copiar os SVGs aprovados para o pacote
  - Comandos:
    - `mkdir -p plasmoid/contents/ui/assets`
    - `cp docs/implementation/visual/assets/deskawake.svg plasmoid/contents/ui/assets/deskawake.svg`
    - `cp docs/implementation/visual/assets/spinner.svg plasmoid/contents/ui/assets/spinner.svg`
    - `cmp docs/implementation/visual/assets/deskawake.svg plasmoid/contents/ui/assets/deskawake.svg && cmp docs/implementation/visual/assets/spinner.svg plasmoid/contents/ui/assets/spinner.svg`
    - `sha256sum plasmoid/contents/ui/assets/*.svg`
    - `python3 -m pytest tests/unit/test_plasmoid_assets.py -v -k "assets or excludes"`
  - Critério: `cmp` exit 0; hashes idênticos aos aprovados; testes de T-19 verdes (GREEN). **Não** redesenhar, simplificar ou recolorir os arquivos.
  - Estimativa: 5min

### 6. Gate automatizado e smoke do pacote

- [ ] **T-21**: Rodar o gate automatizado completo da E5
  - Comandos:
    - `python3 -m pytest tests/unit/test_plasmoid_assets.py -v` ⇒ 0 failures
    - `python3 -m pytest tests/unit -q` ⇒ 0 failures (192 nesta branch; 233 com E4)
    - `python3 -m compileall -q tests/unit/test_plasmoid_assets.py` ⇒ exit 0
    - `grep -RInE "import (gi|dbus)|from gi|from dbus|PyQt|PySide" tests/unit/test_plasmoid_assets.py` ⇒ sem saída
  - Critério: todos exit 0; nenhum teste executa QML, abre display ou fala com o barramento; `tests/conftest.py` intocado.
  - Estimativa: 15min

- [ ] **T-22**: Fazer o smoke de instalação e carregamento do pacote
  - Pré-condição: sessão Plasma 6.6.7/Wayland nesta máquina.
  - Comandos (o primeiro que se aplicar):
    - `kpackagetool6 -t Plasma/Applet -i ./plasmoid` (primeira instalação) ou `kpackagetool6 -t Plasma/Applet -u ./plasmoid` (upgrade)
    - `test -d ~/.local/share/plasma/plasmoids/org.local.deskawake` ⇒ exit 0
    - `kpackagetool6 -t Plasma/Applet -s org.local.deskawake` ⇒ metadados do pacote
    - `plasmawindowed org.local.deskawake` ⇒ carrega sem erros de QML no stderr (a janela não prova 124×42; fechar após o smoke)
  - Critério: pacote instalado apenas no diretório de plasmoids (nunca em `~/.local/share/kpackage/generic/`); `plasmawindowed` carrega sem erro; o pacote permanece instalado para a checklist manual. **Nunca** omitir `-t Plasma/Applet`.
  - Estimativa: 20min

### 7. Validação manual (usuário, nesta máquina)

- [ ] **T-23**: Checklist manual — instalação, visual, layout e tema
  - Pré-condição: T-22 concluída; daemon da E2 disponível; widget adicionado à área de trabalho por “Adicionar widgets”.
  - Passos (design §9.2, não-destrutivos):
    - Pacote em “Adicionar widgets”; `contents/ui/assets/` presente no diretório instalado; símbolo e spinner aparecem.
    - Pílula 124×42, cantos arredondados, borda fina, sem gradiente/sombra; atrás das janelas e visível com a área de trabalho à mostra.
    - Símbolo 22×22, nome “DeskAwake” completo em 10 px semibold, toggle 32×18; sem estouro em 100%, 125% e 150%.
    - Símbolo/spinner neutros em `on`/`off`/`error`; só o trilho do toggle usa menta/cinza/vermelho.
    - Tema BreezeDark ↔ claro: superfície/texto/fonte acompanham; cores de estado fixas e legíveis.
    - Hover na pílula aumenta a borda (alpha ~0,28) sem consumir clique nem impedir o arrasto.
    - Tooltip em `error` no desktop mostra “DeskAwake” + motivo, em texto plano.
  - Critério: cada item marcado OK ou com desvio descrito; resultado colado no corpo do PR. Se a máquina não estiver disponível, registrar a pendência (bloqueia o merge, não o gate automatizado).
  - Estimativa: 30min

- [ ] **T-24**: Checklist manual — interação, menu, spinner e verificação
  - Passos (design §9.2, não-destrutivos):
    - Press-and-hold na pílula move o widget; “Widgets travados” impede o movimento; anotar o comportamento ao pressionar o toggle (a área de 32×18 consome o clique; o arrasto é garantido no restante).
    - Clique rápido no toggle alterna e não move; clique fora do toggle não altera; toggle reflete `on/off/error` em tempo real, sem polling.
    - Menu: `Ativar/Desativar` (rótulo dinâmico), `Sair` e itens nativos do Plasma; sem `Tema` e sem `Iniciar com o sistema`; `Configurar` aparece e, sem `config.qml`, abre a janela nativa sem categorias (registrar a limitação para a E6).
    - `Sair` com ON libera imediatamente (`systemd-inhibit --list` sem `deskawake`; `ActiveInhibitions` sem `deskawake`) e o widget continua na área de trabalho; remover o Plasmoid não desliga o estado de outros clientes.
    - Durante `SetActive`: spinner de duas flechas no slot do símbolo, toggle bloqueado e preservando o último estado, sem âmbar.
    - Durante a verificação de ~6 s: trilho menta, spinner no slot, toggle habilitado; desligar antes dos 6 s cancela sem `error`; falha após ~6 s vira `error` + trilho vermelho + tooltip com `GetLastError()`.
    - Não há animação contínua em repouso.
  - Critério: cada item marcado OK ou com desvio descrito; resultado colado no PR.
  - Estimativa: 30min

- [ ] **T-25**: Checklist manual — backend KDE, erro, liveness e guarda Wayland
  - Passos (design §9.2):
    - Com ON, após ~6 s, `PolicyAgent.ActiveInhibitions` contém a entrada `deskawake` e `HasInhibition(4)` vira `true`; **não** usar `CanSuspend`.
    - `systemctl --user restart plasma-powerdevil` com ON ⇒ `error` + `StateChanged`; ao voltar, re-adquire e volta a `on` após ~6 s, sem rajada.
    - Estado `error` mostra o motivo no tooltip e libera o `systemd-inhibit`.
    - `deskawake ui` recusa Wayland com mensagem; `--force` abre para depuração.
    - Tampa e suspensão manual continuam suspendendo com ON — **destrutivo/opcional**; marcar explicitamente como não executado se não for seguro.
  - Comandos de apoio:
    - `gdbus call --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent --method org.freedesktop.DBus.Properties.Get org.kde.Solid.PowerManagement.PolicyAgent ActiveInhibitions`
    - `gdbus call --session --dest org.kde.Solid.PowerManagement --object-path /org/kde/Solid/PowerManagement/PolicyAgent --method org.kde.Solid.PowerManagement.PolicyAgent.HasInhibition 4`
  - Critério: itens não-destrutivos marcados OK ou com desvio; destrutivos explicitamente marcados como não executados; resultado colado no PR.
  - Estimativa: 30min

### 8. Auditoria e entrega

- [ ] **T-26**: Auditar escopo, higiene e dependências
  - Comandos:
    - `find plasmoid -type f | sort` ⇒ exatamente `metadata.json`, `contents/ui/main.qml`, `contents/ui/assets/deskawake.svg` e `contents/ui/assets/spinner.svg`
    - `grep -RInE "AC-[0-9]|T-[0-9]|design_e5|tasks_e5|spec\\.md|DELIVERY_MAP" plasmoid tests/unit/test_plasmoid_assets.py` ⇒ sem saída
    - `git diff --stat -- core bin ui_gtk assets pyproject.toml` ⇒ sem saída
    - `grep -RInE "config\.json|Plasma5Support|gdbus|callBlocking|StartServiceByName|Iniciar com o sistema|Tema ▸" plasmoid` ⇒ sem saída
    - `git status --short` ⇒ apenas os 5 arquivos da entrega (+ `docs/implementation/`, fora do stage)
  - Critério: todos conforme acima; nenhuma dependência nova; nenhum artefato de spec em código/comentários; nenhuma mudança em `core/`, `bin/`, `ui_gtk/`, `assets/` ou `pyproject.toml`.
  - Estimativa: 15min

- [ ] **T-27**: Preparar commit e PR somente com a entrega
  - Comandos:
    - `git add plasmoid/metadata.json plasmoid/contents/ui/main.qml plasmoid/contents/ui/assets/deskawake.svg plasmoid/contents/ui/assets/spinner.svg tests/unit/test_plasmoid_assets.py`
    - `git diff --cached --name-only` ⇒ exatamente os 5 arquivos
    - `python3 -m pytest tests/unit -q` ⇒ gate verde
    - `git commit -m "feat(e5): Plasmoid para Plasma 6.6"`
    - `git push -u origin feat/e5-plasmoid-kde`
    - `gh pr create --base feat/e3-cli-launcher --head feat/e5-plasmoid-kde --title "feat(e5): Plasmoid para Plasma 6.6" --body "<corpo no template do DELIVERY_MAP §0.2>"`
    - `gh pr view --json baseRefName,headRefName,files --jq '{base: .baseRefName, head: .headRefName, files: [.files[].path]}'` ⇒ base `feat/e3-cli-launcher`, head `feat/e5-plasmoid-kde` e apenas os 5 arquivos
  - Corpo do PR: gate com comando/resultado (teste estático + suíte + `kpackagetool6 -t` + `plasmawindowed`), checklist manual preenchida (T-23–T-25), fora de escopo (E6) e riscos residuais (design §10); **não** citar `spec.md`, `design_e5.md`, `tasks_e5.md`, `docs/implementation/visual/` nem IDs `AC-*`/`T-*`.
  - Critério: PR contém apenas os 5 arquivos; base é a branch da E3 (empilhamento), **não** `main`, sem retarget sem confirmação; `docs/implementation/` e READMEs fora do stage/PR de código. **Nunca** usar `git add -A`/`git add .`.
  - Estimativa: 20min

## Mapeamento AC → Tasks

Os critérios vêm do `DELIVERY_MAP.md` §E5.4, da §9.1/§9.2 do `design_e5.md` e do gate G-E5.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-01 — `metadata.json` válido, `KPackageStructure`, `Id`, Plasma ≥ 6.4, campos e licença MIT; sem API legada/`package/` | T-04, T-05 |
| AC-02 — `main.qml` sem `Plasma5Support`, `gdbus`, `DataSource`, `callBlocking`, `setInterval`, `config.json`, `StartServiceByName` e GTK | T-06, T-08 |
| AC-03 — Transporte nativo presente (`workspace.dbus`, `asyncCall`, `SignalWatcher`, `DBusServiceWatcher`) e `DBus.BusType.Session` qualificado | T-06, T-09 |
| AC-04 — 124×42 fixo pelas seis restrições `Layout.*`, `NoBackground` e sem `width: 124` solto | T-06, T-08 |
| AC-05 — Slots internos fixos: símbolo 22×22, nome 58 px, toggle 32×18 | T-06, T-10 |
| AC-06 — Superfície/texto/fonte do `Kirigami.Theme`; 88% de opacidade; borda 0,18/0,28; nome 10 px semibold com elide | T-07, T-10, T-11 |
| AC-07 — Cores de estado exatas `#80D9A4`/`#929DA5`/`#E47F7F` e toggle como único indicador | T-07, T-12 |
| AC-08 — `SetActive` com `"(b)"`/`DBus.bool`, `GetState`, `GetLastError`, `verifyWindowMs = 6000`; sem `Toggle`/auto-start | T-07, T-15 |
| AC-09 — `Sair` com guarda por dono, `stopVerification`, `SetActive(false)` → `Quit()` | T-07, T-17 |
| AC-10 — Spinner `960 ms`/linear/infinito, visível e animando só em `callPending` ou `verifying` | T-07, T-13 |
| AC-11 — Tooltip via `PlasmaCore.ToolTipArea`, hover por `containsMouse`, `Text.PlainText`, motivo em `error` | T-07, T-10 |
| AC-12 — Menu `contextualActions` com rótulo dinâmico, ações bloqueadas em voo e `Sair`; sem itens exclusivos do GTK | T-07, T-14 |
| AC-13 — Watchers antes de `GetState`, estado em memória e `Component.onCompleted` por último | T-07, T-18 |
| AC-14 — SVGs válidos, verbatim, SHA-256 aprovado; pacote sem config/traduções | T-19, T-20 |
| AC-15 — `test_plasmoid_assets.py` inteiro verde, sem GUI/barramento | T-21 |
| AC-16 — `tests/unit` sem regressão (192; 233 com E4) | T-03, T-21 |
| AC-17 — Instalação com `-t Plasma/Applet` no diretório correto e smoke sem erro de QML | T-22 |
| AC-18 — Nenhuma mudança em `core/`/`bin/`/`ui_gtk/`; PR só com os 5 arquivos e sem artefatos de spec/docs | T-26, T-27 |
| AC-M01 — Manual: instalação/adicionar widget, 124×42 atrás das janelas, geometria, escala e tema | T-23 |
| AC-M02 — Manual: arrasto nativo/travado, clique no toggle, estado em tempo real e remoção | T-24 |
| AC-M03 — Manual: menu enxuto, limitação do `Configurar` e `Sair` como kill switch | T-24 |
| AC-M04 — Manual: spinner na chamada e na verificação, cancelamento, erro com tooltip, sem animação em repouso | T-24 |
| AC-M05 — Manual: `ActiveInhibitions`/`HasInhibition(4)` após ~6 s, queda/retorno do PowerDevil, `deskawake ui` no Wayland; tampa/suspensão destrutivas opcionais | T-25 |

## Cobertura das decisões do design

| Decisão | Tasks que a fixam |
|---|---|
| §1.1-1 — assets aprovados copiados para o pacote e renderizados com `Kirigami.Icon`/`isMask` | T-11, T-13, T-19, T-20 |
| §1.1-2 — nome 10 px semibold com a família de `Kirigami.Theme.defaultFont` | T-11 |
| §1.1-3 — superfície `backgroundColor` a 88% e borda derivada de `textColor` (0,18/0,28) | T-10 |
| §1.1-4 — verificação local de 6000 ms só após ON iniciado pelo widget | T-09, T-15, T-16 |
| ADR-01 — `PlasmoidItem` como full representation, 124×42 e `NoBackground` | T-08 |
| ADR-02 — transporte nativo com `SetActive`, assinatura explícita e callbacks | T-09, T-15, T-16 |
| ADR-03 — watchers antes de consultar, geração de chamadas e liveness sem rajada | T-09, T-18 |
| ADR-04 — spinner de verificação local em duas flags | T-13, T-16 |
| ADR-05 — toggle customizado 32×18, `MouseArea` só no toggle e arrasto nativo | T-10, T-12 |
| ADR-06 — tema para superfície/texto/fonte, cores de estado fixas e nome 10 px | T-10, T-11, T-12 |
| ADR-07 — assets copiados/recoloridos por máscara e rotação de 960 ms | T-13, T-19, T-20 |
| ADR-08 — menu via `contextualActions`; `Sair` é kill switch sem remover o widget | T-14, T-17 |
| ADR-09 — tooltip nativo via `PlasmaCore.ToolTipArea` no desktop | T-10 |
| ADR-10 — testes estáticos; nenhuma GUI automatizada | T-04, T-06, T-07, T-19, T-21 |
| ADR-11 — metadados neutros e mínimo de API 6.4 | T-05 |
| ADR-12 — strings pt-BR literais, sem `.po` e sem config UI | T-07, T-14, T-19 |

## Notas de execução

1. **RED obrigatório:** em cada task de teste, rodar o comando e confirmar a falha esperada (arquivo ausente ou token ainda não presente). Se um teste passar antes da implementação, é regressão — registrar e não “implementar” o que já existe.
2. **Sem GUI automatizada:** a suíte não executa QML, não abre display e não fala com o barramento real. `plasmawindowed` é smoke manual de carregamento e **não** prova 124×42; tamanho, arrasto, tema, spinner e backend só fecham na checklist (§9.2 do design).
3. **Não alterar `tests/conftest.py`** nem os testes E1–E4; `test_plasmoid_assets.py` é o único arquivo novo de teste.
4. **Assets verbatim:** os SVGs do pacote são cópias exatas de `docs/implementation/visual/assets/`; qualquer redesenho exige nova aprovação visual. O teste compara bytes quando os docs existem e sempre valida o SHA-256 gravado.
5. **Nunca usar `git add -A`/`git add .`:** `docs/implementation/`, `README` e artefatos gerados ficam fora do PR de código; a documentação vai em commit/PR `docs:` separado.
6. **Sem artefatos de spec no código:** `plasmoid/` e `tests/unit/test_plasmoid_assets.py` não podem citar `AC-*`, `T-*`, `design_e5.md`, `tasks_e5.md`, `spec.md`, `DELIVERY_MAP.md` ou `visual/` em código, comentários, commits ou corpo do PR.
7. **Fora de escopo intocável:** nenhuma alteração em `core/config.py`, `core/environment.py`, `core/inhibitors.py`, `core/state.py`, `core/daemon.py`, `core/cli.py`, `bin/deskawake`, `ui_gtk/`, `assets/`, `tests/conftest.py` ou no contrato D-Bus da E2.
8. **PR empilhado:** E5 → E3 (base `feat/e3-cli-launcher`), em paralelo à E4. Não retargetar para `main` sem confirmação; a E6 só abre depois de E4 e E5 mergeadas.
9. **Documento transitório:** este `tasks_e5.md` (em `docs/implementation/`) é o escopo canônico do `/implement`; não entra no PR de código nem é citado em código.

## Execução real (2026-11-20)

Status: T-01–T-22 e T-26 executadas; T-23–T-25 (checklist manual) pendentes; T-27 com commits feitos e push/PR pendentes. `tests/unit` = **219 passed** (192 + **27** novos); `tests/integration` mantém 14 falhas pré-existentes de liberação de `UnInhibit`, fora do escopo da E5. Commits: `5f90c78` (entrega), `594e4b9` (docs), `61b18ff` (fix da pílula/estado).

Achados da validação no Plasma real (corrigidos antes do commit final):

| Achado | Evidência | Correção |
|---|---|---|
| Célula do containment maior que a pílula | `ItemGeometries=Applet-134:96,1056,128,96`; `root.width/height=128/96`; o `AppletsLayout` usa `minimumItemHeight = gridUnit*3` | Pílula visível fixada em 124×42, centralizada no `PlasmoidItem` (`pillWidth`/`pillHeight`); as seis `Layout.*` permanecem na raiz. Teste: `test_main_qml_keeps_pill_compact_inside_containment_cell`. |
| `StateChanged` chega como objeto `String` | O handler registrava `on`, mas `applyState` saía na validação estrita e o trilho ficava cinza | `dbusStateChanged` e `applyState` normalizam com `String(...)`; `error` chama `requestLastError()`. Testes: `test_main_qml_normalizes_signal_payload` e `test_main_qml_error_state_refreshes_last_error`. |
| Nome elidindo no slot de 58 px | Noto Sans DemiBold resolve para Bold e mede 58,1 px em 10 px | `font.letterSpacing: -0.05`; validar 100%/125%/150% na T-23. |

Validação manual já feita nesta sessão: widget instalado, adicionado ao desktop, pílula 124×42 confirmada por screenshot, `on` → trilho menta e `off` → cinza via `StateChanged`; a checklist T-23–T-25 continua sendo a validação oficial do usuário.
