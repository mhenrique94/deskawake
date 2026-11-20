# Spec — DeskAwake Widget

Data: 2026-11-19
Status: Aprovado (aguardando implementação)
Escopo: utilitário de desktop Linux (MATE/X11 e KDE Plasma 6/Wayland): núcleo Python, widget GTK3, Plasmoid QML, instalador/desinstalador e testes. Sem empacotamento para distros, sem suporte a Windows/macOS, sem testes de GUI.

## Problema

Em Linux Mint MATE (X11) e Kubuntu (KDE Plasma 6 / Wayland), o usuário precisa impedir que a tela bloqueie/apague e que a máquina suspenda durante vídeos, builds e downloads longos — sem instalar um app pesado e sem manter uma janela convencional aberta. O controle deve viver na área de trabalho, atrás das janelas normais, ser arrastável, não aparecer em `Alt+Tab`/barra de tarefas, e nunca deixar o sistema preso sem dormir depois que o usuário fechar o controle.

O mesmo núcleo precisa servir às duas interfaces: widget GTK3 no MATE e Plasmoid nativo no Plasma 6, com estado sincronizado em tempo real.

## Decisões (design tree)

| # | Decisão | Valor |
|---|---|---|
| 1 | Escopo do ON | Booleano único: `org.freedesktop.ScreenSaver.Inhibit` + `systemd-inhibit --what=idle:sleep --mode=block` |
| 2 | Núcleo | Daemon de sessão residente, nome D-Bus `org.local.DeskAwake`, binário `deskawake` |
| 3 | Ciclo de vida | Residente pela sessão; `.service` de D-Bus como fallback de ativação; UIs assinam `NameOwnerChanged` e forçam OFF se o dono desaparecer |
| 4 | Sair | `SetActive(false)` → `Quit()` → fecha a UI (kill switch explícito) |
| 5 | Persistência | Só posição e tema; estado sempre nasce OFF; posição validada contra a área útil atual |
| 6 | CLI | `on/off/toggle/status/daemon/ui`; `status` sai 0=ON, 1=OFF, 3=daemon inacessível; `ui` recusa Wayland salvo `--force`/`DESKAWAKE_FORCE_UI=1`; `status` não dispara auto-start |
| 7 | Plasmoid ↔ daemon | `gdbus` nativo (sem spawn de Python) + `DBusServiceWatcher` + polling de 2 s |
| 8 | Camada Z (GTK/Marco) | `keep_below` + `skip_taskbar` + `skip_pager` + `stick()`, aplicados antes de `show_all()` e reforçados no `realize`; translucidez só se `is_composited()` |
| 9 | Instalador | Verifica e instrui por padrão; `--install-deps` opt-in; `--only-kde`/`--only-mate`/`--all` |
| 10 | Autostart | XDG `.desktop` (daemon nos dois DEs, widget só no MATE) + `.service`; Plasmoid adicionado manualmente |
| 11 | Inibições | `idle:sleep`; fechar a tampa **ainda suspende** |
| 12 | Sucesso/erro | Tudo ou nada: ON só com ambos os inibidores confirmados; senão libera tudo e estado `error` |
| 13 | Tema | Só GTK (`auto`/`light`/`dark`); Plasmoid segue o Plasma nativamente |
| 14 | Menu GTK | `Ativar/Desativar` (rótulo dinâmico) · `Tema ▸` · `Iniciar com o sistema ☑` · `Sair` |
| 15 | Fonte | Stack `Inter → Cantarell → Noto Sans → DejaVu Sans`; `install.sh` sugere `fonts-inter` sem bloquear |
| 16 | Plasmoid UI | 124×42 fixo; menu só `Ativar/Desativar` + itens nativos do Plasma |
| 17 | Arrasto | Superfície inteira, threshold de 5 px; alterna só se o `press` começou no toggle |
| 18 | Uninstall | Remove tudo exceto `~/.config/deskawake/`; `--purge` remove config; `Quit()` + fallback por PID; idempotente; sem `sudo` |
| 19 | Testes | `pytest` + `dbus-run-session` com ScreenSaver falso; `verify.sh`; checklist manual MATE; sem GUI |
| 20 | Meta | MIT, Python ≥ 3.10, README pt-BR + inglês, árvore do briefing |

