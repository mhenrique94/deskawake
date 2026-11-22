# DeskAwake

Um widget de desktop que mantém a tela acesa e o sistema acordado enquanto você precisa — sem janela convencional, sem barra de tarefas, sem `Alt+Tab`.

Funciona em **Linux Mint 22.3 MATE (X11)** e **Kubuntu 26.04 / KDE Plasma 6.6 (Wayland)**, com um núcleo Python compartilhado e duas interfaces: widget GTK3 no MATE e Plasmoid nativo no Plasma.

> Versão `0.1.0`, licença MIT. Documentação em inglês: [`README.en.md`](README.en.md).

## Sistemas suportados

- **Linux Mint 22.3 MATE/X11** — widget GTK3, backend `org.mate.ScreenSaver` e `systemd-inhibit --what=idle`.
- **Kubuntu 26.04 / KDE Plasma 6.6/Wayland** — Plasmoid nativo, backend `org.freedesktop.ScreenSaver` e `systemd-inhibit --what=idle`.
- Python ≥ 3.10; `python3-gi`, `python3-dbus`, `systemd` e `libglib2.0-bin` (que fornece `systemd-inhibit` e `gdbus`).

## O que ele faz e o que não faz

**Faz:**

- Impede o bloqueio/apagamento da tela e a suspensão **por inatividade** enquanto o estado é `on`.
- Vive na área de trabalho, atrás das janelas normais e arrastável; no Plasma, tamanho e posição são lembrados pelo próprio Plasma.
- Estado sempre inicia desligado; sair da UI libera os bloqueios imediatamente.
- Oferece uma interface única de controle (`deskawake`) para terminal, atalhos e diagnóstico.

**Não faz:**

- **Não** bloqueia o fechamento da tampa (`tampa`/`lid`) nem a suspensão manual (`Suspender` no menu do sistema ou `systemctl suspend`). Isso é intencional.
- **Não** substitui o bloqueio de tela configurado pelo sistema; ele apenas impede a inatividade.
- **Não** instala o Plasmoid automaticamente na área de trabalho: ele precisa ser adicionado em “Adicionar widgets”.

## Requisitos e `--install-deps`

O instalador verifica as dependências e nunca executa `apt` sozinho. Para ver os comandos e o status atual:

```bash
./install.sh --install-deps
```

Dependências obrigatórias de runtime:

```bash
apt install python3-gi python3-dbus systemd libglib2.0-bin
```

Para o Plasmoid no KDE:

```bash
apt install kpackagetool6
```

Opcional (fonte Inter):

```bash
apt install fonts-inter
```

`kpackagetool6` não existe no Linux Mint 22.3; nesse sistema o alvo KDE é indisponível e o `--all` degrada com um aviso explícito.

## Instalação

O instalador é **por usuário** e não requer privilégios administrativos. Ele grava somente em `${XDG_DATA_HOME:-~/.local/share}/deskawake`, `~/.local/bin`, `${XDG_DATA_HOME:-~/.local/share}/dbus-1/services`, `~/.config/autostart` e, no alvo KDE, em `${XDG_DATA_HOME:-~/.local/share}/plasma/plasmoids/org.local.deskawake`.

Sem flag, o desktop é detectado por `XDG_CURRENT_DESKTOP`:

```bash
./install.sh
./install.sh --only-mate
./install.sh --only-kde
./install.sh --all
```

- Sem flag: detecta MATE ou KDE automaticamente. `--only-mate` instala daemon+GTK; `--only-kde`, daemon+Plasmoid; `--all` instala tudo o que estiver disponível.

