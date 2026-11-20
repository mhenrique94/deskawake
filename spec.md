# Spec — DeskAwake Widget

Data: 2026-11-19
Status: Aprovado (hidratado para Linux Mint 22.3 MATE em 19/11/2026; aguardando implementação)
Escopo: utilitário de desktop Linux (MATE/X11 e KDE Plasma 6/Wayland): núcleo Python, widget GTK3, Plasmoid QML, instalador/desinstalador e testes. Sem empacotamento para distros, sem suporte a Windows/macOS, sem testes de GUI.

> **Contexto de validação.** A especificação nasceu com contexto do **Kubuntu (KDE Plasma 6 / Wayland)**. Em **19/11/2026** foi hidratada e validada no **Linux Mint 22.3 “Zena” MATE 1.26 / X11** (desktop ASUS TUF B550M, sem tampa nem bateria). Apenas o **backend e a UI MATE** foram validados nesta máquina; toda afirmação marcada `[Kubuntu]` é **contexto original, não revalidado** aqui. Onde o valor original não se aplica ao Mint, o texto foi preservado e a variação validada foi acrescentada ao lado. A tabela “Variações por distro” consolida as diferenças; o apêndice “Validação no Mint 22.3” registra as evidências.
>
> **Convenções.** `[Kubuntu]` = contexto original da spec, não revalidado nesta rodada. `[Mint 22.3 MATE]` = verificado nesta máquina por leitura de ambiente, D-Bus, `gsettings`, EWMH, fontes, pacotes e código-fonte do MATE; **comportamento de janela** (hints, arrasto, translucidez) fica na checklist manual, porque não foi criado protótipo GUI. Sem marcação = afirmação comum às duas distros ou ainda não exercitada.

## Problema

Em Linux Mint MATE (X11) e Kubuntu (KDE Plasma 6 / Wayland), o usuário precisa impedir que a tela bloqueie/apague e que a máquina suspenda **por inatividade** durante vídeos, builds e downloads longos — sem instalar um app pesado e sem manter uma janela convencional aberta. O controle deve viver na área de trabalho, atrás das janelas normais, ser arrastável, não aparecer em `Alt+Tab`/barra de tarefas, e nunca deixar o sistema preso sem dormir depois que o usuário fechar o controle.

O mesmo núcleo precisa servir às duas interfaces: widget GTK3 no MATE e Plasmoid nativo no Plasma 6, com estado sincronizado em tempo real.

## Decisões (design tree)

