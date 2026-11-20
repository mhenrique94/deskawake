# Tasks: E4 — UI GTK3 (MATE / X11)

**Feature:** DeskAwake — E4 | **Data:** 2026-11-20 | **Estimativa:** ≈ 14 h (36 tasks)
**Referências:** [`spec.md`](spec.md) (decisões 1–33, “Fluxo alvo”, “Contratos”, “Aparência” e “Notas ao implementador”) | [`design_e4.md`](design_e4.md) | [`DELIVERY_MAP.md`](DELIVERY_MAP.md) §E4 | [`visual/design_visual_aprovado.md`](visual/design_visual_aprovado.md)

## Resumo

- Total de tasks: 36
- Estimativa total: ≈ 14 h (~2 dias de trabalho focado)
- Dependências externas: E3 concluída no branch `feat/e3-cli-launcher` (a E4 é **empilhada** sobre a E3); `python3-gi` (GTK 3.24 / PyGObject 3.48+) e `python3-dbus` instalados; `pytest` de desenvolvimento (`python3 -m pytest`); pacote visual presente em `docs/implementation/visual/assets/` para a cópia verbatim; máquina Mint 22.3 MATE/X11 para a checklist manual. **Nenhuma** migration, serviço, `.service`, template de autostart ou dependência nova de runtime.
- Gate: **G-E4** — `tests/unit/test_theme.py` e `tests/unit/test_ui_assets.py` verdes; `tests/unit` completo verde (sem regressão E1–E3); `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget, ui_gtk.theme"` exit 0; `grep -rn "Gdk" core/` vazio; checklist manual MATE (não-destrutiva) e critérios visuais da §9.3.1 registrados no PR.
- Fora de escopo (não criar nesta entrega): `plasmoid/` (E5); `install.sh`/`uninstall.sh`/`verify.sh`/`data/*.service`/autostart instalado por pacote/READMEs (E6); qualquer mudança em `core/config.py`, `core/environment.py`, `core/inhibitors.py`, `core/state.py`, `core/daemon.py` ou `core/cli.py`; qualquer membro novo no contrato D-Bus; qualquer teste automatizado de GUI; redesenho dos SVGs aprovados; dependências novas.
- Referência de comportamento: em conflito, a `spec.md` vence o `design_e4.md`; a ordem completa é `spec.md` > `design_e4.md` > `visual/design_visual_aprovado.md` (apenas forma/movimento). As decisões fechadas em 2026-11-20 estão na §1.1 e nas ADRs 01–15 do design.
- Este arquivo é versionado em `docs/implementation/`; não entra no PR de código nem é citado em código.

**Sequência:** setup → testes puros de `theme.py` (TDD) → assets + testes estáticos → esqueleto/main do widget → janela/layout/config → tema/assets/spinner → D-Bus/estado → interação/menu/autostart/saída → integração do startup → validação final e entrega.

**Regras de teste que valem para todas as tasks:**

- A suíte da E4 é **headless**: não abre display, não instancia `Gtk.Window`, não fala com o barramento real e não usa `GDK_BACKEND=dummy` além do teste de import (sem chamar `Gtk.init()`).
- `tests/conftest.py` **não** é alterado; os testes E1–E3 permanecem intactos.
- `theme.py` é puro: stdlib + constantes de `core.config`; **não** importa `Gtk`, `Gdk`, `GdkPixbuf` nem `dbus`.
- `widget.py` só é validado por compilação, import headless e greps estruturais; o comportamento visual/interativo é a checklist manual da §9.3 do design (a spec proíbe testes de GUI).
- Nenhuma task adiciona flag de CLI, variável de ambiente (além do contrato `DESKAWAKE_FORCE_UI` da E3) ou dependência.
- Mensagens da UI em pt-BR; tokens públicos sempre `on|off|error`.

## Tasks

### 0. Setup e fundação

- [ ] **T-01**: Criar a branch da E4 empilhada sobre a E3
  - Comando: `git switch feat/e3-cli-launcher && git switch -c feat/e4-widget-gtk-mate`
  - Critério: `git branch --show-current` imprime `feat/e4-widget-gtk-mate`; `git merge-base --is-ancestor feat/e3-cli-launcher HEAD` exit 0. **Não** criar a E4 a partir da `main`.
  - Estimativa: 5min

- [ ] **T-02**: Conferir dependências de runtime e de desenvolvimento
  - Comandos:
    - `python3 --version` (≥ 3.10)
    - `python3 -c "import dbus; print(dbus.__version__)"`
    - `python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk, Gdk, GdkPixbuf; print(Gtk.get_major_version(), Gtk.get_minor_version())"`
    - `python3 -m pytest --version`
  - Critério: todos exit 0; GTK 3.24+; **nenhuma** dependência nova além de `python3-gi`, `python3-dbus` e `pytest` (dev). `pyproject.toml` inalterado.
  - Estimativa: 5min

- [ ] **T-03**: Rodar a linha de base da E3 antes de tocar em código
  - Comando: `python3 -m pytest tests/unit -q && python3 -m compileall -q core tests`
  - Critério: 0 failures, 0 errors (linha de base atual: 192 passed); E1–E3 intactos. Se falhar, parar e resolver antes da E4.
  - Estimativa: 5min

- [ ] **T-04**: Criar o marcador do pacote `ui_gtk`
  - Arquivo: `ui_gtk/__init__.py` (vazio, apenas marcador do pacote)
  - Comando: `python3 -c "import ui_gtk"`
  - Critério: exit 0; nenhum código, docstring ou artefato de spec no arquivo.
  - Estimativa: 2min

- [ ] **T-05**: Confirmar a presença do pacote visual aprovado
  - Comandos: `test -f docs/implementation/visual/assets/deskawake.svg && test -f docs/implementation/visual/assets/spinner.svg` e `python3 -c "import xml.etree.ElementTree as ET; [ET.parse(p) for p in ('docs/implementation/visual/assets/deskawake.svg','docs/implementation/visual/assets/spinner.svg')]"`
  - Critério: ambos exit 0; os dois SVGs são XML válido. Se `docs/implementation/visual/` não existir, **parar** e pedir o pacote aprovado (não redesenhar).
  - Estimativa: 5min

### 1. `ui_gtk/theme.py` — decisão visual pura (TDD)