Decisões de contrato derivadas:

| # | Decisão | Valor |
|---|---|---|
| 21 | `SetActive` | Retorna o novo estado (`"on"`/`"off"`/`"error"`), igual a `Toggle()` |
| 22 | Layout do Plasmoid | `plasmoid/metadata.json` + `plasmoid/contents/ui/main.qml` (o prefixo `package/` é convenção de repo-fonte do KDE, não do pacote instalado) |
| 23 | Arrasto × `Gtk.Switch` | Movimento > 5 px suprime `state-set`/`activate` até o release |

## Fluxo alvo

### Ativar

1. UI chama `SetActive(true)` (ou `Toggle()`).
2. Daemon entra em `activating` (interno) e, nesta ordem:
   1. sobe o filho `systemd-inhibit ... sleep infinity` com `PR_SET_PDEATHSIG` e grupo de processos próprio;
   2. espera 200 ms e confirma que o filho continua vivo (se saiu, lê `stderr` e falha);
   3. chama `org.freedesktop.ScreenSaver.Inhibit("DeskAwake", motivo)` na **mesma conexão** D-Bus do daemon e guarda o cookie.
3. Sucesso: estado `on`, sinal `StateChanged("on")`.
4. Falha em qualquer passo: libera o que já foi adquirido, guarda o motivo em `last_error`, estado `error`, `StateChanged("error")`.

### Desativar

1. `SetActive(false)` → `UnInhibit(cookie)` → encerra o filho (`SIGTERM`, espera até 2 s, `SIGKILL` no grupo) → estado `off`.

### Encerrar

- `SIGTERM`/`SIGINT`/`Quit()`: desativa (passos acima), fecha a conexão, sai 0.
- Morte abrupta do daemon: `PDEATHSIG` mata o filho e o barramento libera o cookie automaticamente.

### Sincronização das UIs

- Assinam `StateChanged` e `NameOwnerChanged` para `org.local.DeskAwake`.
- Dono desapareceu → estado visual `off` imediato; próxima ação reativa o daemon via `.service`.
- `org.freedesktop.ScreenSaver` caiu com estado `on` → daemon vai para `error`; quando o serviço reaparece, re-adquire o cookie e volta a `on`.

## Contratos

### D-Bus (sessão)

- Nome: `org.local.DeskAwake`
- Objeto: `/org/local/DeskAwake`
- Interface: `org.local.DeskAwake`
- Estados: `"on" | "off" | "error"`

| Membro | Assinatura | Semântica |
|---|---|---|
| `SetActive` | `b → s` | Aplica e retorna o estado resultante |
| `Toggle` | `→ s` | Inverte e retorna o estado resultante |
| `GetState` | `→ s` | Estado atual (não altera nada) |
| `GetLastError` | `→ s` | Motivo do último erro; vazio se não houver |
| `Quit` | `→ ()` | Desativa e encerra o daemon |
| `StateChanged` | `s` | Emitido a cada mudança de estado |

O daemon adquire o nome com `DO_NOT_QUEUE`; se já houver dono, sai 0. `status` usa `NameHasOwner` antes de `GetState` (sem auto-start).

### Configuração — `~/.config/deskawake/config.json`

```json
{
  "version": 1,
  "theme": "auto",
  "position": { "x": 1234, "y": 24 }
}
```

- `theme`: `auto` (padrão), `light`, `dark`.
- `position` ausente → canto superior direito do monitor primário, margem de 24 px.
- Posição restaurada só se o ponto cair dentro da área útil de algum monitor; senão volta ao padrão.
- Arquivo corrompido → renomeia para `config.json.bak`, recria com padrões.

### CLI

```
deskawake on|off|toggle|status
deskawake daemon
deskawake ui [--force]
```

- `status`: `0` = on, `1` = off, `3` = daemon inacessível; imprime `on|off|error`.
- `ui`: recusa `XDG_SESSION_TYPE=wayland` ou `WAYLAND_DISPLAY` definido, salvo `--force`/`DESKAWAKE_FORCE_UI=1`.
- `ui` é single-instance via nome `org.local.DeskAwake.Ui`; segunda invocação sai 0.