- `--all` no Linux Mint 22.3: instala daemon+GTK, imprime `KDE indisponível: kpackagetool6 ausente` e sai com sucesso deixando claro que daemon+GTK foram instalados.
- `--only-kde` sem `kpackagetool6`: falha com `alvo KDE indisponível: kpackagetool6 ausente` e não copia nada.
- Em sessão Wayland com o alvo GTK ativo, o instalador avisa que o widget GTK exige X11; no KDE a UI suportada é o Plasmoid.
- No Kubuntu, depois da instalação, abra “Adicionar widgets” e arraste o DeskAwake para a área de trabalho.
- Se `~/.local/bin` não estiver no `PATH`, o instalador avisa. Para adicionar ao Bash:
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```
- Reexecutar o instalador é idempotente. O upgrade **não** interrompe um daemon em execução; a versão nova entra no próximo login ou reinício do daemon. Para aplicá-la imediatamente, encerre o daemon e deixe o `.service` reativá-lo na próxima ação:
  ```bash
  gdbus call --session --dest org.local.DeskAwake --object-path /org/local/DeskAwake --method org.local.DeskAwake.Quit
  deskawake on
  ```

### Instalação via `.deb` (system-wide)

Para instalar para todos os usuários, baixe o pacote do GitHub Releases e use o `apt` (recomendado, porque resolve as dependências):

```bash
sudo apt install ./deskawake_0.1.0_all.deb
```

`sudo dpkg -i ./deskawake_0.1.0_all.deb` funciona como fallback, mas não resolve dependências; nesse caso rode `sudo apt install -f` em seguida.

O pacote instala o código em `/usr/lib/deskawake`, o comando em `/usr/bin/deskawake`, o `.service` do D-Bus, os autostarts em `/etc/xdg/autostart` e o Plasmoid em `/usr/share/plasma/plasmoids`. A configuração (`~/.config/deskawake`) e o estado (`~/.local/state/deskawake`) continuam por usuário e são preservados na remoção.

Para remover:

```bash
sudo apt remove deskawake
```

### Atualização

A atualização é manual: baixe o `.deb` da versão nova e instale por cima com `sudo apt install ./deskawake_<nova>_all.deb`. Não há auto-update nem repositório APT nesta versão. Como no `install.sh`, a versão anterior continua ativa até o próximo login ou até reiniciar o daemon.

### Integridade

O release publica o `.deb`, o código-fonte em `deskawake-0.1.0.tar.gz` e o `SHA256SUMS`. Baixe os três e confira no diretório dos downloads:

```bash
sha256sum -c SHA256SUMS
```

O HTTPS e o SHA-256 são a integridade desta rodada; não há assinatura GPG nem repositório APT.

### Coexistência com a instalação per-user

As duas instalações não devem coexistir. Rode `./uninstall.sh` antes de instalar o `.deb`.

- Com o pacote system-wide presente, `./install.sh` recusa e pede `apt remove deskawake`.
- `./uninstall.sh` apenas avisa que o pacote não é removido por ele; a remoção system-wide é feita pelo gerenciador de pacotes.
- `./verify.sh` aceita as duas instalações e avisa se ambas existirem.

## Uso

CLI:

```bash
deskawake on       # liga; imprime "on"
deskawake off      # desliga; imprime "off"
deskawake toggle   # alterna
deskawake status   # 0 = on, 1 = off/error, 3 = daemon inacessível
deskawake daemon   # sobe o daemon em primeiro plano
deskawake ui       # abre o widget GTK (recusa Wayland sem --force)
```

No widget GTK do MATE, clique no toggle para ligar/desligar. O menu oferece `Ativar/Desativar`, `Tema`, `Iniciar com o sistema`, `Sobre o DeskAwake…` e `Sair` (kill switch). O item `Sobre o DeskAwake…` mostra autor, site e licença MIT.

No Plasma, use o toggle do Plasmoid ou o menu hamburguer com `Ativar/Desativar` e `Sair`. O tamanho e a posição são administrados pelo Plasma.

## Diagnóstico

```bash
./verify.sh
deskawake status
```

O `verify.sh` imprime uma linha `[ok]`/`[falha]` por checagem e termina com `verify: OK` ou `verify: FALHOU`. Ele sempre termina com o DeskAwake **OFF**, mesmo em falha.

Outros recursos:

- `GetLastError()` no D-Bus devolve o motivo do último erro.
- `~/.local/state/deskawake/daemon.log` é o log do daemon, com rotação para `daemon.log.1` em 256 KB.
- `systemd-inhibit --list` mostra a inibição `DeskAwake` enquanto o estado é `on`.
- No MATE, `GetInhibitors` do `org.mate.ScreenSaver` lista a aplicação `deskawake`; se existir, `mate-screensaver-command -q` complementa o diagnóstico.
- No KDE, `PolicyAgent.ActiveInhibitions` lista `deskawake`/`DeskAwake active` após o debounce de ~5 s; `HasInhibition(4)` confirma o bloqueio durante o ON.

## Limitações

- **KDE:** o PowerDevil aplica `AddInhibition(4)` após ~5 s (debounce). Por isso o ON é otimista e a confirmação assíncrona ocorre em ~6 s; o `verify.sh` espera até 8 s.
- **Tampa e suspensão manual:** continuam funcionando com o estado `on`. Fechar a tampa ainda suspende o notebook; `systemctl suspend` e o menu do sistema também. Não use o DeskAwake para manter um notebook fechado ligado.
- **Plasmoid:** a adição à área de trabalho é manual, em “Adicionar widgets”; o `install.sh` apenas instala o pacote.
- **`kpackagetool6`:** ausente no Mint 22.3, então o alvo KDE é indisponível nessa distro.
- **GTK no Wayland:** o widget GTK é bloqueado em Wayland; `--force` (ou `DESKAWAKE_FORCE_UI=1`) é apenas para depuração.
- **`Configurar` do Plasmoid:** abre as configurações nativas do Plasma, mas sem categorias próprias.
- **Upgrade:** o `install.sh` não interrompe o daemon em execução; a versão anterior continua ativa até o próximo login/reinício. O mesmo vale para a atualização via `.deb`.
- **Remoção com daemon ativo:** após `sudo apt remove deskawake`, um daemon já em execução continua até o logout, porque o pacote não mata processos de usuário. Saia e entre na sessão para encerrá-lo.
- **Autostart system-wide:** para desativar em um usuário, crie `~/.config/autostart/deskawake-*.desktop` (por exemplo, `deskawake-daemon.desktop` e `deskawake-widget.desktop`) com `Hidden=true`.
- **Plasmoid após remover:** o widget some no próximo login, quando o Plasma reescaneia os pacotes instalados.
- **`verify.sh`:** sempre termina OFF; não deixe o script como forma de ativar o DeskAwake.
- **MATE — “Mostrar área de trabalho”:** o Marco (Ctrl+Alt+D) pode ocultar o widget; ele volta ao restaurar. A limitação é conhecida e não trocamos o tipo de janela para evitar quebrar clique/arrasto.
- **MATE — tema `auto`:** resolve o tema pelo nome (`*Dark*`), porque `gtk-application-prefer-dark-theme` não existe em `org.mate.interface` no Mint 22.3.
- **MATE — estado `error`:** queda de backend preserva o filho do `systemd-inhibit` e libera o inibidor de tela; falha de ativação/verificação libera tudo.
- **MATE — `IsInhibited(8)`:** não existe no `mate-screensaver` 1.26.2; o diagnóstico usa `GetInhibitors` e, quando disponível, `mate-screensaver-command -q`.
- **Idle no MATE:** o `idle-delay` é lido no login; testar um intervalo curto exige uma sessão nova. O `lock-enabled` é destrutivo/opcional.
- **`CanSuspend`:** não reflete os inibidores do DeskAwake e não é usado como teste.
- **Caminhos com espaços:** são suportados e citados nos arquivos gerados; caminhos com aspas ou quebras de linha não são suportados.
- **Ambiente:** `HOME` e `XDG_DATA_HOME` precisam ser caminhos absolutos; valores vazios ou relativos são rejeitados com código 2, sem alterar arquivos.
- **Pendências manuais:** logout, desconexão de monitor externo e bloqueio de tela ainda precisam ser exercitados manualmente.

## Desenvolvimento e testes

Dependência de desenvolvimento (não instalada pelo `install.sh`):

```bash
sudo apt install python3-pytest
```

Testes unitários:

```bash
python3 -m pytest
```

Testes de integração em uma sessão D-Bus privada:

```bash
dbus-run-session -- python3 -m pytest
```

O teste opt-in de ciclo real (debounce de ~5–6 s) não roda por padrão:

```bash
python3 -m pytest tests/integration -m slow
```

Sintaxe dos scripts e lint opcional:

```bash
bash -n install.sh uninstall.sh verify.sh
shellcheck install.sh uninstall.sh verify.sh    # quando disponível
```

## Checklist manual — Linux Mint 22.3 MATE/X11

> A UI GTK foi validada na máquina Mint; esta checklist cobre a instalação, a desinstalação e os itens manuais restantes.

- [ ] Widget abre no canto superior direito, 24 px de margem, sem decoração.
- [ ] Não aparece em `Alt+Tab`, na barra de tarefas nem no pager; aparece em todos os workspaces. Verificar explicitamente `keep_below`, `skip_taskbar`, `skip_pager` e `stick()` (criar um segundo workspace: a máquina de validação tem apenas 1).
- [ ] Fica atrás de janelas normais. **“Mostrar área de trabalho” (Ctrl+Alt+D):** o widget é ocultado e volta ao restaurar; a tentativa de observar `_NET_SHOWING_DESKTOP` e reexibir uma vez foi descartada (o Marco ignora deiconify e `present()` restaura todas as janelas); se houver flicker ou o arrasto quebrar, registrar a limitação.
- [ ] Arrastar funciona a partir de qualquer ponto, inclusive sobre o toggle; arrastar > 5 px não alterna.
- [ ] Clique no toggle alterna; clique fora não altera.
- [ ] Durante `Toggle`/`SetActive`, o spinner de duas flechas aparece e o toggle fica bloqueado até a resposta; sem âmbar.
- [ ] Com o compositor do Marco desligado, a superfície fica sólida e legível; com o compositor ligado, a translucidez aparece.
- [ ] Posição sobrevive a logout; desconectar monitor externo faz o widget voltar ao padrão.
- [ ] Menu: `Ativar/Desativar`, `Tema ▸`, `Iniciar com o sistema`, `Sobre o DeskAwake…`, `Sair`; o `Sobre` mostra autor, site e MIT, sem símbolo de copyright nem CNPJ.
- [ ] `Sair` com estado ON libera imediatamente (`systemd-inhibit --list` sem `deskawake`; `GetInhibitors` vazio; se `mate-screensaver-command` existir, `-q` sem `deskawake`). `IsInhibited(8)` não é usado (ausente no mate-screensaver 1.26.2).
- [ ] `kill -9` no daemon não deixa `systemd-inhibit` órfão nem tela presa.
- [ ] Estando o `mate-screensaver` com idle/lock habilitados, ON impede blanking/bloqueio; após OFF, o comportamento volta. (Nesta máquina idle/lock estão desabilitados; habilitar temporariamente.) O `idle-delay` de `org.mate.session` é lido no login; para testar 1 min, abrir uma sessão nova. O `lock-enabled` é destrutivo/opcional.
- [ ] Suspensão manual (`systemctl suspend`/menu) funciona com ON. (Teste destrutivo; opcional.)
- [ ] Fechar a tampa suspende com ON. (Requer notebook; esta máquina é desktop, sem tampa.)
- [ ] Alternar `Mint-Y` ↔ `Mint-Y-Dark` atualiza o tema do widget sem reiniciar.
- [ ] Com Inter ausente, o widget usa Ubuntu/Noto Sans sem erro de `@font-face`.
- [ ] O estado `error` por **queda de backend** (ex.: matar o `mate-screensaver`) mostra tooltip/`GetLastError()` e **preserva** o filho do `systemd-inhibit` (o inibidor MATE é liberado). Falha de **ativação/verificação** vai para `error` liberando tudo.
- [ ] Pendências não executadas em 21/11/2026: logout, desconexão de monitor externo e bloqueio de tela; registrar no PR/README.

## Checklist manual — Kubuntu 26.04 / Plasma 6.6 Wayland

- [ ] `kpackagetool6 -t Plasma/Applet -i ./plasmoid` instala em `~/.local/share/plasma/plasmoids/org.local.deskawake/`; `--upgrade` atualiza. Reexecutar `./install.sh --all` não falha (idempotente); `--install-deps` imprime os comandos `apt` (obrigatórios × `fonts-inter` opcional) e não executa comandos administrativos.
- [ ] Plasmoid adicionado à área de trabalho mostra o tamanho inicial preferido (184×48); o widget explorer mostra o `preview.png`; o widget é redimensionável de 168×44 a 300×84 pelos handles do Plasma.
- [ ] Arrasto: pressionar e segurar move o widget (comportamento nativo do Plasma); clique rápido no toggle alterna e **não** move; clique no hamburguer abre o menu e não inicia arrasto; o restante da pílula continua arrastável. Se não arrastar, conferir “Widgets Travados” no menu da área de trabalho.
- [ ] Toggle reflete `on/off/error` em tempo real (transporte nativo, sem polling); remover o Plasmoid não desliga o estado de outros clientes.
- [ ] Menu: hamburguer e clique direito compartilham as mesmas ações — `Ativar/Desativar` (rótulo dinâmico), `Sair` (kill switch) e itens nativos do Plasma; durante `callPending`, `Ativar/Desativar` e `Sair` ficam desabilitados e configurar/remover continuam habilitados. `Sair` com ON libera imediatamente (`ActiveInhibitions` sem `deskawake`, `systemd-inhibit --list` sem `deskawake`).
- [ ] Spinner de duas flechas na chamada em voo (toggle bloqueado) e durante a verificação de ~6 s (toggle ainda `on`, clique aceito); desligar antes dos 6 s cancela a verificação sem `error`; falha após ~6 s vira `error` + tooltip.
- [ ] `deskawake ui` recusa Wayland com mensagem; `--force` abre para depuração.
- [ ] **PowerDevil/idle**: com ON, a suspensão automática por inatividade fica bloqueada (dim/DPMS/bloqueio de tela também). Conferir `PolicyAgent.ActiveInhibitions` **após ~6 s** (debounce de ~5 s do `AddInhibition`); `HasInhibition(4)` deve virar `true`. Não usar `CanSuspend` como teste.
- [ ] **Tampa/suspensão manual**: com ON, fechar a tampa e a suspensão manual continuam suspendendo (o `sleep` não é inibido; os caminhos do PowerDevil são `Explicit=true`). Teste destrutivo; a máquina é notebook.
- [ ] **Cookie**: outra conexão consegue `UnInhibit` (sem ownership); derrubar o daemon libera a inibição (o PowerDevil observa a conexão). Teste de isolamento **não** se aplica ao KDE.
- [ ] **Queda do PowerDevil**: `systemctl --user restart plasma-powerdevil` (ou matar `org_kde_powerdevil`) com ON → estado `error` + `StateChanged`; ao voltar, re-adquire e volta a `on` após ~6 s, sem rajada de retries.
- [ ] **Estado `error`** por queda de backend (ex.: PowerDevil/`org.freedesktop.ScreenSaver` ausente) mostra motivo no tooltip/`GetLastError()` e **preserva** o filho do `systemd-inhibit`; falha de ativação/verificação vai para `error` liberando tudo.
- [ ] **Tema/fonte do Plasmoid**: no BreezeDark e em tema claro, o chip acompanha o tom do wallpaper (escuro sobre fundo escuro, claro sobre fundo claro); tinta, logo, borda e spinner acompanham; as cores de estado (menta/cinza/vermelho) permanecem fixas e legíveis.
- [ ] **Chip adaptativo**: trocar o wallpaper ou mover/redimensionar o widget reamostra a região; fundo ambíguo (cinza médio) não pisca; com wallpaper de vídeo/slideshow sem sinal observável, a variante permanece até o próximo evento; sem objeto de wallpaper, cai no tema do Plasma.

## Desinstalação

```bash
./uninstall.sh
./uninstall.sh --purge
```

O desinstalador encerra o daemon (`Quit()` e, se necessário, fallback por PID), fecha a UI GTK, remove o Plasmoid, o launcher, o `.service`, os autostarts, o código e o log/estado. Ele é idempotente, tolera `kpackagetool6` ausente e nunca remove `~/.config` sem `--purge`.

## Créditos e licença

Desenvolvido por **Marcelo Silva · Maniva Software** — [https://manivasoftware.com.br](https://manivasoftware.com.br).

Versão `0.1.0`. Licença MIT.

Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79

A especificação de desenvolvimento está em [`docs/implementation/spec.md`](docs/implementation/spec.md).