| # | Decisão | Valor |
|---|---|---|
| 1 | Escopo do ON | Booleano único, **tudo ou nada**: inibidor de tela (cadeia da decisão 24) + `systemd-inhibit --what=idle --mode=block` `[Mint 22.3 MATE — validado]`. `[Kubuntu — contexto original]` `org.freedesktop.ScreenSaver.Inhibit` + `systemd-inhibit --what=idle:sleep --mode=block`; o `sleep` foi removido para não bloquear tampa/suspensão manual. |
| 2 | Núcleo | Daemon de sessão residente, nome D-Bus `org.local.DeskAwake`, binário `deskawake` |
| 3 | Ciclo de vida | Residente pela sessão; `.service` de D-Bus como fallback de ativação; UIs assinam `NameOwnerChanged` e forçam OFF se o dono desaparecer |
| 4 | Sair | `SetActive(false)` → `Quit()` → fecha a UI (kill switch explícito) |
| 5 | Persistência | Só posição e tema; estado sempre nasce OFF; posição validada contra a área útil atual |
| 6 | CLI | `on/off/toggle/status/daemon/ui`; `status` sai 0=ON, 1=OFF, 3=daemon inacessível; `ui` recusa Wayland salvo `--force`/`DESKAWAKE_FORCE_UI=1`; `status` não dispara auto-start |
| 7 | Plasmoid ↔ daemon | `[Kubuntu — contexto original, não revalidado]` `gdbus` nativo (sem spawn de Python) + `DBusServiceWatcher` + polling de 2 s |
| 8 | Camada Z (GTK/Marco) | `[Mint 22.3 MATE — atoms EWMH e compositor validados; comportamento de janela na checklist manual]` `keep_below` + `skip_taskbar` + `skip_pager` + `stick()`, aplicados antes de `show_all()` e reforçados no `realize`; translucidez só se `is_composited()` |
| 9 | Instalador | `[Mint 22.3 MATE — requisito: kpackagetool6 ausente]` `--all` instala só alvos disponíveis, avisa “KDE indisponível: `kpackagetool6` ausente” e deixa explícito que daemon+GTK foram instalados; `--only-kde` falha com código ≠ 0 quando o alvo pedido falta; `uninstall.sh` não falha se `kpackagetool6` não existir. `[Kubuntu]` original: verifica e instrui por padrão; `--install-deps` opt-in; `--only-kde`/`--only-mate`/`--all` |
| 10 | Autostart | XDG `.desktop` (daemon nos dois DEs, widget só no MATE) + `.service`; Plasmoid adicionado manualmente. `[Mint — diretório e arquivos XDG presentes; comportamento de login não exercitado]` |
| 11 | Inibições | `[Kubuntu — contexto original]` `idle:sleep`; fechar a tampa ainda suspende. `[Mint 22.3 MATE — validado por código/man; tampa não testável em desktop]` `idle` apenas + inibidor de tela; fechar a tampa **ainda suspende** e a suspensão manual também funciona — o `sleep` bloqueava as duas. |
| 12 | Sucesso/erro | Tudo ou nada: ON só com o inibidor de tela confirmado **e** o `systemd-inhibit` confirmado; senão libera tudo e estado `error` |
| 13 | Tema | Só GTK (`auto`/`light`/`dark`); Plasmoid segue o Plasma nativamente. `[Mint 22.3 MATE — schema/valores validados; troca em runtime na checklist]` `auto` = dark se `gtk-theme` contiver “dark” (case-insensitive) **ou** `gtk-application-prefer-dark-theme=true`; monitorar `notify::gtk-theme-name` e `notify::gtk-application-prefer-dark-theme`; **nunca** forçar `prefer-dark` globalmente. O MATE 1.26 não tem `color-scheme` em `org.mate.interface`. |
| 14 | Menu GTK | `Ativar/Desativar` (rótulo dinâmico) · `Tema ▸` · `Iniciar com o sistema ☑` · `Sair` |
| 15 | Fonte | Stack única `"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif` (famílias com espaço entre aspas; `sans-serif` por último). `[Kubuntu — contexto original]` `Inter → Cantarell → Noto Sans → DejaVu Sans`. `[Mint 22.3 MATE — validado]` Inter e Cantarell não instaladas; fonte nativa da UI é `Ubuntu 10`; fallback real Noto Sans; `fonts-inter` 4.0+ds-1 disponível no repositório, sugestão não bloqueante. |
| 16 | Plasmoid UI | `[Kubuntu — contexto original, não revalidado]` 124×42 fixo; menu só `Ativar/Desativar` + itens nativos do Plasma |
| 17 | Arrasto | Superfície inteira, threshold de 5 px; alterna só se o `press` começou no toggle |
| 18 | Uninstall | Remove tudo exceto `~/.config/deskawake/`; `--purge` remove config; `Quit()` + fallback por PID; idempotente; sem `sudo`; `[Mint — requisito: tolerar kpackagetool6 ausente]` |
| 19 | Testes | `pytest` + `dbus-run-session` com ScreenSaver falso; `verify.sh`; checklist manual MATE; sem GUI. `[Mint — decisão: GetInhibitors no MATE; teste de isolamento de cookie condicional ao backend; IsInhibited(8) como confirmação do proxy MATE→GSM]` |
| 20 | Meta | MIT, Python ≥ 3.10, README pt-BR + inglês, árvore do briefing. `[Mint — Python 3.12.3, PyGObject 3.48.2, pytest 7.4.4]` |

Decisões de contrato derivadas:

| # | Decisão | Valor |
|---|---|---|
| 21 | `SetActive` | Retorna o novo estado (`"on"`/`"off"`/`"error"`), igual a `Toggle()` |
| 22 | Layout do Plasmoid | `[Kubuntu]` `plasmoid/metadata.json` + `plasmoid/contents/ui/main.qml` (o prefixo `package/` é convenção de repo-fonte do KDE, não do pacote instalado) |
| 23 | Arrasto × `Gtk.Switch` | Movimento > 5 px suprime `state-set`/`activate` até o release |
| 24 | Backend de tela | Cadeia `org.freedesktop.ScreenSaver` → `org.mate.ScreenSaver` → `org.gnome.SessionManager`; no GSM usar `toplevel_xid=0` e `flags=IDLE (8)`. `xdg-screensaver` **descartado**: exige XID de janela viva e só faz `SimulateUserActivity` a cada 50 s, não é inibição. |
| 25 | Suspensão e tampa | `systemd-inhibit --what=idle --mode=block`; `sleep` **não** é inibido de propósito → fechar a tampa e a suspensão manual continuam funcionando. `[Kubuntu — pendente]` revalidar no PowerDevil/Plasma 6 se `ScreenSaver.Inhibit` + `--what=idle` cobrem a suspensão automática por inatividade (não só o bloqueio/desligamento de tela). |
| 26 | Cookie | `[Mint — validado]` o MATE **não valida o dono** do cookie: outra conexão consegue `UnInhibit`; o cookie morre junto com a conexão que chamou `Inhibit`. O teste de “isolamento de cookie” é condicional ao backend que impõe ownership. |
| 27 | Backend MATE | `mate-screensaver` 1.26.2 expõe somente `org.mate.ScreenSaver`; cada `Inhibit` é **proxy para o GSM com `xid=0` e `flags=IDLE (8)`** — cobre o `mate-screensaver` e o `mate-power-manager` (DPMS/idle; verificado no código-fonte). No master do projeto o nome FDO é adquirido como “soft”; a cadeia cobre versões antigas e novas. |

## Fluxo alvo