- [ ] **T-06**: Escrever os testes RED de constantes e `resolve_variant`
  - Arquivo: `tests/unit/test_theme.py` (novo)
  - Testes (nomes da §9.2 do design):
    - `test_theme_constants` — `SYMBOL_SIZE=22`, `TOGGLE_WIDTH=32`, `TOGGLE_HEIGHT=18`, `NAME_SLOT_WIDTH=58`, `BOX_SPACING=4`, `SIDE_MARGIN=1`, `BORDER_WIDTH=1`, `CORNER_RADIUS=12`, `NAME_FONT_SIZE=10`, `NAME_FONT_WEIGHT=600`, paletas e `STATE_COLORS` exatas; `PILL_WIDTH`/`PILL_HEIGHT` vêm de `core.config`.
    - `test_resolve_variant_dark_name` — `resolve_variant("auto", "Mint-Y-Dark", False) == "dark"`.
    - `test_resolve_variant_dark_case_insensitive` — `resolve_variant("auto", "my-darkish", False) == "dark"`.
    - `test_resolve_variant_prefer_dark` — `resolve_variant("auto", "Mint-Y", True) == "dark"`.
    - `test_resolve_variant_forced_light` / `test_resolve_variant_forced_dark` — `theme="light"`/`"dark"` vencem `gtk_theme_name`/`prefer_dark`.
    - `test_resolve_variant_auto_light` — `auto` com tema claro e `prefer_dark=False` ⇒ `light`; `None`/`""` conta como claro.
    - `test_resolve_variant_invalid_theme_falls_back_to_auto` — `"sepia"` segue a mesma regra de `auto`.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "constants or resolve_variant"`
  - Critério: falha (RED) — `ModuleNotFoundError: No module named 'ui_gtk.theme'`.
  - Estimativa: 20min

- [ ] **T-07**: Implementar constantes, paletas e `resolve_variant`
  - Arquivo: `ui_gtk/theme.py` (novo)
  - Contrato: `design_e4.md` §4.1 — constantes de layout, `FONT_STACK`, `STATE_COLORS`, `SURFACE`, `TEXT`, `BORDER_SOLID`, `BORDER_COMPOSITED`, `BORDER_HOVER_*`, `OPACITY = 0.88`; `resolve_variant(theme, gtk_theme_name, prefer_dark)` com `theme` forçado, `auto` por `prefer_dark` **ou** `"dark"` em `gtk_theme_name.lower()`, `None`/vazio como claro e tema inválido caindo em `auto`.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "constants or resolve_variant" && python3 -m compileall -q ui_gtk/theme.py`
  - Critério: testes de T-06 passam (GREEN); compileall exit 0; nenhum import de `Gtk`/`Gdk`/`dbus`.
  - Estimativa: 25min

- [ ] **T-08**: Escrever os testes RED de `build_css`
  - Arquivo: `tests/unit/test_theme.py`
  - Testes (nomes da §9.2):
    - `test_css_has_no_font_face` — `"@font-face" not in css` para light/dark, composited e opaco.
    - `test_css_font_stack` — contém `FONT_STACK` com `sans-serif` no fim.
    - `test_css_does_not_touch_prefer_dark` — `"gtk-application-prefer-dark-theme" not in css` (nem em comentário).
    - `test_css_state_colors` — contém `#80D9A4`, `#929DA5`, `#E47F7F`.
    - `test_css_variants` — light: `#F0F3F5`/`#20252B`; dark: `#20252B`/`#F0F3F5`; nome em `10px`/`600`; switch `32px`/`18px`; slider `14px`; raio `12px`.
    - `test_css_non_composited_is_opaque` — sem compositor, `"rgba(" not in css` e superfícies/bordas sólidas (`BORDER_SOLID`).
    - `test_css_composited_is_translucent` — com compositor, superfície `rgba(240, 243, 245, 0.88)` (light) / `rgba(32, 37, 43, 0.88)` (dark) e borda `rgba`.
    - `test_css_invalid_variant_raises` — `build_css("sepia", True)` levanta `ValueError`.
    - `test_css_menu_uses_font_stack` — contém o seletor/classe do menu com a mesma `FONT_STACK` (sem tamanho imposto).
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "css"`
  - Critério: falha (RED) — `AttributeError: module 'ui_gtk.theme' has no attribute 'build_css'`.
  - Estimativa: 25min

- [ ] **T-09**: Implementar `build_css`
  - Arquivo: `ui_gtk/theme.py`
  - Contrato: `design_e4.md` §4.1 — CSS completo das variantes light/dark para composited e opaco; superfície translúcida a 88% com compositor e sólida sem; `FONT_STACK`, nome 10 px/600, switch 32×18, slider 14×14, raio 12, cores de estado, hover sutil, classe do menu com a mesma fonte; sem `@font-face` e sem o literal `gtk-application-prefer-dark-theme`; variante inválida ⇒ `ValueError`.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "css" && python3 -m compileall -q ui_gtk/theme.py`
  - Critério: testes de T-08 passam (GREEN); nenhuma dependência nova.
  - Estimativa: 35min

- [ ] **T-10**: Escrever os testes RED de `icon_color` e `svg_with_color`
  - Arquivo: `tests/unit/test_theme.py`
  - Testes:
    - `test_icon_color` — `icon_color("light") == TEXT["light"]`, `icon_color("dark") == TEXT["dark"]`; nunca retorna cor de estado.
    - `test_svg_with_color` — substitui **todas** as ocorrências de `currentColor` pela cor informada; cores fixas pré-existentes permanecem intactas; string sem `currentColor` volta inalterada.
    - `test_svg_with_color_uses_state_neutral_color` — o resultado para light/dark não contém `#80D9A4`/`#929DA5`/`#E47F7F`.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "icon_color or svg_with_color"`
  - Critério: falha (RED) — atributos ainda não existem.
  - Estimativa: 15min

- [ ] **T-11**: Implementar `icon_color` e `svg_with_color`
  - Arquivo: `ui_gtk/theme.py`
  - Contrato: `design_e4.md` §4.1 — `icon_color` retorna `TEXT[variant]`; `svg_with_color` faz `svg.replace("currentColor", color)` sem tocar em outras cores.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "icon_color or svg_with_color" && python3 -m compileall -q ui_gtk/theme.py`
  - Critério: testes de T-10 passam (GREEN).
  - Estimativa: 20min

