# Spec — DeskAwake Widget

Data: 2026-11-19
Status: Aprovado (hidratado para Linux Mint 22.3 MATE e Kubuntu 26.04 / Plasma 6.6 em 19/11/2026; aguardando implementação)
Escopo: utilitário de desktop Linux (MATE/X11 e KDE Plasma 6/Wayland): núcleo Python, widget GTK3, Plasmoid QML, instalador/desinstalador e testes. Sem empacotamento para distros, sem suporte a Windows/macOS, sem testes de GUI.

> **Contexto de validação.** A especificação nasceu com contexto do **Kubuntu (KDE Plasma 6 / Wayland)**. Em **19/11/2026** foi hidratada e validada no **Linux Mint 22.3 “Zena” MATE 1.26 / X11** (desktop ASUS TUF B550M, sem tampa nem bateria) e, na mesma data, o **backend KDE foi revalidado no Kubuntu 26.04.1 / KDE Plasma 6.6.7 / Wayland** (notebook com tampa e bateria, eDP-1 1920×1200). O backend/UI MATE foi validado por leitura de ambiente; o backend KDE foi validado por D-Bus, testes empíricos de inibição e leitura do código-fonte do PowerDevil/kscreenlocker. Onde um valor não se aplica à outra distro, o texto preserva o original e acrescenta a variação validada. A tabela “Variações por distro” consolida as diferenças; os apêndices “Validação no Mint 22.3” e “Validação no Kubuntu 26.04” registram as evidências.
>
> **Convenções.** `[Kubuntu 26.04 / Plasma 6.6 — validado 19/11/2026]` = verificado nesta máquina (D-Bus, código-fonte do PowerDevil/kscreenlocker, pacotes). `[Kubuntu — contexto original]` = texto original ainda não revalidado (sem ocorrências nesta rodada). `[Mint 22.3 MATE — validado]` = verificado na máquina Mint. Sem marcação = comum às duas distros ou não exercitado. **Comportamento visual** (janela GTK, Plasmoid, arrasto) fica na checklist manual, porque não foi criado protótipo GUI.

## Problema

Em Linux Mint MATE (X11) e Kubuntu (KDE Plasma 6 / Wayland), o usuário precisa impedir que a tela bloqueie/apague e que a máquina suspenda **por inatividade** durante vídeos, builds e downloads longos — sem instalar um app pesado e sem manter uma janela convencional aberta. O controle deve viver na área de trabalho, atrás das janelas normais, ser arrastável, não aparecer em `Alt+Tab`/barra de tarefas, e nunca deixar o sistema preso sem dormir depois que o usuário fechar o controle.

O mesmo núcleo precisa servir às duas interfaces: widget GTK3 no MATE e Plasmoid nativo no Plasma 6, com estado sincronizado em tempo real.

## Decisões (design tree)

| # | Decisão | Valor |
|---|---|---|
| 1 | Escopo do ON | Booleano único, **tudo ou nada**: **mecanismo principal** = inibidor de tela (cadeia da decisão 24); **proteção paralela de ociosidade do logind** = `systemd-inhibit --what=idle --mode=block` (`--what=sleep` **nunca**, para não bloquear tampa nem suspensão manual). `[Mint 22.3 MATE — validado]` inibidor MATE + `--what=idle`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` `org.freedesktop.ScreenSaver.Inhibit` + `--what=idle`; o `sleep` **não** é inibido. No Plasma 6.6 o `kscreenlocker` implementa o `ScreenSaver.Inhibit` chamando `PolicyAgent.AddInhibition(ChangeScreenSettings=4)`, que cobre dim/DPMS, bloqueio de tela e suspensão por inatividade (implica `InterruptSession`). |
| 2 | Núcleo | Daemon de sessão residente, nome D-Bus `org.local.DeskAwake`, binário `deskawake` |
| 3 | Ciclo de vida | Residente pela sessão; `.service` de D-Bus como fallback de ativação; UIs assinam `NameOwnerChanged` e forçam OFF se o dono desaparecer |
| 4 | Sair | `SetActive(false)` → `Quit()` → fecha a UI (kill switch explícito) |
| 5 | Persistência | Só posição e tema; estado sempre nasce OFF; posição validada contra a área útil atual |
| 6 | CLI | `on/off/toggle/status/daemon/ui`; `status` sai 0=ON, 1=OFF, 3=daemon inacessível; `ui` recusa Wayland salvo `--force`/`DESKAWAKE_FORCE_UI=1`; `status` não dispara auto-start |
| 7 | Plasmoid ↔ daemon | `[Kubuntu 26.04 / Plasma 6.6 — validado]` módulo QML nativo `org.kde.plasma.workspace.dbus`: `SessionBus.asyncCall` (ações), `SignalWatcher` (`StateChanged` em tempo real) e `DBusServiceWatcher` (liveness); **sem** `Plasma5Support`, **sem** `gdbus` e **sem** polling. Exige Plasma ≥ 6.4 (`SignalWatcher`). |
| 8 | Camada Z (GTK/Marco) | `[Mint 22.3 MATE — atoms EWMH e compositor validados; comportamento de janela na checklist manual]` `keep_below` + `skip_taskbar` + `skip_pager` + `stick()`, aplicados antes de `show_all()` e reforçados no `realize`; translucidez só se `is_composited()` |
| 9 | Instalador | `[Kubuntu 26.04 / Plasma 6.6 — validado]` `kpackagetool6` 2.0 presente: `--all` instala daemon+GTK+Plasmoid; Plasmoid adicionado manualmente (“Adicionar widgets”); `--install-deps` opt-in, **sem `sudo`**, imprime os comandos `apt` (obrigatórios: `python3-gi`, `python3-dbus`, `systemd`, `kpackagetool6`, `libglib2.0-bin`; opcional: `fonts-inter`) e verifica `python3`/`gi`/`dbus`/`systemd-inhibit`/`kpackagetool6`/`gdbus`; instalação/atualização idempotente (`kpackagetool6 -i` ou `--upgrade`). `[Mint 22.3 MATE — requisito: kpackagetool6 ausente]` `--all` instala só alvos disponíveis, avisa “KDE indisponível: `kpackagetool6` ausente” e deixa explícito que daemon+GTK foram instalados; `--only-kde` falha com código ≠ 0 quando o alvo pedido falta; `uninstall.sh` não falha se `kpackagetool6` não existir. |
| 10 | Autostart | XDG `.desktop` (daemon nos dois DEs, widget só no MATE) + `.service`; Plasmoid adicionado manualmente. `[Kubuntu 26.04 / Plasma 6.6 — validado]` `~/.config/autostart` e `~/.local/bin` no `PATH`; Plasmoid entra em “Adicionar widgets”; comportamento de login não exercitado. `[Mint — diretório e arquivos XDG presentes; comportamento de login não exercitado]` |
| 11 | Inibições | `[Kubuntu 26.04 / Plasma 6.6 — validado]` `idle` apenas; fechar a tampa e a suspensão manual **continuam** suspendendo — os caminhos de tampa/botão/menu do PowerDevil são `Explicit=true` e ignoram a política. O `sleep` bloqueava as duas. `[Mint 22.3 MATE — validado por código/man; tampa não testável naquela máquina]` `idle` apenas + inibidor de tela; fechar a tampa **ainda suspende** e a suspensão manual também funciona — o `sleep` bloqueava as duas. |
| 12 | Sucesso/erro | Tudo ou nada: ON só com o inibidor de tela confirmado **e** o `systemd-inhibit` confirmado; senão libera tudo e estado `error`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` como o PowerDevil só reflete a inibição após ~5 s (debounce do `AddInhibition`), o ON é **otimista**: entra em `on` com o cookie do `ScreenSaver` + filho do `systemd-inhibit` vivo e agenda a verificação assíncrona (~6 s); se a confirmação falhar e o estado ainda for `on`, reverte para `error` e emite `StateChanged`. |
| 13 | Tema | GTK: só `auto`/`light`/`dark`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` Plasmoid: superfície/texto/fonte pelo tema do Plasma (`Kirigami.Theme.backgroundColor`/`textColor`/`defaultFont`), mantendo forma/opacidade da pílula; cores de **estado** fixas (menta/cinza/vermelho) + spinner neutro de progresso. `[Mint 22.3 MATE — schema/valores validados; troca em runtime na checklist]` `auto` = dark se `gtk-theme` contiver “dark” (case-insensitive) **ou** `gtk-application-prefer-dark-theme=true`; monitorar `notify::gtk-theme-name` e `notify::gtk-application-prefer-dark-theme`; **nunca** forçar `prefer-dark` globalmente. O MATE 1.26 não tem `color-scheme` em `org.mate.interface`. |
| 14 | Menu GTK | `Ativar/Desativar` (rótulo dinâmico) · `Tema ▸` · `Iniciar com o sistema ☑` · `Sair` |
| 15 | Fonte | Stack única `"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif` (famílias com espaço entre aspas; `sans-serif` por último). `[Kubuntu 26.04 / Plasma 6.6 — validado]` fonte da UI é `Noto Sans 10`; `Ubuntu` presente; Inter/Cantarell **não** instaladas; `fonts-inter` 4.1+ds-1 disponível; no Plasmoid a fonte é a do tema do Plasma. `[Mint 22.3 MATE — validado]` fonte nativa da UI é `Ubuntu 10`; fallback real Noto Sans; `fonts-inter` 4.0+ds-1 disponível no repositório, sugestão não bloqueante. |
| 16 | Plasmoid UI | `[Kubuntu 26.04 / Plasma 6.6 — validado]` **124×42 lógico fixo e não redimensionável** (`Layout.minimum/preferred/maximum` = 124×42 no `PlasmoidItem`; conteúdo interno contido, com `elide` em textos curtos); posição 100% gerenciada pelo Plasma (`ItemGeometries-<W>x<H>` no `appletsrc`), não pelo `config.json`. Menu: `Ativar/Desativar` (rótulo dinâmico) + `Sair` (`SetActive(false)` → `Quit()`) + itens nativos do Plasma (`Remover widget`, `Configurar`). **Sem** `Tema ▸` e **sem** `Iniciar com o sistema` (exclusivos do menu GTK). Tema/fonte na decisão 13 (`Kirigami.Theme`). |
| 17 | Arrasto | **GTK/MATE**: superfície inteira, threshold de 5 px; alterna só se o `press` começou no toggle. `[Kubuntu 26.04 / Plasma 6.6 — validado]` o Plasmoid usa o arrasto nativo do containment (`AppletsLayout`/`ItemContainer` com `AfterPressAndHold`); clique rápido no toggle alterna e **não** dispara arrasto; se os widgets estiverem travados, pressionar e segurar não move. |
| 18 | Uninstall | Remove tudo exceto `~/.config/deskawake/`; `--purge` remove config; `Quit()` + fallback por PID; idempotente; sem `sudo`; `[Mint — requisito: tolerar kpackagetool6 ausente]` |
| 19 | Testes | `pytest` + `dbus-run-session` com ScreenSaver falso; `verify.sh`; checklist manual MATE; sem GUI. `[Mint — decisão: GetInhibitors no MATE; teste de isolamento de cookie condicional ao backend; IsInhibited(8) como confirmação do proxy MATE→GSM]` `[Kubuntu 26.04 / Plasma 6.6 — validado]` fake de `PolicyAgent` com debounce **configurável** e `ActiveInhibitions`; **timeouts injetáveis** no núcleo (padrão ~5 s debounce / ~6 s verificação), restaurados no teardown; rotas rápidas: (i) confirmação dentro da janela, (ii) falha → `error` + `StateChanged("error")`, (iii) `SetActive(false)` cancela o timer; `@pytest.mark.slow` opt-in cobre o ciclo real de 5–6 s; queda/retorno do PowerDevil; **sem** teste de isolamento de cookie no KDE (não há ownership). |
| 20 | Meta | MIT, Python ≥ 3.10, README pt-BR + inglês, árvore do briefing. `[Kubuntu 26.04 / Plasma 6.6 — validado]` Python 3.14.4, PyGObject 3.56.2, `pytest` ausente (`python3-pytest` 9.0.2 no apt). `[Mint — Python 3.12.3, PyGObject 3.48.2, pytest 7.4.4]` |

