# DeskAwake

Um widget de desktop que mantém a tela acesa e o sistema acordado enquanto você precisa — sem janela convencional, sem barra de tarefas, sem `Alt+Tab`.

Funciona em **Linux Mint 22.3 MATE (X11)** e **Kubuntu 26.04 / KDE Plasma 6 (Wayland)**, com um núcleo Python compartilhado e duas interfaces: widget GTK3 no MATE e Plasmoid nativo no Plasma.

> **Status:** especificação aprovada e hidratada para **Linux Mint 22.3 MATE** e **Kubuntu 26.04 / Plasma 6.6** em 19/11/2026; implementação em andamento (o E5 do Plasmoid já foi repaginado).
> A especificação completa está em [`docs/implementation/spec.md`](docs/implementation/spec.md). O backend/UI MATE foi validado na máquina Mint; o backend KDE foi validado no Kubuntu 26.04.1 / Plasma 6.6.7 (Wayland). A GUI do Plasmoid e os testes destrutivos de tampa/suspensão ficam na checklist manual.

## O que ele faz

- Impede o bloqueio/apagamento da tela e a suspensão **por inatividade**; suspensão manual e fechamento da tampa continuam funcionando.
- Vive na área de trabalho, atrás das janelas normais e arrastável; no Plasma, tamanho e posição são lembrados pelo próprio Plasma.
- No Plasma 6, o widget é redimensionável (168×44 a 300×84), tem menu hamburguer e o chip acompanha o tom do papel de parede.
- Estado sempre inicia desligado; sair do widget libera os bloqueios imediatamente.
- Interface única de controle (`deskawake`) para terminal, atalhos e diagnóstico.

## Aviso

Fechar a tampa do notebook **ainda suspende** o sistema, assim como a suspensão manual (`Suspender` no menu do sistema ou `systemctl suspend`) — isso é intencional. Não use o DeskAwake para manter um notebook fechado ligado.

---

# DeskAwake (English)

A desktop widget that keeps your screen on and your system awake while you need it — no conventional window, no taskbar entry, no `Alt+Tab`.

Runs on **Linux Mint 22.3 MATE (X11)** and **Kubuntu 26.04 / KDE Plasma 6 (Wayland)**, with a shared Python core and two interfaces: a GTK3 widget on MATE and a native Plasma widget on KDE.

> **Status:** specification approved and hydrated for **Linux Mint 22.3 MATE** and **Kubuntu 26.04 / Plasma 6.6** on 2026-11-19; implementation in progress (the Plasmoid E5 has been redesigned).
> The full specification lives in [`docs/implementation/spec.md`](docs/implementation/spec.md) (Brazilian Portuguese). The MATE backend/UI was validated on the Mint machine; the KDE backend was validated on Kubuntu 26.04.1 / Plasma 6.6.7 (Wayland). The Plasmoid GUI and the destructive lid/suspend checks remain in the manual checklist.

## What it does

- Prevents screen lock/blanking and **idle** suspension; manual suspend and closing the lid keep working.
- Lives on the desktop, behind normal windows and draggable; on Plasma, size and position are remembered by Plasma itself.
- On Plasma 6, the widget is resizable (168×44 to 300×84), has a hamburger menu and its chip follows the wallpaper tone.
- Always starts disabled; quitting the widget releases the locks immediately.
- A single control interface (`deskawake`) for terminal use, shortcuts and diagnostics.

## Warning

Closing the laptop lid **still suspends** the system, as does manual suspend (`Suspend` in the system menu or `systemctl suspend`) — this is intentional. Do not use DeskAwake to keep a closed laptop running.

## License

MIT