- [ ] **T-12**: Escrever os testes RED do contrato de animação e `spinner_frame`
  - Arquivo: `tests/unit/test_theme.py`
  - Testes (nomes da §9.2):
    - `test_spinner_animation_contract` — `SPINNER_FRAME_COUNT=24`, `SPINNER_STEP_DEGREES=15`, `SPINNER_INTERVAL_MS=40`, `SPINNER_PERIOD_MS=960`, `SPINNER_ANGLES == tuple(range(0, 360, 15))`.
    - `test_spinner_frame_rotation` — para cada ângulo de `SPINNER_ANGLES`, o XML resultante é válido, tem viewBox `0 0 22 22` e contém um `<g transform="rotate(<ângulo> 11 11)">` (aceitar `15` ou `15.0`).
    - `test_spinner_frame_keeps_dot_static` — o `<circle cx="11" cy="11" r="1.45">` **não** está dentro do `<g>` transformado; atributos do círculo inalterados em todos os 24 quadros.
    - `test_spinner_frame_applies_variant_color` — todos os `currentColor` do quadro são substituídos pela cor informada.
    - `test_spinner_frame_does_not_mutate_source` — chamar `spinner_frame` não altera a string original.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "spinner"`
  - Critério: falha (RED) — `spinner_frame`/constantes ausentes.
  - Estimativa: 25min

- [ ] **T-13**: Implementar constantes de animação e `spinner_frame`
  - Arquivo: `ui_gtk/theme.py`
  - Contrato: `design_e4.md` §4.1 e §4.8 — implementação de referência com `xml.etree.ElementTree`: separar o `<circle>` central, envolver os demais elementos em `<g transform="rotate(angle 11 11)">`, reanexar o círculo **fora** do grupo e aplicar `svg_with_color`; registrar o namespace SVG para a saída continuar válida; não usar `Rsvg`/Cairo/PIL.
  - Comando: `python3 -m pytest tests/unit/test_theme.py -v -k "spinner" && python3 -m compileall -q ui_gtk/theme.py`
  - Critério: testes de T-12 passam (GREEN); 24 quadros gerados sem erro.
  - Estimativa: 35min

- [ ] **T-14**: Rodar o arquivo de tema completo e auditar a pureza
  - Comandos:
    - `python3 -m pytest tests/unit/test_theme.py -v`
    - `grep -nE "import (Gtk|Gdk|dbus)|from gi|from dbus" ui_gtk/theme.py` ⇒ sem saída
    - `python3 -m compileall -q ui_gtk/theme.py`
  - Critério: suíte de `test_theme.py` verde; nenhum import de GTK/D-Bus; nenhuma constante duplicada de `PILL_WIDTH`/`PILL_HEIGHT` (importadas de `core.config`).
  - Estimativa: 10min

### 2. Assets e testes estáticos

- [ ] **T-15**: Escrever os testes RED dos SVGs aprovados
  - Arquivo: `tests/unit/test_ui_assets.py` (novo)
  - Testes (nomes da §9.2):
    - `test_symbol_svg` — `assets/deskawake.svg` é XML válido; raiz `width/height="22"` e `viewBox="0 0 22 22"`; contém `currentColor`; exatamente 2 `<path>` de arco no grupo com `stroke` e `stroke-linecap="round"`; um `<circle cx="11" cy="11" r="1.45">`; nenhuma das três cores de estado.
    - `test_spinner_svg` — `assets/spinner.svg` é XML válido; 22×22/viewBox; `currentColor`; 2 `<path>` de arco com `stroke`; exatamente 2 `<path>` de ponta de seta com `fill="currentColor"` e **sem** `stroke`; um `<circle cx="11" cy="11" r="1.45">`; nenhuma cor de estado.
    - `test_assets_have_no_effects` — ambos sem `filter`, `mask`, `linearGradient`, `radialGradient`, `drop-shadow` ou `font-family`.
    - `test_assets_are_verbatim` — os bytes de `assets/*.svg` são idênticos aos de `docs/implementation/visual/assets/*.svg` **quando o diretório visual existir** (pular com `pytest.skip` se ausente).
  - Comando: `python3 -m pytest tests/unit/test_ui_assets.py -v -k "symbol or spinner or effects or verbatim"`
  - Critério: falha (RED) — `FileNotFoundError` para `assets/deskawake.svg` (ainda não copiado).
  - Estimativa: 20min

- [ ] **T-16**: Copiar os SVGs verbatim para `assets/`
  - Comandos:
    - `mkdir -p assets && cp docs/implementation/visual/assets/deskawake.svg assets/deskawake.svg && cp docs/implementation/visual/assets/spinner.svg assets/spinner.svg`
    - `cmp docs/implementation/visual/assets/deskawake.svg assets/deskawake.svg && cmp docs/implementation/visual/assets/spinner.svg assets/spinner.svg`
    - `python3 -m pytest tests/unit/test_ui_assets.py -v -k "symbol or spinner or effects or verbatim"`
  - Critério: `cmp` exit 0 nos dois arquivos; testes de T-15 passam (GREEN). **Não** redesenhar, simplificar ou reinterpretar a geometria.
  - Estimativa: 5min

- [ ] **T-17**: Escrever os testes RED de import headless e ausência de `Gdk` em `core/`
  - Arquivo: `tests/unit/test_ui_assets.py`
  - Testes (nomes da §9.2):
    - `test_modules_import_headless` — `subprocess.run([sys.executable, "-c", "import ui_gtk.widget, ui_gtk.theme"], cwd=REPO_ROOT, env={**os.environ, "GDK_BACKEND": "dummy"}, ...)` exit 0, sem `Gtk.init()` e sem abrir display.
    - `test_core_has_no_gdk` — varre `core/**/*.py` e falha se encontrar `Gdk`/`gi.repository` de GTK; nenhum `Gdk` em `core/`.
  - Comando: `python3 -m pytest tests/unit/test_ui_assets.py -v -k "import_headless or no_gdk"`
  - Critério: `test_modules_import_headless` falha (RED) — `ModuleNotFoundError: No module named 'ui_gtk.widget'`; `test_core_has_no_gdk` passa (o núcleo já está limpo).
  - Estimativa: 15min

### 3. `ui_gtk/widget.py` — esqueleto, janela e layout

- [ ] **T-18**: Implementar o esqueleto de `widget.py`, o estado em memória e `main()`
  - Arquivo: `ui_gtk/widget.py` (novo)
  - Contrato: `design_e4.md` §4.2 e §3.2 — `gi.require_version("Gtk","3.0")`/`Gdk` **antes** dos imports; imports de `core.config` (`CONFIG_PATH`, `PILL_WIDTH`, `PILL_HEIGHT`, `load_config`, `save_config`, `default_position`, `validate_position`) e `core.daemon` (`DBUS_NAME`, `OBJECT_PATH`, `INTERFACE`); constantes `ROOT`, `AUTOSTART_PATH`, `TEMPLATE_PATH`; `DeskAwakeWidget` com os campos de estado da §3.2; `main()` registra `DBusGMainLoop(set_as_default=True)`, chama `Gtk.init_check()` de forma compatível (bool ou `(bool, argv)`, `RuntimeError` se o display não abrir), cria/mostra o widget, roda `Gtk.main()` e retorna `0`. **Não** adquire `org.local.DeskAwake.Ui`; reutiliza o `SessionBus` singleton (cria se chamado direto).
  - Comandos:
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget, ui_gtk.theme"` ⇒ exit 0
    - `python3 -m compileall -q ui_gtk/widget.py` ⇒ exit 0
    - `grep -n "RequestName\|request_name" ui_gtk/widget.py` ⇒ sem saída
    - `grep -n "DBusGMainLoop(set_as_default=True)\|Gtk.init_check()\|Gtk.main()" ui_gtk/widget.py` ⇒ três ocorrências
  - Critério: import headless verde (GREEN para T-17); compileall exit 0; nenhum `RequestName`; nenhuma flag/env nova.
  - Estimativa: 30min