### Ativar

1. UI chama `SetActive(true)` (ou `Toggle()`).
2. Daemon entra em `activating` (interno) e, nesta ordem:
   1. sobe o filho `systemd-inhibit --what=idle --mode=block ... sleep infinity` com `PR_SET_PDEATHSIG` e grupo de processos próprio;
   2. espera 200 ms e confirma que o filho continua vivo (se saiu, lê `stderr` e falha);
   3. adquire o inibidor de tela na ordem **FDO → MATE → GSM**, na **mesma conexão** D-Bus do daemon, e guarda o nome do backend, o caminho e o cookie; no GSM usa `xid=0` e `flags=8`.
3. Confirmação do backend:
   - MATE: `GetInhibitors` contém a aplicação e, se o GSM existir, `IsInhibited(8) == true` (proxy do MATE). Se o proxy não confirmar, libera o cookie MATE e tenta o GSM diretamente.
   - GSM: `IsInhibited(8) == true`.
   - FDO: o cookie retornado é a confirmação disponível (não há `GetInhibitors` no contrato FDO).
4. Sucesso: estado `on`, sinal `StateChanged("on")`.
5. Falha em qualquer passo: libera o que já foi adquirido, guarda o motivo em `last_error`, estado `error`, `StateChanged("error")`.

> No MATE o `org.mate.ScreenSaver.Inhibit` já cria um inibidor GSM `IDLE=8`; **não** adquirir GSM adicionalmente quando o backend MATE foi confirmado.

### Desativar

1. `SetActive(false)` → `UnInhibit(cookie)` no backend ativo (FDO/MATE usam `UnInhibit`; GSM usa `Uninhibit` — “i” minúsculo) → encerra o filho (`SIGTERM`, espera até 2 s, `SIGKILL` no grupo) → estado `off`.

### Encerrar

- `SIGTERM`/`SIGINT`/`Quit()`: desativa (passos acima), fecha a conexão, sai 0.
- Morte abrupta do daemon: `PDEATHSIG` mata o filho e o barramento libera os cookies automaticamente (o cookie morre com a conexão).

### Sincronização das UIs

- Assinam `StateChanged` e `NameOwnerChanged` para `org.local.DeskAwake`.
- Dono desapareceu → estado visual `off` imediato; próxima ação reativa o daemon via `.service`.
- `NameOwnerChanged` do **backend ativo** (`org.freedesktop.ScreenSaver`, `org.mate.ScreenSaver` ou `org.gnome.SessionManager`):
  - caiu com estado `on` → daemon vai para `error`;
  - quando o serviço reaparece, re-adquire o cookie e volta a `on`;
  - se o backend ativo é o GSM e o `mate-session` terminou, o daemon encerra junto com a sessão.

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

### Backend de inibição de tela (por distro)

| Backend | Nome / objeto / interface | Métodos usados | Observações |
|---|---|---|---|
| FDO `[Kubuntu]` | `org.freedesktop.ScreenSaver` / `/org/freedesktop/ScreenSaver` (histórico KDE: `/ScreenSaver`) / `org.freedesktop.ScreenSaver` | `Inhibit(s,s) → u`, `UnInhibit(u)` | `[Mint — validado]` **ausente** no `mate-screensaver` 1.26.2 (sem dono e sem `.service`); no master do MATE é adquirido como “soft”. |
| MATE `[Mint 22.3 MATE — validado]` | `org.mate.ScreenSaver` / `/org/mate/ScreenSaver` / `org.mate.ScreenSaver` | `Inhibit(s,s) → u`, `UnInhibit(u)`, `GetInhibitors() → as` | Cada `Inhibit` cria proxy GSM `IDLE=8`; `GetInhibitors` devolve `Application="..."; Since="..."; Reason="...";`. |
| GSM (fallback) | `org.gnome.SessionManager` / `/org/gnome/SessionManager` / `org.gnome.SessionManager` | `Inhibit(s,u,s,u) → u`, `Uninhibit(u)`, `IsInhibited(u) → b`, `GetInhibitors() → ao` | Flags `1=LOGOUT`, `2=SWITCH`, `4=SUSPEND`, `8=IDLE`; usar `xid=0` e `flags=8`. Presente no MATE via `mate-session`. |

- **Ordem**: FDO → MATE → GSM; o primeiro que responder vence.
- **Confirmação**: MATE/GSM exigem `IsInhibited(8)` verdadeiro; MATE também confere `GetInhibitors`.
- **Cookie**: `u` (uint32); pertence à conexão que o obteve. No MATE não há validação de dono; outra conexão pode `UnInhibit`, mas o cookie morre quando a conexão original fecha. No GSM o cookie também morre com a conexão (verificado via `mate-session-inhibit`); ownership entre conexões não foi testado.
- **Sem `xdg-screensaver`**: não é backend do daemon; no MATE ele faria `SimulateUserActivity` a cada 50 s preso a um XID de janela — não é inibição real.

### `systemd-inhibit`

