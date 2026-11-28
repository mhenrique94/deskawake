# Design: E6 — UI GTK/MATE: Ajustes, Paridade Visual e Créditos

**Feature:** DeskAwake — E6 | **Data:** 2026-11-21 | **Status:** Aprovado — reprogramação E6/E7/E8
**Referências:** [`spec.md`](spec.md) (decisões 8, 14, 16, 19, 33 e 34–38; “Aparência”, “Tarefas de
implementação” 8–9, “Verificação”), [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E6,
[`design_e4.md`](design_e4.md), [`design_e5.md`](design_e5.md),
[`visual/design_visual_aprovado.md`](visual/design_visual_aprovado.md) e a validação MATE de
21/11/2026 (achados A1–A7).

> **Escopo deste documento:** somente a E6. Ela altera `ui_gtk/` e `core/__init__.py` (apenas a
> constante de versão), acrescenta testes estáticos e emenda a documentação. **Não** altera o
> contrato D-Bus, o daemon, a CLI, o `config.json`, os backends, o QML do Plasmoid nem o layout do
> instalador. O instalador/verificação/READMEs são a **E7**; empacotamento é a **E8**. Em caso de
> conflito com a `spec.md`, a `spec.md` vence — e a E6 emenda a spec nos pontos que ela própria
> decidiu (decisões 34–38).

> **Reprogramação (2026-11-21).** A entrega antes chamada “E6 — instalador” foi dividida:
> **E6 = UI GTK/MATE** (este documento), **E7 = instalação/verificação/docs** e **E8 =
> distribuição/empacotamento** (placeholder). O antigo `design_e6.md` de instalador migrou para
> [`design_e7.md`](design_e7.md); referências históricas a “E6 instalador” em E1–E5 devem ser lidas
> como E7.

---

## 1. Contexto e limite da entrega

A E4 entregou um widget GTK funcional e validado na maior parte do contrato: janela 124×42 sem
decoração, hints EWMH corretos, arrasto, spinner, ON/OFF/`error`, `Sair`, autostart, tema e
compositor. A validação MATE de 21/11/2026 confirmou esses itens, mas deixou **A1–A7** em aberto e
revelou que o acabamento visual do GTK ficou atrás do Plasmoid repaginado na E5 (chip adaptativo,
hamburguer, hover/pressed, tooltip estruturado, tipografia escalável). A E6 fecha essa diferença
**sem copiar o que é específico do Plasma** e adiciona os créditos pedidos pelo autor.

**Inclui (e só isso):**

| Arquivo | Responsabilidade |
|---|---|
| `ui_gtk/widget.py` | A1 (“mostrar área de trabalho”), tooltip estruturado, ciclo do `last_error`, retry de assinatura D-Bus, acessibilidade, item `Sobre` e diálogo |
| `ui_gtk/theme.py` | knob do toggle com contraste fixo, hover/pressed e cursor do toggle; helpers puros de formatação de erro |
| `core/__init__.py` | `__version__ = "0.1.0"` (fonte única) |
| `tests/unit/test_version.py` | sincronia `core.__version__` × `pyproject.toml` × `plasmoid/metadata.json` |
| `tests/unit/test_theme.py` (extensão) | tokens do knob/hover e formatação do tooltip sem display |
| `tests/unit/test_ui_assets.py` (extensão) | contrato estático do menu/`Sobre` e ausência de hints proibidos |
| `spec.md` / docs | emendas das decisões 8, 14, 16, 19 e novas 34–38 |

**Explicitamente fora da E6:**

- Redimensionamento, hamburguer, chip adaptativo ao wallpaper, sombra, spinner de verificação de
  ~6 s e qualquer mudança de QML — são específicos do Plasmoid e continuam na E5.
- Instalação, autostart instalado, `.service`, `verify.sh`, READMEs e testes de scripts (E7).
- `.deb`, GitHub Releases, CI e versionamento de release (E8).
- Mudanças de backend, daemon, CLI, contrato D-Bus ou `config.json`.
- Testes automatizados de GUI; teclado como requisito de acessibilidade.
- Traduções `.po`.

### 1.1 Decisões confirmadas pelo usuário (2026-11-21)

| # | Tema | Decisão |
|---|---|---|
| 1 | Roadmap | **E6 = UI GTK/MATE**, **E7 = instalação/verificação/docs**, **E8 = distribuição** (placeholder). Um PR por entrega; E6 nasce da `main`. |
| 2 | Paridade | **Linguagem visual comum, não idêntica**: o GTK herda o nível de acabamento do KDE atual, mas mantém 124×42 fixo, menu completo e ausência de sampling de wallpaper. |
| 3 | A1 | **Tentar corrigir** “mostrar área de trabalho” com observação de `_NET_SHOWING_DESKTOP`; se causar flicker, quebrar arrasto ou exigir hint proibido, **documentar a limitação** e remover o observador. |
| 4 | Pacote | A1, knob (V10), hover/pressed/cursor (V12), tooltip (V13), `last_error` (F5), retry D-Bus (F6), acessibilidade parcial (F13), reteste do submenu `Tema` (A6), correção documental 10×12 px (V2), `Sobre`/créditos e checklist MATE. |
| 5 | Créditos | `Gtk.AboutDialog` no GTK com autor/empresa e licença no corpo e links para o repositório e o site (E6; sem botão Créditos); `metadata.json` com `Authors`/`Website`/`Copyright` (linha legal sem ©) na E7; `LICENSE` com razão social + CNPJ na E7; README com a linha legal na E7. |
| 6 | Versão | Semver **0.1.0**, fonte única em `core/__init__.py`, sincronia testada com `pyproject.toml` e `metadata.json`. |
| 7 | KDE intocado | Nenhuma mudança de QML. Alterações em arquivos compartilhados (`metadata.json`, `assets/`) são aditivas e passam pelos testes do Plasmoid. |
| 8 | Spec | Emendar a `spec.md` em vez de congelá-la; decisões 34–38 registram créditos, versão, paridade e a nova divisão. |

### 1.2 Estado atual e baseline

- **E1–E5 mergeadas na `main`** (PRs #4, #5, #7, #8 e #10). O Plasmoid foi repaginado no commit
  `78b0961`; o README já descreve o visual novo do KDE.
- **Baseline medido na `main` pós-merges (2026-11-21):** `python3 -m pytest tests/unit -q` ⇒
  **267 passed**; `dbus-run-session -- python3 -m pytest tests/integration -q` ⇒ **34 passed,
  1 skipped** (o skip é o teste `@pytest.mark.slow`). A E6 deve preservar esse baseline e somar os
  testes novos.
- **MATE validado em 21/11/2026** na máquina Mint 22.3 MATE/X11 (GTK 3.24.41, Marco composto, tema
  `Squared`, um monitor ativo): passaram geometria/hints, arrasto, spinner, estados, tema,
  compositor, menu, autostart, `Sair` e `kill -9`. Pendências A1–A7 na §1.3.
- **KDE validado** (backend e GUI do Plasmoid) no Kubuntu 26.04.1 / Plasma 6.6.7 / Wayland. A E6
  **não altera** o Plasmoid; o achado de sombra é resolvido por documentação (a sombra é parte do
  design aprovado da E5), não por código.
- **Ferramentas nesta máquina:** Ubuntu 26.04.1 + Plasma 6.6.7 (Wayland), Bash 5.3.9, GTK 3.24,
  `gdbus`, `systemd-inhibit`; a validação manual da E6 é no Mint/MATE.

### 1.3 Achados herdados da validação MATE (21/11/2026)

| # | Achado | Tratamento na E6 |
|---|---|---|
| A1 | Ctrl+Alt+D adiciona `_NET_WM_STATE_HIDDEN`; o widget some e volta ao restaurar. | **Tentado** com observação de `_NET_SHOWING_DESKTOP`; fallback acionado no spike (§3.1). |
| A2 | `error` por queda de backend preserva o filho do `systemd-inhibit` e libera o inibidor de tela. | **Documentação/verificação** na E7 e na spec (já corrigida); a E6 só mantém o comportamento. |
| A3 | `IsInhibited(8)` não existe no mate-screensaver 1.26.2. | **E7** (`verify.sh` usa `GetInhibitors` + `mate-screensaver-command -q`); docs/spec já corrigidos. |
| A4 | `gtk-application-prefer-dark-theme` não existe em `org.mate.interface`. | **E7** (README); o código já lê `Gtk.Settings` sem depender do schema. |
| A5 | `idle-delay` é lido no login; lock é destrutivo/opcional. | **E7** (README/checklist); validação em sessão nova. |
| A6 | Submenu `Tema` às vezes fecha sob XTest. | **Reteste com mouse real** na E6; corrigir só se reproduzir (§3.8). |
| A7 | Logout, monitor externo e bloqueio de tela não exercitados. | **E6** (checklist MATE) e **E7** (README/PR); registrar o que não for executado. |

---

## 2. Arquitetura

### 2.1 Componentes e pontos de entrada

- **`ui_gtk/widget.py`**
  - `DeskAwakeWindow` (ou classe equivalente) mantém o estado visual, o menu e o diálogo `Sobre`.
  - A1: filtro de eventos na janela raiz para `PropertyChangeMask`; leitura de
    `_NET_SHOWING_DESKTOP`; reexibição controlada com guarda contra loop.
  - Tooltip: `format_error_tooltip(last_error)` (helper puro em `theme.py`) + `set_tooltip_markup`
    com escape.
  - `last_error`: limpo ao sair de `error`; relido ao abrir o menu em `error`.
  - D-Bus: `_subscribe_with_retry()` agenda novas tentativas com `GLib.timeout_add_seconds` até
    conseguir assinar `StateChanged`/`NameOwnerChanged`; cancela no `destroy`.
  - Acessibilidade: `get_accessible().set_name(...)` na janela e no switch.
- **`ui_gtk/theme.py`**
  - Tokens `KNOB_COLOR = "#20252B"`, bordas de hover/pressed; CSS do switch com knob fixo.
  - `format_error_tooltip(error: str) -> str` com `GLib.markup_escape_text`; fallback
    `DeskAwake: erro sem detalhes`.
- **`core/__init__.py`**
  - `__version__ = "0.1.0"`; nenhum import novo.
- **Testes estáticos**
  - `tests/unit/test_version.py`: regex de semver + sincronia com `pyproject.toml` e
    `plasmoid/metadata.json`.
  - `tests/unit/test_theme.py`: tokens e formatação pura.
  - `tests/unit/test_ui_assets.py`: menu com `Sobre`, ausência de `WindowTypeHint.DESKTOP` e do
    observador de `_NET_SHOWING_DESKTOP` (fallback), presença de `pointer`,
    `get_accessible().set_name` e `markup_escape_text`.

### 2.2 Fluxo do menu

```
clique direito / (futuro botão) → Menu
├── Ativar | Desativar        (dinâmico; desabilitado em voo)
├── Tema ▸                    (Automático / Claro / Escuro; marca o ativo)
├── Iniciar com o sistema ☑   (lê/escreve o autostart do widget)
├── Sobre o DeskAwake…        (Gtk.AboutDialog)
└── Sair                      (SetActive(false) → Quit() → fecha)
```

`Sobre` fica **antes** de `Sair` para preservar `Sair` como último item e kill switch.

---

## 3. Design detalhado

### 3.1 A1 — “Mostrar área de trabalho” (Ctrl+Alt+D)

**Problema:** o Marco, ao mostrar o desktop, adiciona `_NET_WM_STATE_HIDDEN` a janelas normais
(inclusive `UTILITY` com `BELOW`/`STICKY`). O widget some enquanto o desktop está à mostra.

**Abordagem:**

1. Obter a janela raiz (`Gdk.get_default_root_window()`) e adicionar filtro para
   `Gdk.EventMask.PROPERTY_CHANGE_MASK`.
2. No evento de propriedade, comparar `event.atom` com `Gdk.atom_intern("_NET_SHOWING_DESKTOP", False)`.
3. Se o valor inteiro for `1` e o widget estiver oculto/iconificado, chamar `deiconify()` e
   reaplicar os hints (`keep_below`, `skip_taskbar`, `skip_pager`, `stick()`), **sem** `present()`
   que furta foco; `set_accept_focus(False)` já está aplicado.
4. Agendar uma única reexibição por transição com `GLib.timeout_add(100, ...)`; se a propriedade
   continuar `1` e o WM ocultar de novo, **não** entrar em loop: registrar em log e desistir da
   correção naquela sessão.
5. Quando `_NET_SHOWING_DESKTOP` voltar a `0`, não fazer nada; o WM restaura normalmente.

**Critério de aceite (manual):** com Ctrl+Alt+D, o widget permanece visível; clique e arrasto
continuam funcionando; sem flicker perceptível; comportamento igual com compositor ligado/desligado.
**Fallback:** se o WM reocultar, houver flicker ou o arrasto quebrar, remover o observador e
documentar a limitação no README (E7) e na spec; **nunca** trocar para `WindowTypeHint.DESKTOP`.

**Resultado do spike (Mint 22.3 MATE, 21/11/2026): fallback acionado.** Com Ctrl+Alt+D
(`wmctrl -k on`), o Marco define `WM_STATE=Iconic` e `_NET_WM_STATE_HIDDEN` no widget.
`deiconify()`/`gdk_window.show()` são ignorados enquanto `_NET_SHOWING_DESKTOP=1`; `present()`
reexibe o widget, mas zera `_NET_SHOWING_DESKTOP` e restaura **todas** as janelas. O observador
foi removido; o widget permanece `UTILITY` e a limitação vai para o README da E7.

### 3.2 Knob do toggle (V10)

Hoje o knob usa a cor da superfície da variante; no tema claro ele fica quase branco sobre o trilho
cinza. Passar a usar **`#20252B` fixo** (mesmo valor do Plasmoid) nas duas variantes:

```css
switch slider {
  background-color: #20252B;
  border: 1px solid rgba(255, 255, 255, 0.14);
}
```

O trilho continua usando as cores de estado (`#80D9A4`/`#929DA5`/`#E47F7F`). Teste estático garante
que `KNOB_COLOR` não depende da variante.

### 3.3 Hover/pressed e cursor do toggle (V12)

- `switch:hover` e `switch:active` ganham realce de borda/trilho discreto (alpha ~0,28/0,34),
  consistente com o hover da pílula.
- Cursor `pointer` no switch: no `realize`, obter `Gdk.Cursor.new_from_name(display, "pointer")` e
  aplicar em `switch.get_window().set_cursor(cursor)`; guardar a referência para não coletar.
- Sem animação contínua; transições curtas são opcionais e ficam no CSS quando o GTK suportar.

### 3.4 Tooltip (V13)

- `format_error_tooltip(error)` devolve markup:
  - com erro: `<b>DeskAwake</b>\n<erro escapado>`;
  - sem erro: string vazia (tooltip removido).
- `set_tooltip_markup(...)` em vez de `set_tooltip_text`, com `GLib.markup_escape_text` no motivo.
- Ao entrar em `error`, buscar `GetLastError()`; fallback `DeskAwake: erro sem detalhes`.
- Ao sair de `error`, limpar o tooltip e o `last_error` (F5).

### 3.5 Ciclo do `last_error` (F5)

- `self._last_error` é limpo em toda transição para `on`/`off`.
- Em `error`, o valor é atualizado por `GetLastError()` e reutilizado no menu/tooltip.
- Abrir o menu em `error` relê `GetLastError()` (já existe) e atualiza o tooltip; se a leitura
  falhar, mantém o valor anterior com fallback.

### 3.6 Retry de assinatura D-Bus (F6)

- `_subscribe()` tenta assinar `StateChanged` e `NameOwnerChanged`; se o barramento falhar, agenda
  `GLib.timeout_add_seconds(2, self._retry_subscribe)` até 5 tentativas.
- Sucesso cancela o timer; `destroy` cancela e remove os receptores.
- Não fazer polling de estado; o retry é só de assinatura.

### 3.7 Acessibilidade parcial (F13)

- `self.get_accessible().set_name("DeskAwake")`.
- `switch.get_accessible().set_name("DeskAwake: ativar/desativar")`.
- Não habilitar foco de teclado nem `accept_focus`; o contrato continua mouse-first. O objetivo é
  leitor de tela, não navegação por Tab.

### 3.8 Reteste do submenu `Tema` (A6)

Repetir a seleção com mouse real no Mint. Se o submenu fechar corretamente, A6 fecha como “não
reproduzido”. Se reproduzir, investigar a interação entre `Gtk.Menu` e o arrasto da janela
(provável consumo de `button-release`); a correção entra na E6 e é coberta pela checklist.

### 3.9 Correção documental 10 px × 12 px (V2)

A `spec.md` diz “nome 12 px semibold” na “Aparência ▸ GTK”, mas o design visual aprovado e a
implementação usam **10 px semibold**. A E6 emenda a spec para 10 px e registra a decisão 36
(paridade visual). Nenhuma mudança de código.

### 3.10 `Sobre o DeskAwake` e créditos

- Item `Sobre o DeskAwake…` no menu, antes de `Sair`.
- `Gtk.AboutDialog` com:
  - `program_name = "DeskAwake"`;
  - `version = core.__version__` (`0.1.0`);
  - `comments =` descrição + “Desenvolvido por Marcelo Silva · Maniva Software.” +
    “Licença MIT.”, tudo no corpo;
  - `website = "https://github.com/mhenrique94/deskawake"`,
    `website_label = "Repositório no GitHub"`;
  - `Gtk.LinkButton` no corpo para `https://manivasoftware.com.br`
    (label `manivasoftware.com.br`);
  - **sem** `authors` (o GTK criaria o botão “Créditos”) e **sem** `license_type`/`wrap_license`
    (o GTK criaria o botão “Licença”; a licença fica no corpo);
  - logo: tentar `assets/deskawake.svg` via `GdkPixbuf.Pixbuf.new_from_file_at_scale`; se falhar,
    usar o ícone do tema (`preferences-system-power-management`) ou nenhum logo.
  - **Sem** campo de copyright e **sem** CNPJ (decisão 5: © só no LICENSE).
- O diálogo é modal, transiente da janela, e é destruído no fechamento (`run()` + `destroy()`); não
  bloqueia o loop além da interação do usuário.
- Os créditos do **Plasmoid** (`Authors`, `Website`, `Copyright` com a linha legal) e do **README**
  entram na E7, para manter a E6 livre de mudanças no KDE.

### 3.11 Versão única (0.1.0)

- `core/__init__.py` passa a ter `__version__ = "0.1.0"`.
- `pyproject.toml` e `plasmoid/metadata.json` já estão em `0.1.0`; o teste novo garante a sincronia.
- O About lê `core.__version__`; a E7 usa a mesma constante no README e a E8 no `.deb`.
- Nenhuma alteração em `pyproject.toml` além da sincronia (já está correto).

---

## 4. Contratos

### 4.1 Menu GTK (atualizado)

Ordem exata: `Ativar/Desativar` · `Tema ▸` · `Iniciar com o sistema` · `Sobre o DeskAwake…` ·
`Sair`.

- `Ativar/Desativar` continua dinâmico e desabilitado em voo.
- `Tema ▸` continua com `Automático`/`Claro`/`Escuro` e marca o ativo.
- `Iniciar com o sistema` continua marcando/desmarcando o autostart do widget.
- `Sobre` abre o `Gtk.AboutDialog`; não altera estado.
- `Sair` continua por último e mantém o kill switch.

### 4.2 Tooltip

- Sem erro: sem tooltip (ou tooltip neutro opcional).
- Com erro: título `DeskAwake` em negrito + motivo escapado em texto plano.
- O motivo vem de `GetLastError()` e é limpo ao sair de `error`.

### 4.3 A1

- `_NET_SHOWING_DESKTOP=1` ⇒ tentar manter/reexibir o widget uma vez por transição.
- Sem `WindowTypeHint.DESKTOP`; sem loop de reexibição; fallback documentado.

### 4.4 Versão

- `core.__version__ == 0.1.0 == pyproject.toml == metadata.json`.
- Semver `MAJOR.MINOR.PATCH`; teste estático obrigatório.

---

## 5. Decisões técnicas (ADRs)

### ADR-01: E6 é UI; o instalador é E7 e o pacote é E8

- **Contexto:** o design antigo da E6 proibia mudanças em `ui_gtk/`, mas a validação MATE e a
  repaginação do KDE exigiram exatamente isso. Misturar UI e instalador num PR dificultaria o gate.
- **Decisão:** E6 = UI GTK/MATE; E7 = instalador/verify/docs; E8 = distribuição (placeholder).
- **Consequências:** um PR por entrega; a E7 copia a UI já congelada; a E8 depende do layout da E7.

### ADR-02: Paridade é linguagem visual, não cópia

- **Contexto:** o Plasmoid tem resize, hamburguer, chip de wallpaper e sombra; o GTK vive em X11,
  com 124×42 fixo e menu de contexto.
- **Decisão:** o GTK herda acabamento (knob, hover, tooltip, tipografia, estados), mas mantém suas
  diferenças de plataforma.
- **Consequências:** nenhuma mudança de spec em tamanho/menu do GTK; o visual do KDE continua a
  referência de qualidade, não de layout.

### ADR-03: A1 com observação de `_NET_SHOWING_DESKTOP` e fallback

- **Opções:** (a) documentar a limitação; (b) observar a propriedade e reexibir; (c) usar
  `DESKTOP`/`DOCK`.
- **Decisão:** (b), com fallback para (a) se o WM reocultar ou o arrasto quebrar. (c) é proibida
  pela spec e quebra clique/arrasto no Marco.
- **Consequências:** um observador X11 a mais; nenhum hint novo; a limitação pode voltar ao README
  se o spike falhar.

### ADR-04: Créditos nativos, sem poluir a pílula

- **Contexto:** 124×42 não comporta texto de crédito; o Plasma já tem um “Sobre” nativo.
- **Decisão:** GTK usa `Gtk.AboutDialog` com autor/empresa e licença no corpo e os links do
  repositório e do site; sem botão “Créditos”. O Plasmoid usa `metadata.json` (E7). A pílula não muda.
- **Consequências:** créditos acessíveis sem alterar layout; a E7 mantém a linha legal no LICENSE e
  no README.

### ADR-05: Versão única em `core/__init__.py`

- **Contexto:** `pyproject.toml` e `metadata.json` já duplicam `0.1.0`; o About e o `.deb` precisam
  de uma fonte.
- **Decisão:** `core.__version__` é a fonte; teste estático sincroniza os três.
- **Consequências:** um teste novo; nenhum build backend novo (a E1 evitou isso de propósito).

### ADR-06: KDE intocado; arquivos compartilhados só aditivos

- **Contexto:** o usuário exigiu não desfazer o que a E5 validou.
- **Decisão:** nenhuma mudança de QML na E6; qualquer mudança em `metadata.json`/`assets/` na E7 é
  aditiva e passa por `tests/unit/test_plasmoid_assets.py`.
- **Consequências:** a E6 não pode quebrar o Plasmoid; os créditos do KDE chegam na E7.

---

## 6. Fluxos detalhados

### 6.1 “Mostrar área de trabalho”

1. Usuário pressiona Ctrl+Alt+D.
2. O WM seta `_NET_SHOWING_DESKTOP=1` e adiciona `_NET_WM_STATE_HIDDEN` ao widget.
3. O filtro da E6 lê a propriedade, chama `deiconify()` e reaplica os hints uma vez.
4. O widget permanece visível; clique/arrasto funcionam.
5. Ao restaurar (`0`), nada é feito; o estado visual não muda.

### 6.2 `Sobre`

1. Usuário abre o menu e escolhe `Sobre o DeskAwake…`.
2. O diálogo mostra nome, versão `0.1.0`, comentário, autor, site e licença MIT.
3. Fechar o diálogo devolve o foco ao menu/janela sem alterar estado.

### 6.3 Erro e tooltip

1. `StateChanged("error")` chega.
2. A UI busca `GetLastError()`, aplica o estado vermelho e o tooltip com título + motivo escapado.
3. Abrir o menu em `error` relê o motivo.
4. `StateChanged("on"/"off")` limpa o `last_error` e o tooltip.

### 6.4 Barramento indisponível no startup

1. A UI tenta assinar `StateChanged`/`NameOwnerChanged` e falha.
2. Agenda retry a cada 2 s (até 5 tentativas).
3. Ao conseguir, refaz `GetState`/`GetLastError` e normaliza o visual.
4. `destroy` cancela o timer.

---

## 7. Impacto em features/entregas existentes

| Área | Impacto |
|---|---|
| `core/config.py`, `core/environment.py` (E1) | **Nenhum.** |
| `core/inhibitors.py`, `core/state.py`, `core/daemon.py` (E2) | **Nenhum.** |
| `core/cli.py`, `bin/deskawake` (E3) | **Nenhum.** |
| `ui_gtk/widget.py`, `ui_gtk/theme.py` (E4) | Ajustes localizados (A1, knob, hover, tooltip, retry, acessibilidade, `Sobre`). |
| `plasmoid/` (E5) | **Nenhuma mudança de QML.** O `metadata.json` só muda na E7 (créditos). |
| Testes existentes | Preservados; novos testes estáticos somam. |
| `pyproject.toml` | Sem mudança de conteúdo; a versão já é `0.1.0`. |
| Instalador/READMEs | **E7.** |
| Empacotamento | **E8.** |

---

## 8. Conformidade com padrões do projeto

- [x] Decisão 8 (A1): correção tentada com fallback documentado; `DESKTOP` proibido.
- [x] Decisão 14 (menu GTK): `Sobre` acrescentado antes de `Sair`; demais itens intactos.
- [x] Decisão 16 (Plasmoid): nenhuma mudança de QML; diferenças de plataforma preservadas.
- [x] Decisão 19 (testes): testes estáticos novos, sem GUI.
- [x] Decisões 34–38 (créditos, versão, paridade, divisão E6/E7/E8) registradas na spec.
- [x] G1 (MIT), G9 (config só tema/posição), G11 (124×42), G12 (cores de estado), G13/G14 (fonte
      sem `@font-face`), G19 (docs em pt-BR).
- [x] Nenhuma dependência nova de runtime; nenhum `sudo`; nenhum teste de GUI.
- [x] KDE intocado (nenhum QML alterado).

---

## 9. Plano de verificação

### 9.1 Automático

```bash
python3 -m pytest tests/unit -q
dbus-run-session -- python3 -m pytest tests/integration -q
python3 -m pytest tests/unit/test_version.py tests/unit/test_theme.py tests/unit/test_ui_assets.py -v
```

- [ ] Baseline preservado: **267 unit + 34 integração (1 skip)** ou mais, sem regressões.
- [ ] `test_version.py` verde: `core.__version__ == pyproject.toml == metadata.json`.
- [ ] `test_theme.py` verde: knob fixo, hover/pressed, `format_error_tooltip` e escape.
- [ ] `test_ui_assets.py` verde: menu com `Sobre`, ausência de `WindowTypeHint.DESKTOP` e do
      observador de `_NET_SHOWING_DESKTOP` (fallback), presença de `pointer`,
      `get_accessible().set_name` e `markup_escape_text`.
- [ ] Nenhum teste de GUI; nenhuma dependência nova.

### 9.2 Manual — Mint 22.3 MATE/X11 (obrigatório; fecha A1–A7)

1. `./bin/deskawake ui` (com o daemon da E2) ou o autostart; conferir 124×42, canto superior direito,
   24 px, sem decoração.
2. `Alt+Tab`/barra/pager: widget fora; aparece em todos os workspaces (criar um segundo).
3. **A1:** Ctrl+Alt+D ⇒ o widget some e volta ao restaurar; o fallback da E6 foi acionado
   (spike 21/11/2026: o Marco reoculta e `present()` cancela o modo), então registrar a limitação
   no README da E7.
4. Arrasto de qualquer ponto, inclusive sobre o toggle; > 5 px não alterna.
5. Clique no toggle alterna; clique fora não altera; knob escuro legível no tema claro e no escuro.
6. Hover/pressed no toggle e cursor `pointer`; sem animação contínua.
7. Durante `Toggle`/`SetActive`: spinner, toggle bloqueado, sem âmbar.
8. Compositor do Marco desligado ⇒ superfície sólida; ligado ⇒ translucidez.
9. Posição sobrevive a logout; monitor externo desconectado volta ao padrão.
10. Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sobre o DeskAwake…`, `Sair`.
11. `Sobre`: nome, versão `0.1.0`, autor `Marcelo Silva`, site `manivasoftware.com.br`, licença MIT;
    sem CNPJ e sem ©.
12. `Sair` com ON libera imediatamente (`systemd-inhibit --list` sem `deskawake`; `GetInhibitors`
    vazio; `mate-screensaver-command -q` sem `deskawake` quando existir).
13. `kill -9` no daemon não deixa `systemd-inhibit` órfão nem tela presa.
14. Com idle/lock habilitados, ON impede blanking/bloqueio; OFF restaura (sessão nova para delay
    curto; lock destrutivo/opcional).
15. `Mint-Y` ↔ `Mint-Y-Dark` atualiza o tema sem reiniciar; Inter ausente usa Ubuntu/Noto Sans.
16. `error` por queda de backend mostra tooltip com título e motivo, **preserva** o filho do
    `systemd-inhibit` e libera o inibidor de tela; falha de ativação/verificação libera tudo.
17. **A6:** repetir o submenu `Tema` com mouse real; registrar se reproduz.
18. **A7:** logout, desconexão de monitor externo e bloqueio de tela; registrar no PR/README o que
    não for executado.

---

## 10. Riscos e limitações

| Risco | Onde fecha |
|---|---|
| A1 reexibe e o WM reoculta em loop | Spike 21/11/2026: o Marco reoculta e `present()` cancela o modo; observador removido e limitação no README (E7) |
| `deiconify()` furtar foco ou quebrar arrasto | `set_accept_focus(False)` + teste manual; remover observador se quebrar |
| Logo SVG no About falhar em alguns temas | Fallback para ícone do tema ou sem logo |
| Acessibilidade sem teste automatizado | Verificação manual com leitor de tela, se disponível; nomes estáticos testados |
| Retry de D-Bus mascarar barramento morto | Limite de 5 tentativas e cancelamento no destroy; log |
| Divergência de versão voltar | Teste de sincronia obrigatório |
| A6 não reproduzir fora do XTest | Registro no PR; se não reproduzir, fecha como “não reproduzido” |
| Credenciais/© no About | Decisão 5: About sem © e sem CNPJ; LICENSE é a fonte legal |

---

## 11. Próximos passos

1. Implementar os itens da §3 na ordem: versão/teste → tema/tooltip → retry/acessibilidade →
   `Sobre` → A1 (spike) → A6 (reteste).
2. Rodar o gate automático e a checklist MATE §9.2 na máquina Mint.
3. Abrir o PR da E6 (`feat/e6-ui-gtk-mate`) com gate e checklist no corpo; não commitar `docs/`.
4. Após o merge, iniciar a E7 com o design [`design_e7.md`](design_e7.md).
