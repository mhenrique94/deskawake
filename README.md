# DeskAwake

Um widget de desktop que mantém a tela acesa e o sistema acordado enquanto você precisa — sem janela convencional, sem barra de tarefas, sem `Alt+Tab`.

Funciona em **Linux Mint 22.3 MATE (X11)** e **Kubuntu 26.04 / KDE Plasma 6 (Wayland)**, com um núcleo Python compartilhado e duas interfaces: widget GTK3 no MATE e Plasmoid nativo no Plasma.

> **Status:** especificação aprovada, implementação ainda não iniciada.
> A especificação completa está em [`spec.md`](spec.md).

## O que ele faz

- Impede o bloqueio/apagamento da tela e a suspensão por inatividade (não impede a suspensão ao fechar a tampa).
- Vive na área de trabalho, atrás das janelas normais, arrastável e com posição lembrada entre sessões.
- Estado sempre inicia desligado; sair do widget libera os bloqueios imediatamente.
- Interface única de controle (`deskawake`) para terminal, atalhos e diagnóstico.

## Aviso

Fechar a tampa do notebook **ainda suspende** o sistema — isso é intencional. Não use o DeskAwake para manter um notebook fechado ligado.

---

# DeskAwake (English)

A desktop widget that keeps your screen on and your system awake while you need it — no conventional window, no taskbar entry, no `Alt+Tab`.

Runs on **Linux Mint 22.3 MATE (X11)** and **Kubuntu 26.04 / KDE Plasma 6 (Wayland)**, with a shared Python core and two interfaces: a GTK3 widget on MATE and a native Plasma widget on KDE.

> **Status:** specification approved, implementation not started yet.
> The full specification lives in [`spec.md`](spec.md) (Brazilian Portuguese).

## What it does

- Prevents screen lock/blanking and idle suspension (closing the lid still suspends).
- Lives on the desktop, behind normal windows, draggable, with its position remembered across sessions.
- Always starts disabled; quitting the widget releases the locks immediately.
- A single control interface (`deskawake`) for terminal use, shortcuts and diagnostics.

## Warning

Closing the laptop lid **still suspends** the system — this is intentional. Do not use DeskAwake to keep a closed laptop running.

## License

MIT