- [ ] **T-19**: Implementar a janela e os hints EWMH
  - Arquivo: `ui_gtk/widget.py` (`_build_window`, `_apply_window_hints`)
  - Contrato: `design_e4.md` §2.5 e ADR-05 — `Gtk.WindowType.TOPLEVEL`, `Gdk.WindowTypeHint.UTILITY`, `set_decorated(False)`, `set_resizable(False)`, `set_default_size(124, 42)`, `set_size_request(124, 42)`, `set_keep_below(True)`, `set_skip_taskbar_hint(True)`, `set_skip_pager_hint(True)`, `stick()`, `set_accept_focus(False)`, `set_focus_on_map(False)`; hints **antes** de `show_all()` e reaplicados em `realize` e `map`; com compositor (`Gdk.Screen.is_composited()` + `get_rgba_visual()`), `set_app_paintable(True)` e visual RGBA; sem compositor, janela opaca. **Nunca** `WindowTypeHint.DESKTOP`; **nunca** `set_opacity()`.
  - Comandos:
    - `grep -n "WindowTypeHint.DESKTOP\|set_opacity" ui_gtk/widget.py` ⇒ sem saída
    - `grep -n "set_keep_below(True)\|set_skip_taskbar_hint(True)\|set_skip_pager_hint(True)\|stick()" ui_gtk/widget.py` ⇒ quatro ocorrências
    - `python3 -c "from pathlib import Path; s = Path('ui_gtk/widget.py').read_text(); assert s.index('set_keep_below') < s.index('show_all')"` ⇒ exit 0
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` e `python3 -m compileall -q ui_gtk/widget.py`
  - Critério: greps e verificação de ordem conforme acima; import/compile exit 0.
  - Estimativa: 35min

- [ ] **T-20**: Montar a árvore de widgets 124×42
  - Arquivo: `ui_gtk/widget.py` (construção do layout)
  - Contrato: `design_e4.md` §2.3/§2.4 — `Gtk.Box` com classe `deskawake-pill`, `spacing=BOX_SPACING`, margem `SIDE_MARGIN`; `Gtk.Stack` 22×22 com `Gtk.Image` do símbolo e `Gtk.Image` do spinner; `Gtk.Label` classe `deskawake-name`, `width_request=NAME_SLOT_WIDTH` (58), `width_chars=8`, `ellipsize=END`, `single_line_mode=True`, alinhamento `CENTER`; `Gtk.Switch` `width_request=TOGGLE_WIDTH`/`height_request=TOGGLE_HEIGHT` (32×18), `valign=CENTER`; switch é o único indicador de estado. A fonte 10 px/600 vem do CSS.
  - Comandos:
    - `grep -n "NAME_SLOT_WIDTH\|BOX_SPACING\|SIDE_MARGIN\|SYMBOL_SIZE\|TOGGLE_WIDTH\|TOGGLE_HEIGHT" ui_gtk/widget.py` ⇒ todas as constantes usadas
    - `grep -n "width_chars=8\|ellipsize\|single_line_mode\|Gtk.Stack\|width_request=\|height_request=" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0; nenhum tamanho hardcoded fora das constantes de `theme.py`/`core.config`.
  - Estimativa: 35min

- [ ] **T-21**: Implementar workareas, primeiro uso do config e persistência de posição
  - Arquivo: `ui_gtk/widget.py` (`_workareas`, `_load_and_initialize_config`, `_save_position`, posicionamento antes de `show_all()`)
  - Contrato: `design_e4.md` §4.6 e ADR-07 — workareas com `get_primary_monitor()` primeiro e depois os demais em ordem; se `CONFIG_PATH` não existir, criar com `theme="auto"` e posição `default_position(workareas)`; se existir sem posição, usar o padrão em memória sem gravar; devolver `(theme, validate_position(config.get("position"), workareas))`; mover a janela para a posição **antes** de `show_all()`; `_save_position` só grava se `validate_position(pos, workareas) == pos`; `OSError` é silenciado.
  - Comandos:
    - `grep -n "get_primary_monitor\|get_monitor_workarea\|default_position\|validate_position\|CONFIG_PATH.exists()\|save_config\|load_config" ui_gtk/widget.py` ⇒ todas as chamadas presentes
    - `grep -n "move(" ui_gtk/widget.py` ⇒ presente; confirmar com `python3 -c "from pathlib import Path; s = Path('ui_gtk/widget.py').read_text(); assert s.index('move(') < s.index('show_all')"` ⇒ exit 0
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps/ordem conforme acima; import/compile exit 0.
  - Estimativa: 30min

### 4. `ui_gtk/widget.py` — tema, assets e spinner

- [ ] **T-22**: Implementar `_apply_theme`, o provider CSS e os sinais de tema/compositor
  - Arquivo: `ui_gtk/widget.py` (`_apply_theme`, `_on_gtk_theme_changed`, `_on_composited_changed`)
  - Contrato: `design_e4.md` §2.7, §6.7 e ADR-09/ADR-10 — ler `Gtk.Settings.get_default().props.gtk_theme_name` e `gtk_application_prefer_dark_theme`; resolver com `resolve_variant`; gerar CSS com `build_css(variant, composited)` e aplicar em **um único** `Gtk.CssProvider` no `Gdk.Screen`; assinar `notify::gtk-theme-name`, `notify::gtk-application-prefer-dark-theme` e `composited-changed`; reaplicar sem reiniciar; **nunca** escrever `gtk-application-prefer-dark-theme` no settings global; invalidar/regenerar os pixbufs na troca de variante.
  - Comandos:
    - `grep -n "CssProvider\|add_provider_for_screen\|notify::gtk-theme-name\|notify::gtk-application-prefer-dark-theme\|composited-changed\|build_css\|resolve_variant" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `grep -nE "gtk_application_prefer_dark_theme\s*=" ui_gtk/widget.py` ⇒ sem saída (só leitura)
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 35min

- [ ] **T-23**: Implementar o carregamento dos SVGs e o cache de pixbufs
  - Arquivo: `ui_gtk/widget.py` (loader do símbolo/spinner)
  - Contrato: `design_e4.md` §4.8 — ler `assets/deskawake.svg` e `assets/spinner.svg` a partir de `ROOT / "assets"`; aplicar `svg_with_color(..., icon_color(variant))`; carregar com `GdkPixbuf.PixbufLoader` (sem `Rsvg`/Cairo/PIL); cachear pixbufs por variante; falha do loader ⇒ imagem vazia e widget segue funcionando, sem traceback.
  - Comandos:
    - `grep -n "ROOT / \"assets\"\|svg_with_color\|PixbufLoader\|icon_color" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `grep -nE "Rsvg|cairo|import PIL" ui_gtk/widget.py` ⇒ sem saída
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 25min