### Arquivos instalados

```
~/.local/share/deskawake/            código (core/, ui_gtk/, assets/, bin/)
~/.local/bin/deskawake               launcher (wrapper absoluto)
~/.local/share/dbus-1/services/org.local.DeskAwake.service
~/.config/autostart/deskawake-daemon.desktop
~/.config/autostart/deskawake-widget.desktop      (só MATE)
~/.config/deskawake/config.json                   (criado no 1º uso)
~/.local/state/deskawake/daemon.log               (+ .log.1, corte 256 KB)
~/.local/share/plasma/plasmoids/org.local.deskawake/   (via kpackagetool6)
```

### Aparência (comum)

- Pílula 124×42, cantos arredondados, superfície grafite `#20252B` a 82–90% de opacidade, borda fina, sem gradientes/sombras.
- Símbolo 22×22 ("círculo aberto com ponto de luz"), 9 px de respiro, nome `DeskAwake` 12 px semibold `#F0F3F5`, toggle 32×18.
- Cores: menta `#80D9A4` (on), cinza `#929DA5` (off), âmbar `#E9B85C` (ativando), vermelho `#E47F7F` (erro).
- Símbolo e nome permanecem neutros; o toggle é o único indicador de estado.
- Hover: realce sutil da superfície. Sem animação contínua.

## Tarefas de implementação

1. **Esqueleto do repo** — árvore aprovada, `LICENSE` (MIT), `pyproject.toml` mínimo para `pytest` (sem packaging de distro).
2. **`core/config.py`** — leitura/escrita atômica do JSON, defaults, validação de posição contra `Gdk` (na UI) e fallback.
3. **`core/environment.py`** — detecção de DE/sessão (`XDG_CURRENT_DESKTOP`, `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`), alvos do instalador.
4. **`core/inhibitors.py`** — `SystemdInhibit` (spawn, `PDEATHSIG`, confirmação de 200 ms, kill de grupo) e `ScreenSaverInhibit` (cookie na conexão do daemon), com fakes injetáveis.
5. **`core/state.py`** — máquina `off/activating/on/deactivating/error`, all-or-nothing, `last_error`.
6. **`core/daemon.py`** — barramento, objeto D-Bus, sinais, `NameOwnerChanged` do ScreenSaver, SIGTERM/SIGINT, log rotativo.
7. **`core/cli.py` + `bin/deskawake`** — subcomandos, códigos de saída, guarda Wayland, single-instance da UI.
8. **`ui_gtk/widget.py`** — janela 124×42, hints antes de `show_all()`, drag com threshold e supressão de `state-set`, menu, persistência de posição, tooltip de erro, tema.
9. **`ui_gtk/theme.py` + `assets/`** — CSS das 3 variantes, SVG simbólico, fallback opaco sem compositor.
10. **`plasmoid/`** — `metadata.json`, `contents/ui/main.qml` (124×42, `Plasma5Support` executável + `DBusServiceWatcher`, polling 2 s, estados).
11. **`install.sh`** — checagem condicional de deps, cópia, launcher, `.service`, autostart, `kpackagetool6 -i/--upgrade`, flags de alvo.
12. **`uninstall.sh`** — `Quit()` + fallback por PID, remoção idempotente, `--purge`.
13. **`verify.sh`** — liga/desliga e inspeciona `systemd-inhibit --list`, estado D-Bus e ausência de órfãos.
14. **`tests/`** — unitários + integração (`dbus-run-session` + ScreenSaver falso).
15. **`README.md` + `README.en.md`** — uso, instalação, diagnóstico, checklist manual MATE, limitações.

## Verificação

### Automática