- `--what=idle --mode=block --who=DeskAwake --why=<motivo>`.
- `sleep` **não** é inibido: fechar a tampa e a suspensão manual (`systemctl suspend`/menu) continuam funcionando com o widget em ON.
- O `idle` do logind é um backstop; no Mint o `IdleAction` é `ignore`, então a cobertura real de idle/DPMS vem do backend de tela (MATE → proxy GSM `IDLE=8`; KDE → PowerDevil, pendente de revalidação).
- O filho roda em grupo próprio e com `PR_SET_PDEATHSIG` (via `preexec_fn`) para nunca sobreviver ao daemon.

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
~/.local/share/plasma/plasmoids/org.local.deskawake/   (via kpackagetool6) [Kubuntu]
```

- `[Mint — validado]` `kpackagetool6` **não existe** no Mint 22.3 nem nos repositórios (há apenas `kpackagetool5`, de Plasma 5); o alvo KDE é indisponível e deve ser pulado pelo instalador.

### Tampa e suspensão

- `[Mint 22.3 MATE — validado por código/man]` o `mate-power-manager` trata a tampa (segura um inibidor `handle-lid-switch` do logind) e chama `Suspend` no logind; como o DeskAwake **não** inibe `sleep`, a suspensão por tampa e a manual continuam.
- `[Kubuntu — pendente]` validar no PowerDevil/Plasma 6 se `org.freedesktop.ScreenSaver.Inhibit` + `systemd-inhibit --what=idle` bastam para a suspensão automática por inatividade; se o PowerDevil exigir uma inibição adicional, registrar e ajustar o backend.
- Esta máquina de validação é um **desktop sem tampa/bateria**; o comportamento de tampa não foi exercitado aqui e fica marcado “requer notebook” na checklist.

### Aparência (comum)

- Pílula 124×42, cantos arredondados, superfície grafite `#20252B` a 82–90% de opacidade, borda fina, sem gradientes/sombras.
- Símbolo 22×22 ("círculo aberto com ponto de luz"), 9 px de respiro, nome `DeskAwake` 12 px semibold `#F0F3F5`, toggle 32×18.
- Cores: menta `#80D9A4` (on), cinza `#929DA5` (off), âmbar `#E9B85C` (ativando), vermelho `#E47F7F` (erro).
- Símbolo e nome permanecem neutros; o toggle é o único indicador de estado.
- Hover: realce sutil da superfície. Sem animação contínua.
- Fonte: `"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif`; nomes com espaço entre aspas e `sans-serif` no fim para evitar queda de métricas.

## Tarefas de implementação

1. **Esqueleto do repo** — árvore aprovada, `LICENSE` (MIT), `pyproject.toml` mínimo para `pytest` (sem packaging de distro). `[Mint — Python 3.12.3/pytest 7.4.4]`
2. **`core/config.py`** — leitura/escrita atômica do JSON, defaults, validação de posição contra `Gdk` (na UI) e fallback.
3. **`core/environment.py`** — detecção de DE/sessão (`XDG_CURRENT_DESKTOP`, `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`), disponibilidade dos backends (FDO/MATE/GSM) e ferramentas do instalador (`kpackagetool6`, `gdbus`, `systemd-inhibit`).
4. **`core/inhibitors.py`** — `SystemdInhibit` (`--what=idle`, spawn, `PDEATHSIG`, confirmação de 200 ms, kill de grupo) e `ScreenSaverInhibit` com a cadeia FDO → MATE → GSM, cookie na conexão do daemon, confirmação por `GetInhibitors`/`IsInhibited(8)` e fakes injetáveis. Sem `xdg-screensaver`.
5. **`core/state.py`** — máquina `off/activating/on/deactivating/error`, all-or-nothing, `last_error`.
6. **`core/daemon.py`** — barramento, objeto D-Bus, sinais, `NameOwnerChanged` do backend ativo, SIGTERM/SIGINT, log rotativo.
7. **`core/cli.py` + `bin/deskawake`** — subcomandos, códigos de saída, guarda Wayland, single-instance da UI.
8. **`ui_gtk/widget.py`** — janela 124×42, hints antes de `show_all()`, drag com threshold e supressão de `state-set`, menu, persistência de posição, tooltip de erro, tema; conectar `notify::gtk-theme-name` e `notify::gtk-application-prefer-dark-theme`.
9. **`ui_gtk/theme.py` + `assets/`** — CSS das 3 variantes, detecção `auto` no MATE (nome do tema + `prefer-dark`, sem forçar o global), stack de fontes com aspas e `sans-serif`, SVG simbólico, fallback opaco sem compositor.
10. **`plasmoid/`** `[Kubuntu — não revalidado]` — `metadata.json`, `contents/ui/main.qml` (124×42, `Plasma5Support` executável + `DBusServiceWatcher`, polling 2 s, estados).
11. **`install.sh`** — checagem condicional de deps, cópia, launcher, `.service`, autostart, `kpackagetool6 -i/--upgrade`, flags de alvo; `--all` degrada com aviso explícito (daemon+GTK instalados); `--only-kde` falha se `kpackagetool6` faltar; sugere `fonts-inter` sem bloquear.
12. **`uninstall.sh`** — `Quit()` + fallback por PID, remoção idempotente, `--purge`; tolera `kpackagetool6` ausente.
13. **`verify.sh`** — liga/desliga e inspeciona `systemd-inhibit --list`, estado D-Bus, ausência de órfãos; no MATE, `GetInhibitors` e `IsInhibited(8)` enquanto ON.
14. **`tests/`** — unitários + integração (`dbus-run-session` + ScreenSaver falso): cadeia de backends, `--what=idle`, all-or-nothing, cookie condicional ao backend.
15. **`README.md` + `README.en.md`** — uso, instalação, diagnóstico, checklist manual MATE, limitações; documentar que suspensão manual e tampa continuam funcionando com ON.