- [ ] **T-24**: Implementar o spinner de 24 quadros/15°/40 ms
  - Arquivo: `ui_gtk/widget.py` (`_start_spinner`, `_stop_spinner`, `_advance_spinner_frame`)
  - Contrato: `design_e4.md` §4.8 e ADR-11 — gerar/cachear os 24 quadros com `spinner_frame` por variante; `GLib.timeout_add(SPINNER_INTERVAL_MS, ...)` ciclando `SPINNER_ANGLES`; começar no frame 0 e avançar 15° por tick (960 ms/volta); trocar `Gtk.Stack` símbolo ↔ spinner; parar no reply/erro/timeout, na queda do daemon e ao fechar; nenhuma animação em repouso; ponto central imóvel (garantido por `spinner_frame`).
  - Comandos:
    - `grep -n "SPINNER_ANGLES\|SPINNER_INTERVAL_MS\|timeout_add\|_advance_spinner_frame\|set_visible_child" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 30min

### 5. `ui_gtk/widget.py` — D-Bus e estado

- [ ] **T-25**: Implementar assinatura de sinais, sincronização inicial e chamadas assíncronas
  - Arquivo: `ui_gtk/widget.py` (`_subscribe_signals`, `_sync_initial_state`, `_request_state`, `_request_last_error`, `_send_set_active`, `_on_call_reply`, `_on_call_error`)
  - Contrato: `design_e4.md` §4.3, §6.1, §6.6 e ADR-04/ADR-12 — assinar `StateChanged` e `NameOwnerChanged` (filtrado por `DBUS_NAME`) **antes** de `NameHasOwner`; no startup, sem dono ⇒ `off` visual sem `GetState`; com dono ⇒ `GetState` assíncrono (timeout 2 s) e, se `error`, `GetLastError` (2 s); `SetActive(dbus.Boolean(...))` assíncrono (timeout 5 s); `Quit` assíncrono (2 s); `call_pending` + `call_generation` descartam callbacks antigos; **não** chamar `Toggle`, `StartServiceByName` nem backend; falha de ação sem dono ⇒ `off`; com dono ⇒ ressincronizar.
  - Comandos:
    - `grep -n "add_signal_receiver\|StateChanged\|NameOwnerChanged\|name_has_owner\|GetState\|GetLastError\|SetActive\|Quit\|reply_handler=\|error_handler=" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `grep -n "timeout=2\|timeout=5" ui_gtk/widget.py` ⇒ timeouts corretos
    - `grep -nE "\"Toggle\"|StartServiceByName|start_service_by_name" ui_gtk/widget.py` ⇒ sem saída
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 45min

- [ ] **T-26**: Implementar o mapeamento de estado e os callbacks de sinal
  - Arquivo: `ui_gtk/widget.py` (`_apply_state`, `_on_state_changed`, `_on_name_owner_changed`, atualização de menu/tooltip)
  - Contrato: `design_e4.md` §4.4 e §4.9 — `off`: switch `False`/sensível, classe `state-off`, menu `Ativar`, tooltip limpo, spinner oculto; `on`: `True`, `state-on`, `Desativar`; `error`: `False`, `state-error`, `Ativar`, tooltip com `GetLastError()` e fallback `DeskAwake: erro sem detalhes`; estado inválido é ignorado sem traceback; queda do daemon ⇒ `off`, limpa erro, para spinner e invalida gerações; retorno do daemon ⇒ ressincroniza; durante chamada em voo o switch preserva o último estado e fica insensível; só o toggle usa cores de estado.
  - Comandos:
    - `grep -n "state-on\|state-off\|state-error\|DeskAwake: erro sem detalhes\|call_generation\|call_pending" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `grep -n "set_active(\|set_sensitive(\|set_tooltip_text(" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 35min

### 6. `ui_gtk/widget.py` — interação, menu, autostart e saída

- [ ] **T-27**: Implementar clique no switch e supressão de `state-set`/`activate`
  - Arquivo: `ui_gtk/widget.py` (`_on_switch_state_set`, `_on_button_press`, handlers de `activate`)
  - Contrato: `design_e4.md` §4.5 e ADR-06 — `button-press` grava `(x_root, y_root)`, `dragged=False` e `press_on_switch`; `state-set` **sempre retorna `True`** (o GTK nunca muda o switch sozinho); ignora se `dragged`/`call_pending`; se o desejado já é o estado atual, não chama nada; caso contrário, chama `SetActive(desired)`; clique curto no switch deixa o sinal seguir; clique curto fora do switch não faz nada; `activate` também é guardado por `dragged`.
  - Comandos:
    - `grep -n "state-set\|press_on_switch\|dragged\|call_pending\|SetActive" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `grep -n "def _on_switch_state_set" ui_gtk/widget.py` e conferir que todos os caminhos retornam `True`
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 25min

- [ ] **T-28**: Implementar arrasto com threshold de 5 px e debounce de 250 ms
  - Arquivo: `ui_gtk/widget.py` (`_on_motion_notify`, `_on_button_release`, `_on_configure`, `_finish_drag`)
  - Contrato: `design_e4.md` §4.5, §6.3 e ADR-06 — distância euclidiana > 5 px marca `dragged=True` e chama `window.begin_move_drag(button, x_root, y_root, time)`; `button-release` com `dragged` suprime a alternância e finaliza; cada `configure-event` com `dragged` reagenda `GLib.timeout_add(250, _finish_drag)`; `_finish_drag` lê `window.get_position()`, grava posição + tema **somente** se `validate_position(pos, workareas) == pos`, reseta `dragged`, `press_on_switch` e reaplica o estado ao switch; release antecipado salva na hora e cancela o timer; handlers ligados à janela **e** ao switch.
  - Comandos:
    - `grep -n "begin_move_drag\|_finish_drag\|timeout_add(250\|validate_position\|_save_position\|configure-event\|button-release\|motion-notify" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 35min