Decisões de contrato derivadas:

| # | Decisão | Valor |
|---|---|---|
| 21 | `SetActive` | Retorna o novo estado (`"on"`/`"off"`/`"error"`), igual a `Toggle()` |
| 22 | Layout do Plasmoid | `[Kubuntu 26.04 / Plasma 6.6 — validado]` `plasmoid/metadata.json` + `plasmoid/contents/ui/main.qml` (o prefixo `package/` é convenção de repo-fonte do KDE, não do pacote instalado). `metadata.json` com `KPackageStructure: "Plasma/Applet"`, `KPlugin.Id/Name/Description/Icon/Category/License` e requisito de **Plasma ≥ 6.4** (`SignalWatcher`); instalação via `kpackagetool6 -i ./plasmoid` em `~/.local/share/plasma/plasmoids/org.local.deskawake/`. |
| 23 | Arrasto × `Gtk.Switch` | Movimento > 5 px suprime `state-set`/`activate` até o release |
| 24 | Backend de tela | Cadeia `org.freedesktop.ScreenSaver` → `org.mate.ScreenSaver` → `org.gnome.SessionManager`; no GSM usar `toplevel_xid=0` e `flags=IDLE (8)`. `xdg-screensaver` **descartado**: exige XID de janela viva e só faz `SimulateUserActivity` a cada 50 s, não é inibição. |
| 25 | Suspensão e tampa | `systemd-inhibit --what=idle --mode=block`; `sleep` **não** é inibido de propósito → fechar a tampa e a suspensão manual continuam funcionando. `[Kubuntu 26.04 / Plasma 6.6 — validado]` a suspensão automática por inatividade é do PowerDevil (`AutoSuspendIdleTimeoutSec`, 1800 s no AC desta máquina) e é bloqueada porque o `ScreenSaver.Inhibit` vira `ChangeScreenSettings` (implica `InterruptSession`); tampa/botão/menu são `Explicit=true` no PowerDevil e ignoram a política; o `--what=idle` do logind é backstop (`IdleAction=ignore` aqui). |
| 26 | Cookie | `[Mint — validado]` o MATE **não valida o dono** do cookie: outra conexão consegue `UnInhibit`; o cookie morre junto com a conexão que chamou `Inhibit`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` o kwin/kscreenlocker **também não valida o dono** (outra conexão consegue `UnInhibit`); o que garante o isolamento é o **ciclo de vida da conexão D-Bus do daemon** — o compositor/PowerDevil libera a inibição automaticamente se a conexão cair. O teste de “isolamento de cookie” é condicional ao backend que impõe ownership. |
| 27 | Backend MATE | `mate-screensaver` 1.26.2 expõe somente `org.mate.ScreenSaver`; cada `Inhibit` é **proxy para o GSM com `xid=0` e `flags=IDLE (8)`** — cobre o `mate-screensaver` e o `mate-power-manager` (DPMS/idle; verificado no código-fonte). No master do projeto o nome FDO é adquirido como “soft”; a cadeia cobre versões antigas e novas. |
| 28 | Backend KDE | `[Kubuntu 26.04 / Plasma 6.6 — validado]` `org.freedesktop.ScreenSaver.Inhibit` é o **mecanismo principal** de inibição de tela/ociosidade no KDE; o `kscreenlocker` o traduz para `PolicyAgent.AddInhibition(ChangeScreenSettings=4)` (implica `InterruptSession`). **Não** chamar o `PolicyAgent` diretamente para inibir (duplicaria cookies e acoplaria a internals do KDE); `systemd-inhibit --what=idle` atua em paralelo como proteção de ociosidade do `logind`. |
| 29 | Confirmação no KDE | `[Kubuntu 26.04 / Plasma 6.6 — validado]` hierarquia: **(a)** `PolicyAgent.ActiveInhibitions` contendo a nossa entrada `(who, why)`; **(b)** fallback `PolicyAgent.HasInhibition(4)`; **(c)** degradação para cookie + aviso em log se (a) e (b) não existirem. `who="deskawake"` e `why="DeskAwake active"` fixos (sem `gettext`), usados tanto no `Inhibit` quanto na busca. |
| 30 | Verificação assíncrona | `[Kubuntu 26.04 / Plasma 6.6 — validado]` o PowerDevil aplica o `AddInhibition` só após ~5 s (debounce). O daemon entra em `on` imediatamente (cookie + filho do `systemd-inhibit` vivo) e agenda `GLib.timeout_add_seconds(6, ...)`; se a confirmação falhar e o estado ainda for `on`, vai para `error` + `StateChanged`. **`SetActive(false)` durante a janela cancela o timer pendente** e segue o fluxo normal de desativação (decisão 33: a UI mostra spinner sem bloquear o clique). |
| 31 | Liveness no KDE | `[Kubuntu 26.04 / Plasma 6.6 — validado]` observar `org.kde.Solid.PowerManagement` **e** `org.freedesktop.ScreenSaver`; queda com `on` → `error` + `StateChanged`; retorno → descartar o cookie antigo, re-adquirir (`ScreenSaver.Inhibit` novo + nova verificação de ~6 s) e voltar a `on`. **Sem rajadas de retry**: falha repetida permanece em `error` com motivo em `GetLastError()`; o filho do `systemd-inhibit` é preservado (não reiniciar). `SetActive(false)` em `error` limpa de forma idempotente e vai para `off`. |
| 32 | Fim de sessão no KDE | `[Kubuntu 26.04 / Plasma 6.6 — validado]` encerrar em `org.freedesktop.DBus.Local.Disconnected` (barramento de sessão fechou): **não** fazer novas chamadas D-Bus, apenas encerrar o filho do `systemd-inhibit`, `loop.quit()` e sair 0. O barramento/PowerDevil já liberam a inibição e o `PDEATHSIG` cobre o filho. `org.kde.Shutdown`/`plasma-login-session` podem ser um gancho **opcional** de saída antecipada, nunca requisito. |
| 33 | Indicador de progresso | Spinner de **duas flechas circulares** (sync/refresh) no lugar da cor âmbar de “ativando”. **Chamada inicial** (`activating`/`deactivating`): spinner e toggle temporariamente bloqueado enquanto o `Toggle`/`SetActive` estiver em voo (evita duplo clique/corrida). **Verificação KDE (~6 s)**: estado visual permanece `on` (menta) + spinner; o clique **não** é bloqueado e `SetActive(false)` cancela a verificação pendente. Falha após ~6 s → `error` (vermelho) + tooltip/`GetLastError()`. Contrato D-Bus inalterado (sem estados extras de verificação). |

### Fechamento do design tree

A fronteira está vazia para o escopo desta rodada: backend KDE, UI do Plasmoid, instalador e testes/dev estão decididos e hidratados. O que resta é **implementação** e **validação manual** (checklists), não decisões. Itens de GUI (tamanho visual, empilhamento, spinner, tema em tema claro) e o teste destrutivo de tampa/suspensão só podem ser fechados com o protótipo e a máquina física.

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
   - KDE (FDO no Plasma 6.6): `[Kubuntu 26.04 / Plasma 6.6 — validado]` o cookie é imediato; a confirmação real é **assíncrona**: `PolicyAgent.ActiveInhibitions` deve conter `(who="deskawake", why="DeskAwake active")`; fallback `PolicyAgent.HasInhibition(4)`; se nenhum existir, cookie + aviso em log. O PowerDevil só aplica a inibição após ~5 s (debounce do `AddInhibition`).
4. Sucesso: estado `on`, sinal `StateChanged("on")`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` no KDE o `on` é **otimista** (cookie + filho vivo); a verificação assíncrona roda em ~6 s e, se falhar com o estado ainda `on`, vai para `error` + `StateChanged`.
5. Falha em qualquer passo: libera o que já foi adquirido, guarda o motivo em `last_error`, estado `error`, `StateChanged("error")`.