- `pytest tests/unit` — config/posição, parser de ambiente, comando `systemd-inhibit`, máquina de estados, falhas parciais (all-or-nothing), liberação de locks.
- `dbus-run-session -- pytest tests/integration` — ScreenSaver falso no barramento privado:
  - `on` → `systemd-inhibit --list` contém `deskawake`; `GetState() == "on"`;
  - `off` → lock ausente; `GetState() == "off"`;
  - cookie pertence à conexão (outra conexão não consegue `UnInhibit` com o cookie alheio);
  - `SIGTERM` libera os dois inibidores;
  - queda do ScreenSaver com estado `on` → `error`; retorno do serviço → `on`;
  - `PDEATHSIG` mata o filho quando o pai morre;
  - `Quit()` encerra o processo e o nome sai do barramento.
- `shellcheck` em `install.sh`, `uninstall.sh`, `verify.sh` (quando disponível).

### Manual — Linux Mint 22.3 MATE/X11 (obrigatório)

- [ ] Widget abre no canto superior direito, 24 px de margem, sem decoração.
- [ ] Não aparece em `Alt+Tab`, na barra de tarefas nem no pager; aparece em todos os workspaces (`stick`).
- [ ] Fica atrás de janelas normais e visível com a área de trabalho à mostra; "Mostrar área de trabalho" do Caja não o quebra.
- [ ] Arrastar funciona a partir de qualquer ponto, inclusive sobre o toggle; arrastar > 5 px não alterna.
- [ ] Clique no toggle alterna; clique fora não altera.
- [ ] Com o compositor do Marco desligado, a superfície fica sólida e legível.
- [ ] Posição sobrevive a logout; desconectar monitor externo faz o widget voltar ao padrão.
- [ ] Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sair`.
- [ ] `Sair` com estado ON libera imediatamente (`systemd-inhibit --list` sem `deskawake`).
- [ ] `kill -9` no daemon não deixa `systemd-inhibit` órfão nem tela presa.

### Manual — Kubuntu 26.04 / Plasma 6 Wayland

- [ ] `kpackagetool6 -i ./plasmoid` instala; `--upgrade` atualiza.
- [ ] Plasmoid adicionado à área de trabalho mostra 124×42, atrás das janelas, arrastável pelo Plasma.
- [ ] Toggle reflete `on/off/error`; remover o Plasmoid não desliga o estado de outros clientes.
- [ ] `deskawake ui` recusa Wayland com mensagem; `--force` abre para depuração.

## Notas ao implementador

- **Ordem dos hints**: `keep_below`, `skip_taskbar`, `skip_pager` e `stick()` **antes** de `show_all()`; reforce em `realize`/`map`. No Marco, `WindowTypeHint.DESKTOP` quebra clique/arrasto — não usar.
- **`Gtk.Switch` + drag**: conectar `state-set` e retornar `True` enquanto `dragged == True`; resetar a flag só no `button-release`. Sem isso o switch alterna ao soltar o mouse.
- **GTK3 não suporta `@font-face`** (verificado: `unknown @ rule`). Não tentar embutir fonte via CSS.
- **`systemd-inhibit`**: `--mode=block`, `--who=DeskAwake`, `--why` descritivo; o filho deve rodar em grupo próprio e com `PR_SET_PDEATHSIG` (via `preexec_fn`) para nunca sobreviver ao daemon.
- **Cookie**: só vale na conexão que o obteve — nunca abrir conexão nova para `UnInhibit`.
- **Plasmoid**: não existe dataengine `dbus` no Plasma 6; usar `Plasma5Support` engine `executable` com `gdbus` e `DBusServiceWatcher` para liveness. `gdbus` é binário de sistema, sempre no `PATH` do plasmashell.
- **Auto-start**: `status`/`off` usam `NameHasOwner` para não acordar o daemon sem necessidade.
- **Log**: corte em 256 KB com rotação para `daemon.log.1`; nunca logar credenciais (não há).
- **Docs**: README do usuário em pt-BR e inglês; spec/design internos em pt-BR.

## Referências

- `org.freedesktop.ScreenSaver` — D-Bus Interface Specification (freedesktop.org).
- `systemd-inhibit(1)` — logind inhibit locks.
- KDE — `kpackagetool6`, estrutura `metadata.json` + `contents/ui/main.qml` (verificado em Plasma 6 local).
- Inter — SIL Open Font License 1.1 (apenas dependência opcional sugerida).