- [ ] **T-29**: Implementar o menu completo
  - Arquivo: `ui_gtk/widget.py` (`_build_menu`, `_on_popup_menu`)
  - Contrato: `design_e4.md` §2.6, §6.4 e ADR-14 — clique direito (inclusive sobre o switch) abre o menu e retorna `True`; itens `Ativar/Desativar` (rótulo dinâmico), `Tema ▸` com `Automático`/`Claro`/`Escuro` em `Gtk.RadioMenuItem` (marca o valor atual, grava `auto`/`light`/`dark` e reaplica o CSS), `Iniciar com o sistema` em `Gtk.CheckMenuItem` e `Sair`; antes do `popup_at_pointer`, atualizar rótulo/checks, reler autostart e, em `error`, atualizar `GetLastError()`; durante chamada em voo, item de estado e `Sair` desabilitados (itens locais disponíveis); classe `deskawake-menu`; nunca disparar auto-start.
  - Comandos:
    - `grep -n "Ativar\|Desativar\|Automático\|Claro\|Escuro\|Iniciar com o sistema\|Sair\|RadioMenuItem\|CheckMenuItem\|popup_at_pointer\|deskawake-menu" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 30min

- [ ] **T-30**: Implementar o autostart do widget
  - Arquivo: `ui_gtk/widget.py` (`AUTOSTART_PATH`, `TEMPLATE_PATH`, `_autostart_enabled`, `_set_autostart`)
  - Contrato: `design_e4.md` §4.7, §6.8 e ADR-08 — `~/.config/autostart/deskawake-widget.desktop`; `_autostart_enabled` retorna `False` se o arquivo não existe ou tem `Hidden=true`/`X-GNOME-Autostart-enabled=false`; `_set_autostart(False)` usa `unlink(missing_ok=True)`; `_set_autostart(True)` lê `data/deskawake-widget.desktop` quando existir, reescreve `Exec=` para `<ROOT>/bin/deskawake ui` absoluto (com aspas duplas se houver espaços), remove `Hidden=true`, garante `X-GNOME-Autostart-enabled=true`, ou sintetiza a entrada mínima se o template não existir; escrita atômica (`tmp` no mesmo diretório + `os.replace`); falha reverte o checkbox sem diálogo; nunca toca no autostart do daemon.
  - Comandos:
    - `grep -n "AUTOSTART_PATH\|TEMPLATE_PATH\|X-GNOME-Autostart-enabled\|Hidden=true\|Exec=\|unlink(missing_ok=True)\|os.replace" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0; nenhuma dependência nova.
  - Estimativa: 30min

- [ ] **T-31**: Implementar `Sair`/fechamento como kill switch
  - Arquivo: `ui_gtk/widget.py` (`_quit`, `_close`, handler de `delete-event`)
  - Contrato: `design_e4.md` §6.5 e ADR-13 — se o daemon não existe, fecha imediatamente (`Gtk.main_quit()`); se existe, `SetActive(false)` (timeout 5 s) e, no reply/erro, `Quit()` (timeout 2 s); no reply/erro do `Quit` (ou timeout), `Gtk.main_quit()`; `delete-event` chama `_quit()` e retorna `True`; nenhum caminho fecha a UI deixando o daemon `on` sem intenção.
  - Comandos:
    - `grep -n "def _quit\|def _close\|delete-event\|Gtk.main_quit\|SetActive\|Quit()" ui_gtk/widget.py` ⇒ ocorrências esperadas
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
  - Critério: greps conforme acima; import/compile exit 0.
  - Estimativa: 20min

- [ ] **T-32**: Integrar a ordem de abertura em `show()`
  - Arquivo: `ui_gtk/widget.py` (`__init__`, `show`)
  - Contrato: `design_e4.md` §6.1 — construir janela/hints/layout/menu/provider; obter `SessionBus` singleton; **assinar sinais antes** de qualquer consulta; ler/incializar config; mover para a posição validada; `show_all()`; só então `NameHasOwner`/`GetState` (se houver dono); entrar em `Gtk.main()`. A ordem não pode disparar auto-start nem bloquear o loop.
  - Comandos:
    - `python3 -c "from pathlib import Path; s = Path('ui_gtk/widget.py').read_text(); assert s.index('_subscribe_signals') < s.index('name_has_owner'); assert s.index('show_all') < s.index('_sync_initial_state')"` ⇒ exit 0
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget"` ⇒ exit 0
    - `python3 -m compileall -q ui_gtk/widget.py` ⇒ exit 0
  - Critério: ordem conforme acima; import/compile exit 0.
  - Estimativa: 20min

### 7. Validação final e entrega

- [ ] **T-33**: Rodar o gate automatizado completo da E4
  - Comandos:
    - `python3 -m pytest tests/unit/test_theme.py tests/unit/test_ui_assets.py -v` ⇒ 0 failures
    - `python3 -m pytest tests/unit -q` ⇒ 0 failures, 0 skipped (sem regressão E1–E3)
    - `GDK_BACKEND=dummy python3 -c "import ui_gtk.widget, ui_gtk.theme"` ⇒ exit 0
    - `grep -rn "Gdk" core/` ⇒ sem saída
    - `python3 -m compileall -q core ui_gtk tests` ⇒ exit 0 (o projeto não tem lint/typecheck configurado; compileall + import headless são os gates)
  - Critério: todos exit 0; nenhum teste de GUI criado; nenhum display/barramento real usado.
  - Estimativa: 10min

- [ ] **T-34**: Auditar escopo, higiene e dependências
  - Comandos:
    - `grep -RInE "AC-[0-9]|T-[0-9]|design_e4|tasks_e4|spec\.md|DELIVERY_MAP" ui_gtk assets tests/unit/test_theme.py tests/unit/test_ui_assets.py` ⇒ sem saída
    - `git status --short` ⇒ apenas os 7 arquivos da entrega (+ docs já versionadas em `docs/implementation/`, fora do stage)
    - `git diff --stat -- core bin pyproject.toml` ⇒ sem saída (núcleo/CLI/pyproject intocados)
    - `grep -RInE "Gtk|Gdk|dbus" ui_gtk/theme.py` ⇒ sem saída
  - Critério: todos conforme acima; nenhuma dependência nova; nenhum artefato de spec em código/comentários; nenhuma mudança em `core/*` ou `bin/`.
  - Estimativa: 15min