> No MATE o `org.mate.ScreenSaver.Inhibit` já cria um inibidor GSM `IDLE=8`; **não** adquirir GSM adicionalmente quando o backend MATE foi confirmado.
>
> No KDE o `org.freedesktop.ScreenSaver.Inhibit` já cria o `PolicyAgent.AddInhibition(ChangeScreenSettings=4)`; **não** chamar o `PolicyAgent` para inibir. O `PolicyAgent` é usado somente para confirmar (decisões 28–30).

### Desativar

1. `SetActive(false)` → `UnInhibit(cookie)` no backend ativo (FDO/MATE usam `UnInhibit`; GSM usa `Uninhibit` — “i” minúsculo) → encerra o filho (`SIGTERM`, espera até 2 s, `SIGKILL` no grupo) → estado `off`.
   - `[Kubuntu 26.04 / Plasma 6.6 — validado]` no KDE o `UnInhibit` do `ScreenSaver` é traduzido pelo `kscreenlocker` em `PolicyAgent.ReleaseInhibition`; se o estado era `error`, a limpeza é idempotente (descarta cookie antigo, mantém/remove o filho conforme necessário) e vai para `off`.

### Encerrar

- `SIGTERM`/`SIGINT`/`Quit()`: desativa (passos acima), fecha a conexão, sai 0.
- `[Kubuntu 26.04 / Plasma 6.6 — validado]` `org.freedesktop.DBus.Local.Disconnected` (logout/desligamento no Plasma): **não** fazer novas chamadas D-Bus no barramento morto; encerrar o filho do `systemd-inhibit` (SIGTERM, até 2 s, SIGKILL no grupo), `loop.quit()` e sair 0. A inibição já é liberada pelo PowerDevil quando a conexão cai. `org.kde.Shutdown`/`plasma-login-session` são gancho opcional, não requisito.
- Morte abrupta do daemon: `PDEATHSIG` mata o filho e o barramento libera os cookies automaticamente (o cookie morre com a conexão).

### Sincronização das UIs

- Assinam `StateChanged` e `NameOwnerChanged` para `org.local.DeskAwake`.
- Dono desapareceu → estado visual `off` imediato; próxima ação reativa o daemon via `.service`.
- `NameOwnerChanged` do **backend ativo** (`org.freedesktop.ScreenSaver`, `org.mate.ScreenSaver` ou `org.gnome.SessionManager`):
  - caiu com estado `on` → daemon vai para `error`;
  - quando o serviço reaparece, re-adquire o cookie e volta a `on`;
  - se o backend ativo é o GSM e o `mate-session` terminou, o daemon encerra junto com a sessão.
- `[Kubuntu 26.04 / Plasma 6.6 — validado]` no KDE a inibição efetiva vive no PowerDevil: observar **também** `org.kde.Solid.PowerManagement` além de `org.freedesktop.ScreenSaver`.
  - queda com `on` → `error` + `StateChanged`; retorno → descarta o cookie antigo, re-adquire (`ScreenSaver.Inhibit` novo) e agenda nova verificação de ~6 s;
  - falha repetida **não** entra em rajada de retry: permanece em `error` com o motivo em `GetLastError()`;
  - o filho do `systemd-inhibit` **não** é reiniciado só porque o PowerDevil caiu.

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
| FDO `[Kubuntu 26.04 / Plasma 6.6 — validado]` | `org.freedesktop.ScreenSaver` / `/org/freedesktop/ScreenSaver` / `org.freedesktop.ScreenSaver` | `Inhibit(s,s) → u`, `UnInhibit(u)` | Dono `kwin_wayland`; **sem** `GetInhibitors`; `Throttle`/`UnThrottle` existem mas não são usados. O `kscreenlocker` implementa `Inhibit` chamando `PolicyAgent.AddInhibition(ChangeScreenSettings=4)`. `[Mint — validado]` **ausente** no `mate-screensaver` 1.26.2 (sem dono e sem `.service`); no master do MATE é adquirido como “soft”. |
| MATE `[Mint 22.3 MATE — validado]` | `org.mate.ScreenSaver` / `/org/mate/ScreenSaver` / `org.mate.ScreenSaver` | `Inhibit(s,s) → u`, `UnInhibit(u)`, `GetInhibitors() → as` | Cada `Inhibit` cria proxy GSM `IDLE=8`; `GetInhibitors` devolve `Application="..."; Since="..."; Reason="...";`. |
| GSM (fallback) | `org.gnome.SessionManager` / `/org/gnome/SessionManager` / `org.gnome.SessionManager` | `Inhibit(s,u,s,u) → u`, `Uninhibit(u)`, `IsInhibited(u) → b`, `GetInhibitors() → ao` | Flags `1=LOGOUT`, `2=SWITCH`, `4=SUSPEND`, `8=IDLE`; usar `xid=0` e `flags=8`. Presente no MATE via `mate-session`. |
| PowerDevil `[Kubuntu 26.04 / Plasma 6.6 — validado]` | `org.kde.Solid.PowerManagement` / `/org/kde/Solid/PowerManagement/PolicyAgent` / `org.kde.Solid.PowerManagement.PolicyAgent` | `HasInhibition(u) → b`, `ActiveInhibitions → a(ssssu)` (leitura); `AddInhibition(u,s,s) → u` e `ReleaseInhibition(u)` **não** são chamados pelo daemon | Confirmação do ON no KDE. `AddInhibition(4)` tem debounce de ~5 s; `ChangeScreenSettings=4` implica `InterruptSession=1`. `ActiveInhibitions` traz `(what, who, why, mode, flags)` — casar `who`/`why` fixos. |