## Verificação

### Automática

- `pytest tests/unit` — config/posição, parser de ambiente, seleção de backend, comando `systemd-inhibit --what=idle`, máquina de estados, falhas parciais (all-or-nothing), liberação de locks.
- `dbus-run-session -- pytest tests/integration` — ScreenSaver falso no barramento privado:
  - `on` → `systemd-inhibit --list` contém `deskawake`; `GetState() == "on"`;
  - `off` → lock ausente; `GetState() == "off"`;
  - cadeia FDO → MATE → GSM: o primeiro backend disponível vence; ausência de FDO cai para MATE; ausência de ambos cai para GSM com `xid=0`/`flags=8`;
  - teste de isolamento de cookie **condicional**: executar apenas para backends que impõem ownership; no MATE, verificar que o cookie morre com a conexão e que outra conexão consegue `UnInhibit` (comportamento documentado);
  - `SIGTERM` libera os dois inibidores;
  - queda do backend ativo com estado `on` → `error`; retorno do serviço → `on`;
  - `PDEATHSIG` mata o filho quando o pai morre;
  - `Quit()` encerra o processo e o nome sai do barramento.
- `shellcheck` em `install.sh`, `uninstall.sh`, `verify.sh` (quando disponível). `[Mint — shellcheck ausente nesta máquina]`

### Manual — Linux Mint 22.3 MATE/X11 (obrigatório)