- [ ] **T-35**: Executar a checklist manual no Mint 22.3 MATE/X11 e registrar o resultado
  - Pré-condição: daemon da E2 rodando (`./bin/deskawake daemon` em outro terminal); UI aberta com `./bin/deskawake ui`.
  - Passos (design §9.3 e §9.3.1; não-destrutivos obrigatórios):
    - abrir no canto superior direito, 24 px de margem, sem decoração; nome `DeskAwake` completo (Ubuntu), símbolo 22×22 e toggle 32×18 dentro de 124×42
    - não aparecer em `Alt+Tab`/barra/pager; aparecer em todos os workspaces (criar um segundo); ficar atrás de janelas normais; “Mostrar área de trabalho” do Caja não quebra
    - arrastar de qualquer ponto, inclusive sobre o toggle; > 5 px não alterna; clique curto no toggle alterna; clique fora não altera
    - durante `SetActive`: spinner de duas flechas, toggle bloqueado, sem âmbar; ao responder, volta ao símbolo
    - compositor do Marco desligado ⇒ superfície sólida/legível; ligado ⇒ translucidez
    - posição sobrevive a logout; desconectar monitor externo volta ao padrão
    - menu completo (`Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sair`); `Tema ▸` marca o atual e persiste; autostart cria/remove `~/.config/autostart/deskawake-widget.desktop` com `Exec` absoluto
    - `Sair` com ON libera inibidores (`systemd-inhibit --list` sem `deskawake`; `GetInhibitors` vazio; `IsInhibited(8)` falso)
    - `kill -9` no daemon ⇒ `off` imediato, sem spinner preso e sem `systemd-inhibit` órfão
    - idle/lock do `mate-screensaver`: ON impede blanking/bloqueio; OFF restaura
    - `Mint-Y` ↔ `Mint-Y-Dark` atualiza sem reiniciar; com Inter ausente, Ubuntu/Noto Sans sem erro
    - `error` (ex.: matar `mate-screensaver`) mostra tooltip e libera o inibidor
    - critérios visuais: dois arcos + ponto central no símbolo; duas setas sólidas no spinner; ponto central imóvel; só o toggle usa cores de estado; variantes mudam apenas cores neutras
    - suspensão/lid (destrutivos) **opcionais** — marcar como não executados se a máquina não permitir
  - Critério: cada item não-destrutivo marcado como OK ou com desvio descrito; resultados colados no corpo do PR. Se a máquina Mint não estiver disponível, registrar a pendência no PR (não bloqueia o gate automatizado, mas bloqueia o merge).
  - Estimativa: 45min

- [ ] **T-36**: Preparar commit e PR somente com a entrega
  - Comandos:
    - `git add ui_gtk/__init__.py ui_gtk/theme.py ui_gtk/widget.py assets/deskawake.svg assets/spinner.svg tests/unit/test_theme.py tests/unit/test_ui_assets.py`
    - `git diff --cached --name-only` ⇒ exatamente os 7 arquivos
    - `python3 -m pytest tests/unit -q` ⇒ gate verde
    - `git commit -m "feat(e4): widget GTK3 para MATE/X11"`
    - `git push -u origin feat/e4-widget-gtk-mate`
    - `gh pr create --base feat/e3-cli-launcher --head feat/e4-widget-gtk-mate --title "feat(e4): widget GTK3 para MATE/X11" --body "<corpo no template do DELIVERY_MAP §0.2>"`
    - `gh pr view --json baseRefName,headRefName,files --jq '{base: .baseRefName, head: .headRefName, files: [.files[].path]}'` ⇒ base `feat/e3-cli-launcher`, head `feat/e4-widget-gtk-mate` e apenas os 7 arquivos
  - Corpo do PR: gate com comando/resultado (unit + import headless + `grep Gdk` + manual), checklist manual/visual preenchida, fora de escopo (E5/E6) e riscos residuais (§10 do design); **não** citar `spec.md`, `design_e4.md`, `tasks_e4.md`, `docs/implementation/visual/` nem IDs `AC-*`/`T-*`.
  - Critério: PR contém apenas os 7 arquivos; base é a branch da E3 (empilhamento), **não** `main`, sem retarget sem confirmação; `docs/implementation/` (incluindo `visual/`) e `README.md` fora do stage/PR de código. **Nunca** usar `git add -A`/`git add .`.
  - Estimativa: 20min

## Mapeamento AC → Tasks

Os critérios vêm do `DELIVERY_MAP.md` §E4.4 (automático e manual), da §9.2/§9.3 do `design_e4.md` e do gate G-E4.

| Critério de aceite | Tasks que validam |
|---|---|
| AC-01 — `resolve_variant` cobre `Mint-Y-Dark`, `my-darkish`, `prefer_dark`, forçados light/dark e `auto` claro | T-06, T-07 |
| AC-02 — CSS sem `@font-face`, com `FONT_STACK` e `sans-serif` no fim; sem o literal `gtk-application-prefer-dark-theme` | T-08, T-09 |
| AC-03 — CSS contém as três cores de estado e as paletas light/dark corretas | T-08, T-09 |
| AC-04 — Sem compositor o CSS é sólido (sem `rgba` de superfície); com compositor é translúcido a 88% | T-08, T-09 |
| AC-05 — `deskawake.svg` válido, 22×22, `currentColor`, dois arcos, ponto central, sem cores de estado/efeitos | T-15, T-16 |
| AC-06 — `spinner.svg` válido, 22×22, `currentColor`, duas pontas sólidas (`fill`, sem `stroke`), ponto central | T-15, T-16 |
| AC-07 — Nenhum `Gdk` em `core/` | T-17 |
| AC-08 — `ui_gtk.widget` e `ui_gtk.theme` importam sem display (`GDK_BACKEND=dummy`) | T-17, T-18 |
| AC-09 — `svg_with_color` substitui `currentColor` sem tocar nas demais cores | T-10, T-11 |
| AC-10 — `spinner_frame` gera XML válido com `rotate(...)` e mantém o `<circle>` central fora do grupo | T-12, T-13 |
| AC-11 — Contrato de animação: 24 quadros, 15°, 40 ms, 960 ms | T-12, T-13 |
| AC-12 — `icon_color` acompanha a variante e não usa cores de estado | T-10, T-11 |
| AC-13 — Janela 124×42 sem decoração, `UTILITY`, sem `DESKTOP`; hints antes de `show_all` e em `realize`/`map` | T-19 |
| AC-14 — Layout 124×42: símbolo 22×22, nome 58 px (10 px/600), switch 32×18, espaçamento 4 e margens 1 | T-20 |
| AC-15 — Primeiro uso cria `config.json` com `theme=auto` e posição padrão; posição validada e movida antes de `show_all` | T-21 |
| AC-16 — Tema reativo: `notify::gtk-theme-name`/`prefer-dark` + `composited-changed`, sem escrever no settings global | T-22 |
| AC-17 — SVGs lidos de `assets/` com `currentColor`, cor da variante e fallback vazio sem traceback | T-23 |
| AC-18 — Spinner só durante chamada em voo, 24 quadros/15°/40 ms, sem animação em repouso | T-24 |
| AC-19 — Sinais assinados antes das consultas; sem dono ⇒ `off` sem `GetState`/auto-start; chamadas assíncronas com timeouts 2 s/5 s e geração | T-25 |
| AC-20 — Mapeamento `on`/`off`/`error`: switch, classes, rótulo, tooltip, spinner e liveness | T-26 |
| AC-21 — `state-set` sempre retorna `True`; clique curto no toggle alterna; clique fora não altera | T-27 |
| AC-22 — Arrasto > 5 px inicia `begin_move_drag` e não alterna; debounce de 250 ms salva posição validada | T-28 |
| AC-23 — Menu completo com rótulo dinâmico, tema, autostart e `Sair`; itens de estado/`Sair` bloqueados em voo | T-29 |
| AC-24 — Autostart do widget idempotente, `Exec` absoluto, template E6 ou síntese, escrita atômica | T-30 |
| AC-25 — `Sair`/`delete-event` executam `SetActive(false)` → `Quit()` → fechar; daemon morto fecha direto | T-31 |
| AC-26 — Ordem de abertura: montar → assinar → config/posição → `show_all` → `NameHasOwner`/`GetState` → `Gtk.main` | T-32 |
| AC-M01 — Manual: abre no canto superior direito, 24 px, sem decoração, nome/fonte/geometria corretos | T-35 |
| AC-M02 — Manual: fora de `Alt+Tab`/barra/pager, em todos os workspaces, atrás das janelas, Caja OK | T-35 |
| AC-M03 — Manual: arrasto de qualquer ponto, threshold 5 px, toggle não alterna no drag | T-35 |
| AC-M04 — Manual: spinner durante a chamada, toggle bloqueado/preservando estado, sem âmbar | T-35 |
| AC-M05 — Manual: compositor ligado/desligado, posição persistida e fallback de monitor | T-35 |
| AC-M06 — Manual: menu completo, tema em runtime, autostart cria/remove | T-35 |
| AC-M07 — Manual: `Sair`/`kill -9` liberam inibidores e não deixam spinner/tela presos | T-35 |
| AC-M08 — Manual: idle/lock do `mate-screensaver` e tooltip de `error` | T-35 |
| AC-M09 — Manual visual: símbolo/spinner aprovados, ponto central imóvel, só o toggle colorido | T-35 |
| AC-G01 — `test_theme.py` + `test_ui_assets.py` verdes | T-33 |
| AC-G02 — `tests/unit` completo verde, sem regressão E1–E3 | T-33 |
| AC-G03 — Import headless exit 0; `grep Gdk core/` vazio | T-17, T-33 |
| AC-G04 — Nenhuma dependência nova; `pyproject.toml` e `core/*`/`bin/*` intocados | T-02, T-34 |
| AC-G05 — Nenhum artefato de spec em código/comentários/commits/PRs; PR empilhado sobre a E3 e só com os 7 arquivos | T-34, T-36 |