- **Ordem**: FDO → MATE → GSM; o primeiro que responder vence. `[Kubuntu 26.04 / Plasma 6.6 — validado]` no Kubuntu só o FDO existe; MATE/GSM ficam inativos.
- **Confirmação**: MATE/GSM exigem `IsInhibited(8)` verdadeiro; MATE também confere `GetInhibitors`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` no KDE a confirmação é `PolicyAgent.ActiveInhibitions` com `(who, why)` do DeskAwake; fallback `HasInhibition(4)`; senão cookie + log (decisão 29). O PowerDevil leva ~5 s para refletir (decisão 30).
- **Cookie**: `u` (uint32); pertence à conexão que o obteve. No MATE **e no KDE/kwin não há validação de dono**; outra conexão pode `UnInhibit`, mas a inibição morre quando a conexão original fecha (no KDE o PowerDevil observa o nome único do chamador). No GSM o cookie também morre com a conexão (verificado via `mate-session-inhibit`); ownership entre conexões não foi testado.
- **Sem `xdg-screensaver`**: não é backend do daemon; no MATE ele faria `SimulateUserActivity` a cada 50 s preso a um XID de janela — não é inibição real.

### `systemd-inhibit`

- `--what=idle --mode=block --who=DeskAwake --why=<motivo>`.
- `sleep` **não** é inibido: fechar a tampa e a suspensão manual (`systemctl suspend`/menu) continuam funcionando com o widget em ON.
- O `idle` do logind é um backstop; no Mint o `IdleAction` é `ignore`, então a cobertura real de idle/DPMS vem do backend de tela (MATE → proxy GSM `IDLE=8`). `[Kubuntu 26.04 / Plasma 6.6 — validado]` no Kubuntu o `IdleAction` também é `ignore`; a suspensão automática é do PowerDevil (`AutoSuspendIdleTimeoutSec`) e a cobertura vem do `ScreenSaver.Inhibit` → `ChangeScreenSettings`/`InterruptSession`. O `--what=idle` permanece como backstop para sistemas com `IdleAction` configurado.
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
~/.local/share/plasma/plasmoids/org.local.deskawake/   (via kpackagetool6) [Kubuntu 26.04 / Plasma 6.6 — validado]
```

- `[Kubuntu 26.04 / Plasma 6.6 — validado]` `kpackagetool6` 2.0 presente; `kpackagetool6 -i ./plasmoid` instala em `~/.local/share/plasma/plasmoids/org.local.deskawake/` e `--upgrade` atualiza.
- `[Mint — validado]` `kpackagetool6` **não existe** no Mint 22.3 nem nos repositórios (há apenas `kpackagetool5`, de Plasma 5); o alvo KDE é indisponível e deve ser pulado pelo instalador.

### Tampa e suspensão

- `[Mint 22.3 MATE — validado por código/man]` o `mate-power-manager` trata a tampa (segura um inibidor `handle-lid-switch` do logind) e chama `Suspend` no logind; como o DeskAwake **não** inibe `sleep`, a suspensão por tampa e a manual continuam.
- `[Kubuntu 26.04 / Plasma 6.6 — validado]` o PowerDevil trata tampa/botão (`handle-lid-switch` block no logind) e dispara a ação com `Explicit=true`, que **ignora** o `PolicyAgent`; a suspensão manual (menu/`systemctl suspend`/`org.freedesktop.PowerManagement.Suspend`) também é explícita ou passa pelo logind sem inibidor de `sleep`. Logo, com ON, tampa e suspensão manual continuam. A suspensão automática por inatividade é do PowerDevil (`AutoSuspendIdleTimeoutSec`, 1800 s no AC nesta máquina; dim 600 s; DPMS 900 s) e é bloqueada porque o `ScreenSaver.Inhibit` vira `ChangeScreenSettings` (implica `InterruptSession`).
- A máquina Mint de validação é um **desktop sem tampa/bateria**; a máquina Kubuntu é um **notebook com tampa e bateria** (eDP-1, 1920×1200). O teste destrutivo de tampa/suspensão fica na checklist manual do Kubuntu.

### Aparência

**Comum:** pílula 124×42, cantos arredondados, borda fina, sem gradientes/sombras; símbolo 22×22 ("círculo aberto com ponto de luz"), 9 px de respiro, nome `DeskAwake` 12 px semibold, toggle 32×18; símbolo e nome permanecem neutros e o toggle é o único indicador de estado; hover sutil, sem animação contínua. Cores de **estado** fixas: menta `#80D9A4` (on), cinza `#929DA5` (off), vermelho `#E47F7F` (erro). **Progresso**: spinner de duas flechas circulares (sync/refresh) em cor neutra (texto do tema), sem âmbar; anima só durante a chamada em voo e durante a verificação assíncrona do KDE; sem animação contínua fora desses casos.

**GTK/MATE:** superfície grafite `#20252B` a 82–90% de opacidade; texto `#F0F3F5`; fonte `"Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", sans-serif` (nomes com espaço entre aspas e `sans-serif` no fim para evitar queda de métricas).

**Plasmoid** `[Kubuntu 26.04 / Plasma 6.6 — validado]`: superfície/texto/fonte pelo tema do Plasma (`Kirigami.Theme.backgroundColor`, `textColor`, `defaultFont`), preservando a forma/opacidade da pílula; no BreezeDark o fundo de cartão do tema fica próximo do grafite. As cores de estado continuam fixas e semânticas, para o estado ser inequívoco em tema claro ou escuro.

## Tarefas de implementação