- [ ] Widget abre no canto superior direito, 24 px de margem, sem decoração.
- [ ] Não aparece em `Alt+Tab`, na barra de tarefas nem no pager; aparece em todos os workspaces. Verificar explicitamente `keep_below`, `skip_taskbar`, `skip_pager` e `stick()` (criar um segundo workspace: a máquina de validação tem apenas 1).
- [ ] Fica atrás de janelas normais e visível com a área de trabalho à mostra; "Mostrar área de trabalho" do Caja não o quebra.
- [ ] Arrastar funciona a partir de qualquer ponto, inclusive sobre o toggle; arrastar > 5 px não alterna.
- [ ] Clique no toggle alterna; clique fora não altera.
- [ ] Com o compositor do Marco desligado, a superfície fica sólida e legível; com o compositor ligado, a translucidez aparece.
- [ ] Posição sobrevive a logout; desconectar monitor externo faz o widget voltar ao padrão.
- [ ] Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sair`.
- [ ] `Sair` com estado ON libera imediatamente (`systemd-inhibit --list` sem `deskawake`; `GetInhibitors` vazio; `IsInhibited(8)` falso).
- [ ] `kill -9` no daemon não deixa `systemd-inhibit` órfão nem tela presa.
- [ ] Estando o `mate-screensaver` com idle/lock habilitados, ON impede blanking/bloqueio; após OFF, o comportamento volta. (Nesta máquina idle/lock estão desabilitados; habilitar temporariamente.)
- [ ] Suspensão manual (`systemctl suspend`/menu) funciona com ON. (Teste destrutivo; opcional.)
- [ ] Fechar a tampa suspende com ON. (Requer notebook; esta máquina é desktop, sem tampa.)
- [ ] Alternar `Mint-Y` ↔ `Mint-Y-Dark` atualiza o tema do widget sem reiniciar.
- [ ] Com Inter ausente, o widget usa Ubuntu/Noto Sans sem erro de `@font-face`.
- [ ] O estado `error` (ex.: matar o `mate-screensaver`) mostra tooltip e libera o `systemd-inhibit`.

### Manual — Kubuntu 26.04 / Plasma 6 Wayland (`[Kubuntu — não revalidado nesta rodada]`)

- [ ] `kpackagetool6 -i ./plasmoid` instala; `--upgrade` atualiza.
- [ ] Plasmoid adicionado à área de trabalho mostra 124×42, atrás das janelas, arrastável pelo Plasma.
- [ ] Toggle reflete `on/off/error`; remover o Plasmoid não desliga o estado de outros clientes.
- [ ] `deskawake ui` recusa Wayland com mensagem; `--force` abre para depuração.
- [ ] **PowerDevil/idle**: com ON (`org.freedesktop.ScreenSaver.Inhibit` + `systemd-inhibit --what=idle`), a suspensão automática por inatividade fica bloqueada — não apenas o bloqueio/desligamento de tela. Se o PowerDevil exigir inibição adicional, registrar e ajustar o backend.
- [ ] **Tampa/suspensão manual**: com ON, fechar a tampa e a suspensão manual continuam suspendendo (o `sleep` não é inibido).
- [ ] **Cookie**: verificar se o backend FDO impõe ownership de cookie; se sim, o teste de isolamento roda; se não, documentar como no MATE.

## Notas ao implementador

- **Ordem dos hints**: `keep_below`, `skip_taskbar`, `skip_pager` e `stick()` **antes** de `show_all()`; reforce em `realize`/`map`. No Marco, `WindowTypeHint.DESKTOP` quebra clique/arrasto — não usar.
- **`Gtk.Switch` + drag**: conectar `state-set` e retornar `True` enquanto `dragged == True`; resetar a flag só no `button-release`. Sem isso o switch alterna ao soltar o mouse.
- **GTK3 não suporta `@font-face`** (verificado no Mint com GTK 3.24.41: `unknown @ rule`). Não tentar embutir fonte via CSS.
- **`systemd-inhibit`**: `--what=idle` (não `sleep`), `--mode=block`, `--who=DeskAwake`, `--why` descritivo; o filho deve rodar em grupo próprio e com `PR_SET_PDEATHSIG` (via `preexec_fn`) para nunca sobreviver ao daemon. O `CanSuspend` do logind **não** reflete inibidores; não usá-lo como teste de bloqueio.
- **Cookie**: só vale na conexão que o obteve — nunca abrir conexão nova para `UnInhibit`. No MATE não há checagem de dono (FIXME no upstream); não escrever teste universal de isolamento. No GSM o método é `Uninhibit` (i minúsculo), diferente de FDO/MATE.
- **Backend MATE**: `org.mate.ScreenSaver.Inhibit` já cria o proxy GSM `IDLE=8`; confirmar com `IsInhibited(8)` e **não** adquirir GSM de novo. Se o proxy não confirmar, liberar o cookie MATE e cair para o GSM.
- **FDO no MATE**: `mate-screensaver` 1.26.2 não expõe `org.freedesktop.ScreenSaver`; o master expõe como nome “soft”. Não assumir que o FDO existe em qualquer MATE — sempre tentar primeiro e cair para o MATE.
- **`xdg-screensaver`**: não usar. No MATE ele só faz `SimulateUserActivity` a cada 50 s preso a um XID de janela; não inibe DPMS/lock de verdade e acopla o ciclo de vida à janela.
- **Tema `auto`**: ler `gtk-theme` e `gtk-application-prefer-dark-theme`; conectar `notify::gtk-theme-name`/`notify::gtk-application-prefer-dark-theme`; não alterar o `prefer-dark` global. MATE 1.26 não tem `color-scheme`.
- **Fonte**: usar a stack única com aspas e `sans-serif` no fim; Inter é opcional (`fonts-inter` 4.0+ds-1 no Mint), Ubuntu é a nativa do MATE, Noto Sans é o fallback real.
- **Plasmoid** `[Kubuntu]`: não existe dataengine `dbus` no Plasma 6; usar `Plasma5Support` engine `executable` com `gdbus` e `DBusServiceWatcher` para liveness. `gdbus` é binário de sistema, sempre no `PATH` do plasmashell.
- **Instalador**: detectar alvo por ferramenta (`kpackagetool6`), não por nome de distro; `--all` degrada com aviso e deixa claro que daemon+GTK foram instalados; `--only-kde` falha; `uninstall.sh` tolera ausência.
- **Auto-start**: `status`/`off` usam `NameHasOwner` para não acordar o daemon sem necessidade.
- **Log**: corte em 256 KB com rotação para `daemon.log.1`; nunca logar credenciais (não há).
- **Docs**: README do usuário em pt-BR e inglês; spec/design internos em pt-BR.
- **Limite de validação**: só o backend/UI MATE foi validado; o Plasmoid e o comportamento do PowerDevil seguem baseados no contexto original do Kubuntu. A máquina é desktop (sem tampa/bateria); itens de tampa são “requer notebook”.

## Variações por distro

| Ponto | Kubuntu (contexto original) | Mint 22.3 MATE (validado 19/11/2026) |
|---|---|---|
| Inibidor de tela | `org.freedesktop.ScreenSaver.Inhibit` | `org.freedesktop.ScreenSaver` ausente no `mate-screensaver` 1.26.2; usar `org.mate.ScreenSaver` (fallback GSM). No master do MATE o FDO é adquirido como “soft”. |
| Suspensão | `systemd-inhibit --what=idle:sleep` | `--what=idle` apenas; tampa e suspensão manual continuam funcionando. |
| Cookie | Presumido com isolamento de dono; teste universal | Sem validação de dono; cookie morre com a conexão; teste condicional ao backend. |
| `xdg-screensaver` | Não especificado | Descartado explicitamente (XID + poke a cada 50 s, não é inibição). |
| Tema `auto` | Mecanismo não detalhado | `gtk-theme` contém “dark” **ou** `gtk-application-prefer-dark-theme`; sinais `notify::*`; sem `color-scheme`. |
| Fonte | `Inter → Cantarell → Noto Sans → DejaVu Sans` | Stack aditiva com `Ubuntu`; Inter/Cantarell não instaladas; `fonts-inter` disponível. |
| Instalador/KDE | `kpackagetool6` presente | `kpackagetool6` ausente nos repos; `--all` degrada, `--only-kde` falha, uninstall tolera. |
| Autostart | XDG + `.service` | XDG presente; comportamento de login não exercitado. |
| EWMH/hints | MATE/Marco | Atoms `SKIP_TASKBAR`, `SKIP_PAGER`, `STICKY`, `BELOW`, `UTILITY`, `DESKTOP` presentes; comportamento de janela na checklist. |
| Compositor | Marco | `compositing-manager=true`; selection owner de `_NET_WM_CM_S0` é o Marco; `Gdk.Screen.is_composited() == True`. |
| Caja/desktop | — | `org.mate.background show-desktop-icons=true`; janela do Caja é `DESKTOP`, sticky e skip pager/taskbar. |
| Tampa | “Ainda suspende” | “Ainda suspende” agora é consistente com `--what=idle`; não testável nesta máquina (desktop sem tampa). |
| Plasmoid | Suportado | Não aplicável nesta máquina; **não revalidado**. |
| Validação | Contexto original | Backend/UI MATE validados; GUI na checklist manual. |

## Validação no Mint 22.3 (evidências)

**Ambiente:** Linux Mint 22.3 “Zena” (`UBUNTU_CODENAME=noble`), kernel `7.0.0-43-generic`, `XDG_CURRENT_DESKTOP=MATE`, `XDG_SESSION_TYPE=x11`, `DESKTOP_SESSION=mate`; chassis **desktop** (ASUS TUF B550M-PLUS, sem bateria/tampa). MATE: `mate-session 1.26.1`, `marco 1.26.2`, `caja 1.26.3`, `mate-screensaver 1.26.2`, `mate-panel 1.27.1` (build do Ubuntu noble). GTK 3.24.41; Python 3.12.3; PyGObject 3.48.2; pytest 7.4.4; systemd 255.4; dbus 1.14.10; `shellcheck` ausente.

**D-Bus da sessão:**
- `org.freedesktop.ScreenSaver`: **sem dono** e **sem `.service`**.
- `org.mate.ScreenSaver`: dono `mate-screensaver` (`--no-daemon`), objeto `/org/mate/ScreenSaver`; métodos `Inhibit(s,s)→u`, `UnInhibit(u)`, `GetInhibitors()→as`, `GetActive`, `SetActive`, etc.
- `org.gnome.SessionManager`: dono `mate-session`; `Inhibit(s,u,s,u)→u`, `Uninhibit(u)`, `IsInhibited(u)→b`, `GetInhibitors()→ao`; flags 1/2/4/8.
- `Inhibit` MATE com cookie `u`; `GetInhibitors` contém `Application="deskawake-probe"`; `UnInhibit` de **outra conexão** retorna sucesso; o cookie morre quando a conexão que inibiu fecha (testado).
- `org.mate.ScreenSaver.Inhibit` → `org.gnome.SessionManager.IsInhibited(8)` muda de `false` para `true` e volta a `false` após `UnInhibit` (proxy MATE→GSM confirmado em runtime).
- `mate-session-inhibit` (1.26.1) inibe `idle`/`suspend` via flags GSM; o CLI exige `--inhibit <flags>` como argumento separado (`--inhibit=idle` falha) e usa `:` entre flags; cookie liberado ao sair.

**systemd/logind:**
- `systemd-inhibit --what=idle:sleep --who=deskawake-probe --why=probe --mode=block true` → exit 0; `--what=idle --mode=block true` → exit 0; nenhum resíduo em `systemd-inhibit --list`.
- `systemd-logind` ativo; PID 1 = systemd; `IdleAction=ignore`; `HandleLidSwitch=suspend` (comentado no `logind.conf`, default).
- `systemd-inhibit(1)`: `--mode=block` proíbe a operação sem limite de tempo. `CanSuspend` do logind **não** reflete inibidores (retornou `yes` com um lock ativo) — não foi feito teste destrutivo de suspensão; a conclusão sobre tampa/suspensão vem da man page + código do `mate-power-manager`.
- `mate-power-manager` trata a tampa (`handle-lid-switch` block) e chama `Suspend` no logind; seu laço de idle consulta GSM `IsInhibited(8/4)` (`gpm-idle.c`/`gpm-session.c`).

**EWMH/Marco:**
- `_NET_SUPPORTED` contém `_NET_WM_STATE_SKIP_TASKBAR`, `SKIP_PAGER`, `STICKY`, `BELOW`, `ABOVE`, `_NET_WM_WINDOW_TYPE_DESKTOP`, `UTILITY`, `_NET_WM_DESKTOP`, `_NET_SHOWING_DESKTOP`, `_NET_CLIENT_LIST`, `_NET_ACTIVE_WINDOW`.
- `_NET_NUMBER_OF_DESKTOPS=1`, `_NET_CURRENT_DESKTOP=0`, `_NET_WORKAREA=0,0,1920,1050` (painel inferior de 30 px); 1920×1080, Xft.dpi=96.
- Compositor: `marco --composite --replace`; `org.mate.Marco.general compositing-manager=true`; `_NET_WM_CM_S0` sem propriedade na raiz, mas com **selection owner** (janela 1×1 do Marco); `Gdk.Screen.is_composited() == True`.
- Janela do Caja: “Área de trabalho”, `_NET_WM_WINDOW_TYPE_DESKTOP`, `_NET_WM_STATE=SKIP_PAGER,SKIP_TASKBAR,STICKY`, `_NET_WM_DESKTOP=4294967295`; `show-desktop-icons=true`.
- `_NET_SHOWING_DESKTOP` é átomo suportado, mas a propriedade de raiz estava ausente no momento da coleta; não foi acionado “mostrar desktop”.

**GTK/gsettings/fontes:**
- `org.mate.interface`: `gtk-theme='Squared'` (tema custom do usuário, **não** empacotar), `icon-theme='Mint-L-Grey'`, `font-name='Ubuntu 10'`; **não existe** `color-scheme`; `gtk-application-prefer-dark-theme=False` em runtime.
- Temas do sistema presentes: `Mint-Y`, `Mint-Y-Dark`, `Mint-L*` (incl. `Mint-L-Dark*`), `Adwaita`, `Adwaita-dark`.
- `org.mate.screensaver`: `idle-activation-enabled=false`, `lock-enabled=false` (config do usuário; habilitar para o teste manual).
- `org.mate.power-manager`: `button-lid-ac='suspend'`, `button-lid-battery='suspend'`, `action-sleep-type-ac='suspend'`, `sleep-display-ac=1800`, `dpms-method-ac='off'`; esses são os nomes reais das chaves neste MATE — não usar nomes de outros DEs.
- Fontes: `fc-match Inter` → Noto Sans; `fc-match Cantarell` → Noto Sans; `fc-match "Noto Sans"` → Noto Sans; `fc-match "DejaVu Sans"` → DejaVu Sans; `fc-match sans-serif` → Noto Sans; Inter/Cantarell **não instaladas**; `fonts-inter` 4.0+ds-1 disponível (noble/universe).
- `Gtk.CssProvider.load_from_data('@font-face {...}')` → `unknown @ rule` (GTK 3.24.41).

**Ferramentas/instalação:**
- `gdbus`, `dbus-run-session`, `xprop`, `wmctrl` presentes; `~/.local/bin` no `PATH` via `~/.profile`/`~/.bashrc`.
- `kpackagetool6` **ausente** e sem candidato no apt; `kpackagetool5` 5.115.0 instalado; `plasma-desktop` ausente (candidato Plasma 5).
- Autostart: `/etc/xdg/autostart` com `mate-power-manager`, `mate-screensaver`, `mate-settings-daemon` etc.; `~/.config/autostart` existe.
- `fonts-inter` disponível; `shellcheck` ausente.

**Limitações desta validação:**
- Não foi criado protótipo GUI: empilhamento, `Alt+Tab`, arrasto, `stick()` e translucidez ficam na checklist manual.
- Máquina desktop: tampa/bateria não testadas; `LidIsClosed` não existe no logind desta máquina.
- Kubuntu/Plasma 6 não foi revalidado; o Plasmoid e o comportamento do PowerDevil seguem o contexto original.
- `CanSuspend` não é um teste válido de inibição; não foi feito teste destrutivo de suspensão.

## Referências

- `org.freedesktop.ScreenSaver` — D-Bus Interface Specification (freedesktop.org).
- `org.mate.ScreenSaver` — `mate-screensaver` 1.26.2, objeto `/org/mate/ScreenSaver`; código: `gs-listener-dbus.c` (proxy GSM `IDLE=8`, FIXME de ownership de cookie; FDO como nome “soft” no master) — https://github.com/mate-desktop/mate-screensaver
- `org.gnome.SessionManager` — `mate-session` 1.26.1; flags de inibição 1/2/4/8.
- `mate-power-manager` — `gpm-idle.c`/`gpm-session.c` (idle/DPMS consultam GSM `IsInhibited(8/4)`) — https://github.com/mate-desktop/mate-power-manager
- `systemd-inhibit(1)` — semântica de `--what` e `--mode=block`; logind.
- KDE — `kpackagetool6`, estrutura `metadata.json` + `contents/ui/main.qml` `[Kubuntu — verificado em Plasma 6 local, não revalidado nesta rodada]`.
- Linux Mint 22.3 “Zena” — `UBUNTU_CODENAME=noble`; pacotes MATE 1.26.x.
- Inter — SIL Open Font License 1.1 (apenas dependência opcional sugerida; `fonts-inter` 4.0+ds-1).