## Cobertura das decisões do design (ADR)

| Decisão | Tasks que a fixam |
|---|---|
| ADR-01 — layout 124×42 com nome em 10 px/600 e slot de 58 px | T-07, T-20 |
| ADR-02 — paleta clara espelhada e escura grafite; cores de estado fixas | T-07, T-09 |
| ADR-03 — spinner no slot do símbolo (22×22), toggle visível e desabilitado | T-20, T-24 |
| ADR-04 — chamadas D-Bus assíncronas com geração e timeouts | T-25 |
| ADR-05 — janela `UTILITY` + hints antes de `show_all`; nunca `DESKTOP` | T-19 |
| ADR-06 — arrasto com threshold 5 px, `begin_move_drag` e debounce 250 ms | T-27, T-28 |
| ADR-07 — posição/workareas, primeiro uso do `config.json` | T-21 |
| ADR-08 — autostart somente do widget, template E6 ou síntese, `Exec` absoluto | T-30 |
| ADR-09 — `auto` por `gtk-theme-name`/`prefer-dark`, sinais de runtime, sem escrever no settings | T-22 |
| ADR-10 — compositor decide `rgba` × sólido; sem `set_opacity()` | T-19, T-22 |
| ADR-11 — SVG `currentColor`, 24 quadros/15°/40 ms, ponto central fora da rotação | T-12, T-13, T-23, T-24 |
| ADR-12 — assinar sinais antes de consultar; sem auto-start no startup | T-25, T-32 |
| ADR-13 — `Sair` e `delete-event` como kill switch | T-31 |
| ADR-14 — rótulos do menu em pt-BR (`Automático`/`Claro`/`Escuro`) | T-29 |
| ADR-15 — testes puros, sem GUI; import verificado em subprocesso | T-06–T-18, T-33 |

## Notas de execução

1. **RED obrigatório:** em cada task de teste, rodar o comando e confirmar a falha esperada (módulo/atributo/arquivo ausente). Se um teste passar antes da implementação, é regressão — registrar e não “implementar” o que já existe.
2. **Sem GUI automatizada:** a suíte não instancia `Gtk.Window`, não chama `Gtk.init()` e não fala com o barramento real. `GDK_BACKEND=dummy` é usado **apenas** no import headless. Aparência, empilhamento, arrasto, tema e animação são a checklist manual da §9.3.
3. **Não alterar `tests/conftest.py`** nem os testes E1–E3; `test_theme.py` e `test_ui_assets.py` são os únicos arquivos novos de teste.
4. **Assets verbatim:** `assets/*.svg` são cópias exatas de `docs/implementation/visual/assets/*.svg`; qualquer redesenho exige nova aprovação visual. Os testes automatizados não dependem do pacote visual existir (a comparação é `pytest.skip` quando ausente).
5. **Nunca usar `git add -A`/`git add .`:** `README.md`, `docs/implementation/` e artefatos gerados ficam fora do PR de código; a documentação vai em PR/commit `docs:` separado.
6. **Sem artefatos de spec no código:** `ui_gtk/`, `assets/` e `tests/` não podem citar `AC-*`, `T-*`, `design_e4.md`, `tasks_e4.md`, `spec.md`, `DELIVERY_MAP.md` ou `visual/` em código, comentários, commits ou corpo do PR.
7. **Fora de escopo intocável:** nenhuma alteração em `core/config.py`, `core/environment.py`, `core/inhibitors.py`, `core/state.py`, `core/daemon.py`, `core/cli.py`, `bin/deskawake`, `tests/conftest.py`, contrato D-Bus da E2 ou qualquer arquivo de E5/E6.
8. **PRs empilhados:** E4 → E3 (base `feat/e3-cli-launcher`), E5 → E3 (paralela), E6 só depois de E4 e E5 mergeadas. Não retargetar para `main` sem confirmação.
9. **Documento versionado:** este `tasks_e4.md` (em `docs/implementation/`) é o escopo canônico do `/implement`; não entra no PR de código nem é citado em código.