1. **Esqueleto do repo** — árvore aprovada, `LICENSE` (MIT), `pyproject.toml` mínimo para `pytest` (sem packaging de distro). `[Mint — Python 3.12.3/pytest 7.4.4]` `[Kubuntu 26.04 — Python 3.14.4/PyGObject 3.56.2; pytest ausente, `python3-pytest` 9.0.2 no apt]`
2. **`core/config.py`** — leitura/escrita atômica do JSON, defaults, validação de posição contra `Gdk` (na UI) e fallback. No Plasmoid a posição é do Plasma (`ItemGeometries`/appletsrc), não do `config.json`.
3. **`core/environment.py`** — detecção de DE/sessão (`XDG_CURRENT_DESKTOP`, `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`), disponibilidade dos backends (FDO/MATE/GSM + `PolicyAgent` no KDE) e ferramentas do instalador (`kpackagetool6`, `gdbus`, `systemd-inhibit`).
4. **`core/inhibitors.py`** — `SystemdInhibit` (`--what=idle`, spawn, `PDEATHSIG`, confirmação de 200 ms, kill de grupo) e `ScreenSaverInhibit` com a cadeia FDO → MATE → GSM, cookie na conexão do daemon, confirmação por `GetInhibitors`/`IsInhibited(8)`/`ActiveInhibitions` e fakes injetáveis. Sem `xdg-screensaver`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` confirmação KDE: `ActiveInhibitions` com `(who="deskawake", why="DeskAwake active")` → fallback `HasInhibition(4)` → cookie + log; verificação assíncrona em ~6 s.
5. **`core/state.py`** — máquina `off/activating/on/deactivating/error`, all-or-nothing, `last_error`. `[Kubuntu 26.04 / Plasma 6.6 — validado]` no KDE o `on` é otimista com verificação assíncrona que pode reverter para `error`.
6. **`core/daemon.py`** — barramento, objeto D-Bus, sinais, `NameOwnerChanged` do backend ativo, SIGTERM/SIGINT, log rotativo. `[Kubuntu 26.04 / Plasma 6.6 — validado]` observar `org.kde.Solid.PowerManagement` além do `org.freedesktop.ScreenSaver`; sem retry em rajada; preservar o filho do `systemd-inhibit`.
7. **`core/cli.py` + `bin/deskawake`** — subcomandos, códigos de saída, guarda Wayland, single-instance da UI. `[Kubuntu 26.04 / Plasma 6.6 — validado]` `deskawake ui` recusa Wayland (é o caso do Kubuntu) salvo `--force`/`DESKAWAKE_FORCE_UI=1`.
8. **`ui_gtk/widget.py`** — janela 124×42, hints antes de `show_all()`, drag com threshold e supressão de `state-set`, menu, persistência de posição, tooltip de erro, tema; conectar `notify::gtk-theme-name` e `notify::gtk-application-prefer-dark-theme`.
9. **`ui_gtk/theme.py` + `assets/`** — CSS das 3 variantes, detecção `auto` no MATE (nome do tema + `prefer-dark`, sem forçar o global), stack de fontes com aspas e `sans-serif`, SVG simbólico, fallback opaco sem compositor.
10. **`plasmoid/`** `[Kubuntu 26.04 / Plasma 6.6 — validado no backend]` — `metadata.json` (`KPackageStructure: "Plasma/Applet"`, Plasma ≥ 6.4) e `contents/ui/main.qml` (124×42 fixo via `Layout.minimum/preferred/maximum`, `SessionBus.asyncCall`, `SignalWatcher`, `DBusServiceWatcher`; **sem** `Plasma5Support`/`gdbus`/polling; registrar watchers antes de `GetState`; toggle só no clique rápido; arrasto nativo por press‑and‑hold; menu `Ativar/Desativar` + `Sair` + nativos; tema via `Kirigami.Theme` + cores de estado fixas; spinner de duas flechas na chamada e na verificação).
11. **`install.sh`** — checagem condicional de deps, cópia, launcher, `.service`, autostart, `kpackagetool6 -i/--upgrade` idempotente, flags de alvo; `--install-deps` opt-in imprime os comandos `apt` (sem `sudo`; `fonts-inter` como opcional) e verifica `python3`/`gi`/`dbus`/`systemd-inhibit`/`kpackagetool6`/`gdbus`; `--all` instala os alvos disponíveis (no Kubuntu, daemon+GTK+Plasmoid; no Mint, degrada com aviso explícito e deixa claro que daemon+GTK foram instalados); `--only-kde` falha se `kpackagetool6` faltar; sugere `fonts-inter` sem bloquear.
12. **`uninstall.sh`** — `Quit()` + fallback por PID, remoção idempotente, `--purge`; tolera `kpackagetool6` ausente.
13. **`verify.sh`** — liga/desliga e inspeciona `systemd-inhibit --list`, estado D-Bus, ausência de órfãos; no MATE, `GetInhibitors` e `IsInhibited(8)` enquanto ON; no KDE, aguardar ~6 s e conferir `ActiveInhibitions`/`HasInhibition(4)` e o `UnInhibit` do `ScreenSaver`.
14. **`tests/`** — unitários + integração (`dbus-run-session` + ScreenSaver/PolicyAgent falsos): cadeia de backends, `--what=idle`, all-or-nothing, cookie condicional ao backend, ON otimista + verificação assíncrona, queda/retorno do PowerDevil. `[Kubuntu 26.04 / Plasma 6.6 — validado]` fake do `PolicyAgent` com debounce configurável e `ActiveInhibitions`; timeouts injetáveis no núcleo (padrão ~5 s/~6 s) restaurados no teardown; rotas rápidas: confirmação, falha → `error` + `StateChanged("error")`, cancelamento por `SetActive(false)`; `@pytest.mark.slow` opt-in para o ciclo real. `pytest` 9.0.2 via `apt install python3-pytest`, rodando com `python3 -m pytest`; dependência **só de desenvolvimento**, nunca instalada pelo `install.sh`.
15. **`README.md` + `README.en.md`** — uso, instalação, diagnóstico, checklists manuais MATE e Kubuntu, limitações; documentar que suspensão manual e tampa continuam funcionando com ON, o debounce de ~5 s do KDE e o setup de testes (`sudo apt install python3-pytest`; `python3 -m pytest`).

## Verificação

### Automática

- `python3 -m pytest tests/unit` — config/posição, parser de ambiente, seleção de backend, comando `systemd-inhibit --what=idle`, máquina de estados, falhas parciais (all-or-nothing), liberação de locks. (`pytest` via `apt install python3-pytest`; ver apêndice do Kubuntu.)
- `dbus-run-session -- python3 -m pytest tests/integration` — ScreenSaver/PolicyAgent falsos no barramento privado:
  - `on` → `systemd-inhibit --list` contém `deskawake`; `GetState() == "on"`;
  - `off` → lock ausente; `GetState() == "off"`;
  - cadeia FDO → MATE → GSM: o primeiro backend disponível vence; ausência de FDO cai para MATE; ausência de ambos cai para GSM com `xid=0`/`flags=8`;
  - teste de isolamento de cookie **condicional**: executar apenas para backends que impõem ownership; no MATE **e no KDE/kwin**, verificar que o cookie morre com a conexão e que outra conexão consegue `UnInhibit` (comportamento documentado);
  - `[Kubuntu 26.04 / Plasma 6.6 — validado]` fake do `PolicyAgent` com **debounce configurável** e `ActiveInhibitions`; timeouts injetáveis (padrão ~5 s/~6 s, restaurados no teardown); ON otimista entra em `on` antes da confirmação; rotas rápidas: (i) confirmação dentro da janela, (ii) falha → `error` + `StateChanged("error")`, (iii) `SetActive(false)` cancela o timer; `@pytest.mark.slow` opt-in para o ciclo real; queda/retorno do `org.kde.Solid.PowerManagement` → `error`/`on` sem rajada de retry;
  - `SIGTERM` libera os dois inibidores;
  - queda do backend ativo com estado `on` → `error`; retorno do serviço → `on`;
  - `PDEATHSIG` mata o filho quando o pai morre;
  - `Quit()` encerra o processo e o nome sai do barramento.
- `shellcheck` em `install.sh`, `uninstall.sh`, `verify.sh` (quando disponível). `[Mint — shellcheck ausente nesta máquina]` `[Kubuntu 26.04 — shellcheck ausente; `python3-pytest` 9.0.2 disponível no apt]`

### Manual — Linux Mint 22.3 MATE/X11 (obrigatório)

- [ ] Widget abre no canto superior direito, 24 px de margem, sem decoração.
- [ ] Não aparece em `Alt+Tab`, na barra de tarefas nem no pager; aparece em todos os workspaces. Verificar explicitamente `keep_below`, `skip_taskbar`, `skip_pager` e `stick()` (criar um segundo workspace: a máquina de validação tem apenas 1).
- [ ] Fica atrás de janelas normais e visível com a área de trabalho à mostra; "Mostrar área de trabalho" do Caja não o quebra.
- [ ] Arrastar funciona a partir de qualquer ponto, inclusive sobre o toggle; arrastar > 5 px não alterna.
- [ ] Clique no toggle alterna; clique fora não altera.
- [ ] Durante `Toggle`/`SetActive`, o spinner de duas flechas aparece e o toggle fica bloqueado até a resposta; sem âmbar.
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

### Manual — Kubuntu 26.04 / Plasma 6.6 Wayland (backend validado; GUI pendente)

- [ ] `kpackagetool6 -i ./plasmoid` instala em `~/.local/share/plasma/plasmoids/org.local.deskawake/`; `--upgrade` atualiza. Reexecutar `./install.sh --all` não falha (idempotente); `--install-deps` imprime os comandos `apt` (obrigatórios × `fonts-inter` opcional) e não usa `sudo`.
- [ ] Plasmoid adicionado à área de trabalho mostra 124×42, atrás das janelas normais e visível com a área de trabalho à mostra.
- [ ] Arrasto: pressionar e segurar move o widget (comportamento nativo do Plasma); clique rápido no toggle alterna e **não** move. Se não arrastar, conferir “Widgets Travados” no menu da área de trabalho.
- [ ] Toggle reflete `on/off/error` em tempo real (transporte nativo, sem polling); remover o Plasmoid não desliga o estado de outros clientes.
- [ ] Menu: `Ativar/Desativar` (rótulo dinâmico), `Sair` (kill switch) e itens nativos do Plasma; `Sair` com ON libera imediatamente (`ActiveInhibitions` sem `deskawake`, `systemd-inhibit --list` sem `deskawake`).
- [ ] Spinner de duas flechas na chamada em voo (toggle bloqueado) e durante a verificação de ~6 s (toggle ainda `on`, clique aceito); desligar antes dos 6 s cancela a verificação sem `error`; falha após ~6 s vira `error` + tooltip.
- [ ] `deskawake ui` recusa Wayland com mensagem; `--force` abre para depuração.
- [ ] **PowerDevil/idle**: com ON, a suspensão automática por inatividade fica bloqueada (dim/DPMS/bloqueio de tela também). Conferir `PolicyAgent.ActiveInhibitions` **após ~6 s** (debounce de ~5 s do `AddInhibition`); `HasInhibition(4)` deve virar `true`. Não usar `CanSuspend` como teste.
- [ ] **Tampa/suspensão manual**: com ON, fechar a tampa e a suspensão manual continuam suspendendo (o `sleep` não é inibido; os caminhos do PowerDevil são `Explicit=true`). Teste destrutivo; a máquina é notebook.
- [ ] **Cookie**: outra conexão consegue `UnInhibit` (sem ownership); derrubar o daemon libera a inibição (o PowerDevil observa a conexão). Teste de isolamento **não** se aplica ao KDE.
- [ ] **Queda do PowerDevil**: `systemctl --user restart plasma-powerdevil` (ou matar `org_kde_powerdevil`) com ON → estado `error` + `StateChanged`; ao voltar, re-adquire e volta a `on` após ~6 s, sem rajada de retries.
- [ ] **Estado `error`** (ex.: inibição bloqueada nas configurações do PowerDevil ou serviço ausente) mostra motivo no tooltip/`GetLastError()` e libera o `systemd-inhibit`.
- [ ] **Tema/fonte do Plasmoid**: superfície/texto/fonte acompanham o tema do Plasma (testar BreezeDark ↔ tema claro); cores de estado (menta/cinza/vermelho) permanecem fixas e legíveis.

## Notas ao implementador

- **Ordem dos hints**: `keep_below`, `skip_taskbar`, `skip_pager` e `stick()` **antes** de `show_all()`; reforce em `realize`/`map`. No Marco, `WindowTypeHint.DESKTOP` quebra clique/arrasto — não usar.
- **`Gtk.Switch` + drag**: conectar `state-set` e retornar `True` enquanto `dragged == True`; resetar a flag só no `button-release`. Sem isso o switch alterna ao soltar o mouse.
- **GTK3 não suporta `@font-face`** (verificado no Mint com GTK 3.24.41: `unknown @ rule`). Não tentar embutir fonte via CSS.
- **`systemd-inhibit`**: `--what=idle` (não `sleep`), `--mode=block`, `--who=DeskAwake`, `--why` descritivo; o filho deve rodar em grupo próprio e com `PR_SET_PDEATHSIG` (via `preexec_fn`) para nunca sobreviver ao daemon. O `CanSuspend` do logind **não** reflete inibidores; não usá-lo como teste de bloqueio.
- **Cookie**: só vale na conexão que o obteve — nunca abrir conexão nova para `UnInhibit`. No MATE **e no KDE/kwin** não há checagem de dono; não escrever teste universal de isolamento. No GSM o método é `Uninhibit` (i minúsculo), diferente de FDO/MATE.
- **Backend KDE** `[Kubuntu 26.04 / Plasma 6.6 — validado]`: `org.freedesktop.ScreenSaver.Inhibit` é traduzido pelo `kscreenlocker` em `PolicyAgent.AddInhibition(ChangeScreenSettings=4)`; **não** chamar o `PolicyAgent` para inibir (duplicaria cookies). O PowerDevil aplica o `AddInhibition` só após **~5 s** — o ON é otimista (cookie + filho vivo) e a verificação assíncrona (`GLib.timeout_add_seconds(6, ...)`) confirma em `ActiveInhibitions` com `who="deskawake"`/`why="DeskAwake active"` (fallback `HasInhibition(4)`; senão cookie + log). Queda do `org.kde.Solid.PowerManagement` ou do `org.freedesktop.ScreenSaver` com ON → `error` + `StateChanged`; retorno → descarta o cookie antigo, re-adquire e volta a `on` após ~6 s, **sem rajada de retries**. O filho do `systemd-inhibit` não é reiniciado nesse caso.
- **Fim de sessão** `[Kubuntu 26.04 / Plasma 6.6 — validado]`: tratar `org.freedesktop.DBus.Local.Disconnected` como logout/desligamento. Não fazer chamadas no barramento morto; encerrar o filho do `systemd-inhibit` (SIGTERM → 2 s → SIGKILL no grupo), `loop.quit()` e sair 0. `org.kde.Shutdown`/`plasma-login-session` são opcionais, nunca requisito.
- **Menu do Plasmoid** `[Kubuntu 26.04 / Plasma 6.6 — validado]`: `Ativar/Desativar` com rótulo dinâmico (`Desativar` quando `on`; `Ativar` quando `off`/`error`) + `Sair` (`SetActive(false)` → `Quit()`) + itens nativos do Plasma. `Sair` deve tratar o daemon já caído sem travar a UI (o `DBusServiceWatcher` já leva o estado visual para `off`). **Não** incluir `Tema ▸`/`Iniciar com o sistema` no Plasmoid — são exclusivos do menu GTK.
- **Tema do Plasmoid** `[Kubuntu 26.04 / Plasma 6.6 — validado]`: usar `Kirigami.Theme.backgroundColor`/`textColor`/`defaultFont` para superfície/texto/fonte; **não** fixar o grafite/texto claro no QML. As cores de estado são fixas (menta/cinza/vermelho) e o toggle é o único indicador.
- **Testes do KDE**: injetar debounce/verificação como constantes ou parâmetros sobrescrevíveis (padrão ~5 s/~6 s), restaurando no teardown/monkeypatch para não vazar estado entre testes; cobrir as três rotas rápidas (confirmação, falha → `error` + `StateChanged("error")`, cancelamento por `SetActive(false)`) e manter um `@pytest.mark.slow` opt-in para o ciclo real.
- **Tamanho do Plasmoid** (decisão 16): fixar `Layout.minimumWidth`, `Layout.preferredWidth` e `Layout.maximumWidth` em `124` e as três de altura em `42`; manter o conteúdo interno contido (`implicitWidth/Height`) e usar `elide` em textos curtos para não estourar em escalas fracionárias (125%/150%). A posição é do Plasma (`ItemGeometries-<W>x<H>` no `appletsrc`), não do `config.json`.
- **Indicador de progresso** (decisão 33): spinner de duas flechas circulares em cor neutra (sem âmbar). Na chamada em voo (`Toggle`/`SetActive`), animar e bloquear o toggle; na verificação KDE, manter `on` (menta) + spinner **sem** bloquear o clique — `SetActive(false)` cancela o timer pendente. Não adicionar estado de verificação ao D-Bus; o spinner é visual (timer/estado local na UI).
- **`ActiveInhibitions`**: é `a(ssssu)` = `(what, who, why, mode, flags)`; `flags & 3 == 3` indica ativa/permitida. Não confundir com `HasInhibition(4)`, que é global.
- **Backend MATE**: `org.mate.ScreenSaver.Inhibit` já cria o proxy GSM `IDLE=8`; confirmar com `IsInhibited(8)` e **não** adquirir GSM de novo. Se o proxy não confirmar, liberar o cookie MATE e cair para o GSM.
- **FDO no MATE**: `mate-screensaver` 1.26.2 não expõe `org.freedesktop.ScreenSaver`; o master expõe como nome “soft”. Não assumir que o FDO existe em qualquer MATE — sempre tentar primeiro e cair para o MATE.
- **`xdg-screensaver`**: não usar. No MATE ele só faz `SimulateUserActivity` a cada 50 s preso a um XID de janela; não inibe DPMS/lock de verdade e acopla o ciclo de vida à janela.
- **Tema `auto`**: ler `gtk-theme` e `gtk-application-prefer-dark-theme`; conectar `notify::gtk-theme-name`/`notify::gtk-application-prefer-dark-theme`; não alterar o `prefer-dark` global. MATE 1.26 não tem `color-scheme`.
- **Fonte**: usar a stack única com aspas e `sans-serif` no fim; Inter é opcional (`fonts-inter` 4.0+ds-1 no Mint; 4.1+ds-1 no Kubuntu), Ubuntu é a nativa do MATE, Noto Sans é o fallback real.
- **Plasmoid** `[Kubuntu 26.04 / Plasma 6.6 — validado]`: **não** existe dataengine `dbus` no Plasma 6 e **não** usar `Plasma5Support`/`gdbus`/polling. Usar o módulo nativo `org.kde.plasma.workspace.dbus` (`SessionBus.asyncCall`, `SignalWatcher`, `DBusServiceWatcher`); registrar os watchers **antes** de `GetState`/`GetLastError` no `Component.onCompleted` para não perder `StateChanged` inicial. Exige Plasma ≥ 6.4 (declare no `metadata.json`). Toggle só no clique rápido; arrasto nativo por press‑and‑hold (`AfterPressAndHold`).
- **Instalador**: detectar alvo por ferramenta (`kpackagetool6`), não por nome de distro; no Kubuntu `kpackagetool6` 2.0 existe e `--all` instala daemon+GTK+Plasmoid; no Mint `--all` degrada com aviso e deixa claro que daemon+GTK foram instalados; `--only-kde` falha se faltar; `uninstall.sh` tolera ausência. **Idempotência**: se o pacote já estiver registrado, usar `kpackagetool6 --upgrade` (ou remover/reinstalar) para `--all` não falhar na segunda execução. **`--install-deps`**: nunca usar `sudo`; imprimir os comandos `apt` separando obrigatórios de `fonts-inter` (opcional) e verificar ao final `python3`/`gi`/`dbus`/`systemd-inhibit`/`kpackagetool6`/`gdbus`.
- **Auto-start**: `status`/`off` usam `NameHasOwner` para não acordar o daemon sem necessidade.
- **Log**: corte em 256 KB com rotação para `daemon.log.1`; nunca logar credenciais (não há).
- **Docs**: README do usuário em pt-BR e inglês; spec/design internos em pt-BR.
- **Limite de validação**: o backend/UI MATE foi validado por leitura de ambiente; o **backend KDE foi validado** (D-Bus + fonte do PowerDevil/kscreenlocker), mas **a GUI do Plasmoid e o arrasto ficam na checklist manual**. A máquina Mint é desktop (sem tampa); a máquina Kubuntu é notebook (tampa/bateria), mas o teste destrutivo de tampa/suspensão é manual.

## Variações por distro

| Ponto | Kubuntu 26.04.1 / Plasma 6.6.7 (validado 19/11/2026) | Mint 22.3 MATE (validado 19/11/2026) |
|---|---|---|
| Inibidor de tela | `org.freedesktop.ScreenSaver.Inhibit` (dono `kwin_wayland`); o `kscreenlocker` o traduz em `PolicyAgent.AddInhibition(ChangeScreenSettings=4)`; sem `GetInhibitors`; confirmação em `ActiveInhibitions`/`HasInhibition(4)` após ~5 s. | `org.freedesktop.ScreenSaver` ausente no `mate-screensaver` 1.26.2; usar `org.mate.ScreenSaver` (fallback GSM). No master do MATE o FDO é adquirido como “soft”. |
| Suspensão | `--what=idle` apenas; a suspensão automática é do PowerDevil (`AutoSuspendIdleTimeoutSec=1800` no AC) e é bloqueada via `ChangeScreenSettings`→`InterruptSession`; tampa e suspensão manual continuam (`Explicit=true`). | `--what=idle` apenas; tampa e suspensão manual continuam funcionando. |
| Cookie | Sem validação de dono (outra conexão faz `UnInhibit`); a inibição morre com a conexão do daemon (PowerDevil observa o nome único). | Sem validação de dono; cookie morre com a conexão; teste condicional ao backend. |
| `xdg-screensaver` | Descartado (não é backend). | Descartado explicitamente (XID + poke a cada 50 s, não é inibição). |
| Tema | Plasmoid: superfície/texto/fonte via `Kirigami.Theme`; cores de estado fixas (menta/cinza/vermelho) + spinner neutro. | `gtk-theme` contém “dark” **ou** `gtk-application-prefer-dark-theme`; sinais `notify::*`; sem `color-scheme`. |
| Fonte | Noto Sans 10 é a fonte da UI; Inter/Cantarell ausentes; `fonts-inter` 4.1+ds-1 disponível. | Stack aditiva com `Ubuntu`; Inter/Cantarell não instaladas; `fonts-inter` 4.0+ds-1 disponível. |
| Instalador/KDE | `kpackagetool6` 2.0 presente; `--all` instala daemon+GTK+Plasmoid; `--only-kde` funciona. | `kpackagetool6` ausente nos repos; `--all` degrada, `--only-kde` falha, uninstall tolera. |
| Autostart | XDG + `.service`; Plasmoid adicionado manualmente; login não exercitado. | XDG presente; comportamento de login não exercitado. |
| EWMH/hints | N/A (Wayland); o Plasmoid vive na camada do desktop do Plasma. | Atoms `SKIP_TASKBAR`, `SKIP_PAGER`, `STICKY`, `BELOW`, `UTILITY`, `DESKTOP` presentes; comportamento de janela na checklist. |
| Compositor | `kwin_wayland` 6.6.7; Wayland; escala 1; eDP-1 1920×1200. | `compositing-manager=true`; selection owner de `_NET_WM_CM_S0` é o Marco; `Gdk.Screen.is_composited() == True`. |
| Caja/desktop | N/A (Plasma desktop). | `org.mate.background show-desktop-icons=true`; janela do Caja é `DESKTOP`, sticky e skip pager/taskbar. |
| Tampa | Notebook com tampa/bateria; comportamento validado por código (PowerDevil `Explicit=true`); teste destrutivo na checklist. | “Ainda suspende” consistente com `--what=idle`; não testável (desktop sem tampa). |
| Plasmoid | Transporte nativo `org.kde.plasma.workspace.dbus` (Plasma ≥ 6.4); backend validado; GUI na checklist. | Não aplicável. |
| Validação | Backend KDE validado por D-Bus + fonte do PowerDevil/kscreenlocker; GUI na checklist. | Backend/UI MATE validados; GUI na checklist manual. |

## Validação no Kubuntu 26.04.1 / Plasma 6.6.7 (evidências)

**Ambiente:** Ubuntu 26.04.1 “Resolute Raccoon” (`kubuntu-desktop` 1.496), kernel `7.0.0-43-generic`, **KDE Plasma 6.6.7** (`plasmashell`/`kwin` 6.6.7), sessão **Wayland** (`XDG_SESSION_TYPE=wayland`, `WAYLAND_DISPLAY=wayland-0`, `XDG_CURRENT_DESKTOP=KDE`, `KDE_SESSION_VERSION=6`); notebook (chassis 10, `BAT0`), eDP‑1 1920×1200, escala 1, painel inferior. Python 3.14.4; PyGObject 3.56.2; `pytest` ausente (`python3-pytest` 9.0.2 no apt); `shellcheck` ausente; `kpackagetool6` 2.0; `gdbus`/`dbus-run-session` presentes.

**D-Bus da sessão:**
- `org.freedesktop.ScreenSaver`: dono `kwin_wayland`; objeto `/org/freedesktop/ScreenSaver`; métodos `Lock`, `SimulateUserActivity`, `GetActive`, `GetActiveTime`, `GetSessionIdleTime`, `SetActive`, `Inhibit(s,s)→u`, `UnInhibit(u)`, `Throttle`, `UnThrottle`; interface adicional `org.kde.screensaver` (`configure`, sinal `AboutToLock`); **sem** `GetInhibitors`.
- `org.kde.Solid.PowerManagement`: dono `org_kde_powerdevil`; `/org/kde/Solid/PowerManagement` com `isLidPresent`, `isLidClosed`, `isActionSupported`, `scheduleWakeup` etc.; `/org/kde/Solid/PowerManagement/PolicyAgent` com `AddInhibition(u,s,s)→u`, `ReleaseInhibition(u)`, `HasInhibition(u)→b`, `SetInhibitionAllowed(s,s,b)`, `ListInhibitions` e propriedades `RequestedInhibitions`/`ActiveInhibitions` (`a(ssssu)`).
- `org.freedesktop.PowerManagement.Inhibit`: dono `org_kde_powerdevil`; `Inhibit(s,s)→u`, `UnInhibit(u)`, `HasInhibit()→b`.
- **Teste empírico**: `ScreenSaver.Inhibit("deskawake-probe-d","probe D")` → `HasInhibition(4)` virou `true` após **~5,3 s**; `HasInhibition(1)` também `true`; `ActiveInhibitions = [("idle","deskawake-probe-d","probe D","block",3)]`; `UnInhibit` → `HasInhibition(4)` volta a `false`. O `AddInhibition(4)` direto também ativa em ~4,8 s e implica `HasInhibition(1)`.
- **Cookie**: outra conexão consegue `UnInhibit` (sem ownership). A inibição desaparece quando a conexão que chamou `Inhibit` fecha (PowerDevil observa o nome único; as primeiras sondas com `gdbus` morreram em ~1 s e não ativaram).
- `systemd-inhibit --what=idle --mode=block --who=DeskAwake --why=probe sleep 3` aparece em `systemd-inhibit --list` e não deixa resíduo.
- `logind`: `IdleAction=ignore`, `IdleActionUSec=1800 s`, `HandleLidSwitch=suspend`.

**PowerDevil/kscreenlocker (código-fonte):**
- `kscreenlocker` (Plasma/6.6): `Interface::Inhibit` cria `PowerInhibitor`, que chama `PolicyAgent.AddInhibition(ChangeScreenSettings=4)`; `KSldApp::isInhibited()` inclui `PowerManagementInhibition` (`HasInhibition(4)`), então a inibição também impede o bloqueio automático de tela.
- `PowerDevil` (6.6/master): `PolicyAgent::addInhibitionWithExplicitDBusService` agenda a aplicação com `QTimer::singleShot(5000, ...)` (debounce de 5 s); `ChangeScreenSettings` implica `InterruptSession`; `SuspendSession::onIdleTimeout` checa `InterruptSession`; `DimDisplay`/`DPMS` exigem `ChangeScreenSettings`; `HandleButtonEvents::triggerAction` passa `Explicit=true` (tampa/botão/menu ignoram a política); `FdoConnector::Inhibit` mapeia para `InterruptSession`.
- `powerdevilrc` (AC): `DimDisplayIdleTimeoutSec=600`, `TurnOffDisplayIdleTimeoutSec=900`, `AutoSuspendIdleTimeoutSec=1800`, `PowerProfile=performance`.

**Plasma/QML:**
- `org.kde.plasma.workspace.dbus` presente (`plasma-workspace` 6.6.7): `SessionBus`/`SystemBus` (`asyncCall`), `SignalWatcher`, `DBusServiceWatcher`, tipos `DBus.uint32` etc. `SignalWatcher` existe desde o Plasma 6.4 (ausente em 6.2/6.3; presente em 6.4/6.5/6.6).
- `AppletsLayout`/`BasicAppletContainer` do desktop usam `AfterPressAndHold` (arrasto por pressionar e segurar) e `Locked` quando `Plasmoid.immutable`.
- `kpackagetool6 -i ./plasmoid` instala em `~/.local/share/plasma/plasmoids/org.local.deskawake/`.

**GTK/tema/fontes (para o GTK `--force`):**
- `org.gnome.desktop.interface`: `gtk-theme='Breeze'`, `color-scheme='prefer-dark'`, `font-name='Noto Sans 10'`; `~/.config/gtk-3.0/settings.ini` com `gtk-application-prefer-dark-theme=true`.
- `kreadconfig6 kdeglobals General ColorScheme` = `BreezeDark`.
- `fc-match Inter` → Noto Sans; `fc-match Cantarell` → Noto Sans; `fc-match Ubuntu` → Ubuntu; `fc-match "Noto Sans"` → Noto Sans; Inter/Cantarell não instaladas; `fonts-inter` 4.1+ds-1 disponível.

**Limitações desta validação:**
- Não foi criado protótipo GUI: tamanho/empilhamento do Plasmoid, tema, menu e arrasto ficam na checklist manual.
- Teste destrutivo de tampa/suspensão não executado; a conclusão vem do código do PowerDevil (`Explicit=true`) e do logind.
- `CanSuspend` não é teste válido de inibição.
- A GUI GTK não é usada no Kubuntu (Wayland); só `--force`/XWayland para depuração.

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

## Adendo de implementação — E2 (2026-11-20)

> Este adendo registra a leitura adotada na Phase 2 da E2 para pontos que a spec deixava abertos.
> **Não altera as decisões 1–33**; detalhes de implementação ficam no `design_e2.md` (versionado em `docs/implementation/`)
> e no `DELIVERY_MAP.md` §E2.5.

- **Confirmação no KDE (decisões 29–30):** a degradação para cookie + aviso em log só vale quando
  o mecanismo não existe (propriedade/método/interface indisponível). Se `ActiveInhibitions` ou
  `HasInhibition(4)` existem e indicam “não inibido”, a confirmação falha (`error` + `StateChanged`).
  `PolicyAgent` ausente do barramento continua sendo cookie (não é KDE).
- **Liveness (decisão 31):** observar os quatro nomes, mas reagir apenas aos relevantes ao backend
  ativo: o nome do backend; `org.gnome.SessionManager` quando o backend é o MATE (proxy GSM); e
  `org.kde.Solid.PowerManagement` quando o backend é o FDO (KDE). Queda relevante com `on` ⇒
  `error`; o retorno só tenta re-adquirir quando todos os nomes relevantes que caíram voltarem,
  com **uma** tentativa por vez, sem rajada. O filho do `systemd-inhibit` é preservado nesse
  caminho.
- **Queda do GSM (decisão 31):** se o backend ativo é o GSM, o estado público é `on` e
  `org.gnome.SessionManager` cai, o daemon encerra junto com a sessão (`exit 0`), parando o filho e
  **sem** tentar `Uninhibit`. Em `error`, não encerra; o `Local.Disconnected` cobre o logout.
- **`GetLastError`/`Toggle`/`StateChanged`:** `last_error` existe apenas em `error` e é limpo ao
  sair para `on`/`off`; `GetLastError()` devolve `""` fora de `error`. `Toggle` em `error` tenta
  ativar (coerente com o rótulo `Ativar` da UI). Uma falha repetida em `error` atualiza o motivo,
  mas não reemite `StateChanged("error")` porque o estado não mudou.
- **Fora do contrato público:** injeção de dependências na máquina de estados, papel de
  `debounce`/`verify_delay`, overrides de `core.daemon.main()` para testes, retenção do último
  backend após `release()` e `set_exit_on_disconnect(False)` são decisões de implementação; não
  alteram os estados, membros D-Bus nem o comportamento do produto.

## Referências

- `org.freedesktop.ScreenSaver` — D-Bus Interface Specification (freedesktop.org).
- `org.mate.ScreenSaver` — `mate-screensaver` 1.26.2, objeto `/org/mate/ScreenSaver`; código: `gs-listener-dbus.c` (proxy GSM `IDLE=8`, FIXME de ownership de cookie; FDO como nome “soft” no master) — https://github.com/mate-desktop/mate-screensaver
- `org.gnome.SessionManager` — `mate-session` 1.26.1; flags de inibição 1/2/4/8.
- `mate-power-manager` — `gpm-idle.c`/`gpm-session.c` (idle/DPMS consultam GSM `IsInhibited(8/4)`) — https://github.com/mate-desktop/mate-power-manager
- `systemd-inhibit(1)` — semântica de `--what` e `--mode=block`; logind.
- KDE — `kpackagetool6` 2.0, estrutura `metadata.json` (`KPackageStructure: "Plasma/Applet"`) + `contents/ui/main.qml`; `org.kde.plasma.workspace.dbus` (`SessionBus`, `SignalWatcher`, `DBusServiceWatcher`) — `plasma-workspace` 6.6.7; `SignalWatcher` desde o Plasma 6.4.
- PowerDevil — `PolicyAgent` (`AddInhibition`, `HasInhibition`, `ActiveInhibitions`; debounce de 5 s), `SuspendSession::onIdleTimeout`, `DimDisplay`/`DPMS` (`ChangeScreenSettings`), `HandleButtonEvents` (`Explicit=true`), `FdoConnector` — https://invent.kde.org/plasma/powerdevil
- kscreenlocker — `Interface::Inhibit`/`PowerInhibitor` (traduz para `PolicyAgent.AddInhibition(ChangeScreenSettings)`), `PowerManagementInhibition`/`KSldApp::isInhibited` — https://invent.kde.org/plasma/kscreenlocker (branch `Plasma/6.6`)
- Kubuntu 26.04.1 “Resolute Raccoon” — `kubuntu-desktop` 1.496; Plasma 6.6.7; Wayland.
- Linux Mint 22.3 “Zena” — `UBUNTU_CODENAME=noble`; pacotes MATE 1.26.x.
- Inter — SIL Open Font License 1.1 (apenas dependência opcional sugerida; `fonts-inter` 4.0+ds-1 no Mint, 4.1+ds-1 no Kubuntu).
