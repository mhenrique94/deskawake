# Design: E8 — Empacotamento e Distribuição (placeholder)

**Feature:** DeskAwake — E8 | **Data:** 2026-11-21 | **Status:** Placeholder — canal decidido; design
completo após a E7
**Referências:** [`spec.md`](spec.md) (decisões 34–38; “Meta”), [`DELIVERY_MAP.md`](DELIVERY_MAP.md)
§E8, [`design_e7.md`](design_e7.md) (layout per-user e instalador), [`design_e6.md`](design_e6.md)
(versão `0.1.0`).

> **Escopo deste documento:** registrar a decisão de canal e os pontos que serão especificados
> depois da E7. **Não** há implementação nesta rodada. O layout system-wide do `.deb` depende do
> layout per-user que a E7 vai congelar; especificar agora seria adivinhação.

---

## 1. Contexto

A E7 entrega instalação per-user, sem `sudo`, a partir do repositório (`./install.sh`). Para o
usuário final de Mint/Kubuntu, o canal natural é um pacote Debian/Ubuntu; para desenvolvedores e
usuários sem privilégios, o `install.sh` continua válido. A E8 fecha essa lacuna sem mudar o núcleo
nem as UIs.

## 2. Decisão de canal (confirmada em 2026-11-21)

| # | Tema | Decisão |
|---|---|---|
| 1 | Canal principal | **GitHub Releases + `.deb`** (CI gera o pacote, o tarball e os checksums) |
| 2 | Instalador per-user | **`install.sh` continua** como alternativa sem `sudo`; não é substituído pelo `.deb` |
| 3 | Versão | **0.1.0** (fonte `core.__version__`, E6); o primeiro release público usa esse valor |
| 4 | Fora de escopo | **AUR**, **Flatpak**, **AppImage** e **Snap** nesta rodada |
| 5 | Layout | O `.deb` instala **system-wide** (`/usr/lib/deskawake`, `/usr/bin/deskawake`, `/usr/share/...`); config/autostart continuam por usuário |
| 6 | CI | GitHub Actions em `ubuntu-latest`; build com `dpkg-deb` (sem debhelper/fpm) |
| 7 | Assinatura | Sem assinatura GPG do `.deb` nesta rodada; checksums SHA-256 no release |
| 8 | Spec | A decisão “sem empacotamento de distro” da spec será emendada na E8 |

**Por que não Flatpak/AppImage:** o produto depende de `systemd-inhibit`, do barramento de sessão e
do backend de tela (MATE/kscreenlocker/PowerDevil); um sandbox teria de expor tudo isso e mudaria o
comportamento validado. AUR não tem público-alvo entre Mint/Kubuntu. Um `.deb` nativo preserva o
comportamento e a instalação system-wide que usuários Debian esperam.

## 3. Pontos a especificar depois da E7

| Tema | O que falta decidir |
|---|---|
| Nome do pacote | `deskawake` (provável) e conflito com o wrapper per-user |
| Maintainer | Nome + e-mail no `control` (o e-mail ainda não foi fornecido; usar o site/CNPJ como referência até a decisão) |
| Dependências | `python3-gi`, `python3-dbus`, `systemd`, `libglib2.0-bin`; `kpackagetool6` como `Recommends` ou dependência do pacote KDE |
| Paths | Código em `/usr/lib/deskawake`, CLI em `/usr/bin/deskawake`, `.service` em `/usr/share/dbus-1/services`, autostart em `/etc/xdg/autostart`, Plasmoid em `/usr/share/plasma/plasmoids` |
| `@EXEC@` | Como o `.service`/autostart system-wide aponta para `/usr/bin/deskawake` sem conflitar com o wrapper per-user |
| `postinst`/`prerm` | Nada além de `update-desktop-database`/`glib-compile-schemas` se necessário; não iniciar daemon no install |
| Conflito com install.sh | Detectar instalação per-user e avisar/recusar; `uninstall.sh` não remove o `.deb` |
| Plasmoid system-wide | Incluir no `.deb` ou manter `kpackagetool6` no pós-instalação? |
| CI | Workflow de tag `v*`, build reprodutível, anexos do release e checksums |
| Teste do pacote | Instalação em container `ubuntu:24.04`/`26.04`, `dpkg -i`, `deskawake status`, remoção |
| Update | Sem auto-update; o usuário baixa o próximo `.deb` (documentar) |

## 4. Critérios para iniciar a E8

- [ ] E7 mergeada e layout per-user congelado.
- [ ] E6 mergeada com `core.__version__` e About.
- [ ] Destino do e-mail do maintainer definido.
- [ ] Workflow de CI e nomes de artefatos aprovados.

## 5. Fora de escopo até segunda ordem

- AUR, Flatpak, AppImage, Snap.
- Repositório APT/PPA próprio e assinatura de pacote.
- Auto-update embutido.
- Pacote para outras distros (Fedora/RHEL, Arch).
- Mudanças de código no núcleo ou nas UIs.
