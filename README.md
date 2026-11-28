# DeskAwake

Mantém a tela acesa e o sistema acordado enquanto você precisa — sem janela convencional, sem barra de tarefas, sem `Alt+Tab`.

Funciona em **Linux Mint 22.3 MATE (X11)** e **Kubuntu 26.04 / KDE Plasma 6.6 (Wayland)**: widget GTK3 no MATE e Plasmoid nativo no Plasma.

> Versão `0.1.0`, licença MIT. English: [`README.en.md`](README.en.md).

## O que ele faz

- Impede o bloqueio/apagamento da tela e a suspensão **por inatividade** enquanto está ligado.
- Fica na área de trabalho, atrás das janelas e arrastável; no Plasma, tamanho e posição são lembrados pelo próprio Plasma.
- Sempre inicia desligado; `Sair` libera os bloqueios imediatamente.
- Oferece a CLI `deskawake` para terminal, atalhos e diagnóstico.

## O que ele não faz

- **Não** bloqueia o fechamento da tampa nem a suspensão manual (`systemctl suspend` ou o menu do sistema).
- **Não** substitui o bloqueio de tela do sistema; ele só evita a inatividade.
- **Não** adiciona o Plasmoid automaticamente: use “Adicionar widgets”.

## Instalação

### Via `.deb` (recomendada)

Baixe o pacote em [Releases](https://github.com/mhenrique94/deskawake/releases/latest) e instale:

```bash
sudo apt install ./deskawake_0.1.0_all.deb
```

`sudo dpkg -i ./deskawake_0.1.0_all.deb` funciona como fallback, mas não resolve dependências; rode `sudo apt install -f` depois.

O pacote instala para todos os usuários em `/usr/lib/deskawake` e `/usr/bin/deskawake`. A configuração (`~/.config/deskawake`) e o estado (`~/.local/state/deskawake`) continuam por usuário e são preservados na remoção.

### Por usuário (sem `sudo`)

```bash
./install.sh
./install.sh --only-mate
./install.sh --only-kde
./install.sh --all
```

- Sem flag, o desktop é detectado automaticamente. `--only-mate` instala daemon + widget GTK; `--only-kde`, daemon + Plasmoid; `--all` instala o que estiver disponível.
- Para ver as dependências e os comandos de instalação: `./install.sh --install-deps`.
- Se `~/.local/bin` não estiver no `PATH`, adicione ao Bash:

  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```

- No Kubuntu, depois de instalar, adicione o DeskAwake em “Adicionar widgets”.
- `kpackagetool6` não existe no Linux Mint 22.3; nesse sistema o alvo KDE fica indisponível.

### Coexistência

As duas instalações não devem coexistir. Rode `./uninstall.sh` antes de instalar o `.deb`.

- Com o pacote system-wide presente, `./install.sh` recusa e pede `apt remove deskawake`.
- `./uninstall.sh` apenas avisa que o pacote não é removido por ele.
- `./verify.sh` aceita as duas instalações e avisa se ambas existirem.

### Integridade

Cada release publica o `.deb`, o código-fonte `deskawake-0.1.0.tar.gz` e o `SHA256SUMS`. Baixe os três e confira no diretório dos downloads:

```bash
sha256sum -c SHA256SUMS
```

O HTTPS e o SHA-256 garantem a integridade; não há assinatura GPG nem repositório APT.

## Uso

```bash
deskawake on       # liga; imprime "on"
deskawake off      # desliga; imprime "off"
deskawake toggle   # alterna
deskawake status   # 0 = on, 1 = off/error, 3 = daemon inacessível
deskawake ui       # abre o widget GTK (recusa Wayland sem --force)
```

No MATE, clique no toggle do widget. O menu oferece `Ativar/Desativar`, `Tema`, `Iniciar com o sistema`, `Sobre o DeskAwake…` e `Sair`.

No Plasma, use o toggle do Plasmoid ou o menu hamburguer com `Ativar/Desativar` e `Sair`.

## Atualização

A atualização é manual: baixe o `.deb` da versão nova e instale por cima com `sudo apt install ./deskawake_<nova>_all.deb`. Não há auto-update nem repositório APT nesta versão. A versão anterior continua ativa até o próximo login ou até reiniciar o daemon.

## Remoção

System-wide:

```bash
sudo apt remove deskawake
```

Por usuário:

```bash
./uninstall.sh
./uninstall.sh --purge
```

`--purge` também remove `~/.config/deskawake`. Sem ele, configuração e estado são preservados.

## Diagnóstico

```bash
deskawake status
./verify.sh
systemd-inhibit --list
```

- `./verify.sh` imprime uma linha `[ok]`/`[falha]` por checagem e termina sempre com o DeskAwake **OFF**.
- `systemd-inhibit --list` mostra a inibição `DeskAwake` enquanto o estado é `on`.
- O log fica em `~/.local/state/deskawake/daemon.log`, com rotação para `daemon.log.1` em 256 KB.

## Limitações

- **Tampa e suspensão manual:** continuam funcionando com o DeskAwake ligado. Fechar a tampa ainda suspende o notebook; `systemctl suspend` e o menu do sistema também.
- **Plasmoid:** a adição à área de trabalho é manual, em “Adicionar widgets”. Após remover o pacote, ele some no próximo login.
- **`kpackagetool6`:** ausente no Mint 22.3, então o alvo KDE é indisponível nessa distro.
- **GTK no Wayland:** o widget GTK é bloqueado em Wayland; `--force` é apenas para depuração.
- **`Configurar` do Plasmoid:** abre as configurações nativas do Plasma, sem categorias próprias.
- **Atualização:** a versão anterior continua ativa até o próximo login ou reinício do daemon.
- **Remoção com daemon ativo:** após `sudo apt remove deskawake`, um daemon em execução continua até o logout. Saia e entre na sessão para encerrá-lo.
- **Autostart system-wide:** para desativar em um usuário, crie `~/.config/autostart/deskawake-*.desktop` com `Hidden=true`.
- **MATE — “Mostrar área de trabalho”:** o Marco pode ocultar o widget; ele volta ao restaurar.

## Créditos e licença

Desenvolvido por **Marcelo Silva · Maniva Software** — [https://manivasoftware.com.br](https://manivasoftware.com.br).

Versão `0.1.0`. Licença MIT.

Marcelo Silva, MANIVA SOFTWARE E TECNOLOGIA LTDA - CNPJ 66.739.634/0001-79
