from __future__ import annotations

import os
from pathlib import Path

import dbus
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

from core.config import (
    CONFIG_PATH,
    PILL_HEIGHT,
    PILL_WIDTH,
    VALID_THEMES,
    default_position,
    load_config,
    save_config,
    validate_position,
)
from core.daemon import DBUS_NAME, INTERFACE, OBJECT_PATH
from ui_gtk.theme import (
    BOX_SPACING,
    NAME_SLOT_WIDTH,
    SIDE_MARGIN,
    SPINNER_ANGLES,
    SPINNER_FRAME_COUNT,
    SPINNER_INTERVAL_MS,
    SYMBOL_SIZE,
    TOGGLE_HEIGHT,
    TOGGLE_WIDTH,
    build_css,
    icon_color,
    resolve_variant,
    spinner_frame,
    svg_with_color,
)

ROOT = Path(__file__).resolve().parent.parent
ASSETS_PATH = ROOT / "assets"
AUTOSTART_PATH = Path("~/.config/autostart/deskawake-widget.desktop").expanduser()
TEMPLATE_PATH = ROOT / "data" / "deskawake-widget.desktop"

PUBLIC_STATES = frozenset({"on", "off", "error"})
DRAG_THRESHOLD = 5
ERROR_FALLBACK = "DeskAwake: erro sem detalhes"
STATE_CLASSES = ("state-on", "state-off", "state-error")
HIDDEN_LINE = "Hidden=true"
AUTOSTART_DISABLED_LINE = "X-GNOME-Autostart-enabled=false"
DISABLED_AUTOSTART_LINES = frozenset(
    {HIDDEN_LINE.lower(), AUTOSTART_DISABLED_LINE.lower()}
)


class DeskAwakeWidget:
    def __init__(self) -> None:
        self.bus = self._open_bus()
        self.state = "off"
        self.last_error = ""
        self.theme_setting = "auto"
        self.variant = "light"
        self.composited = False
        self.rgba_visual = False
        self.call_pending = False
        self.call_generation = 0
        self.spinner_source = 0
        self.spinner_index = 0
        self.symbol_pixbufs: dict[str, GdkPixbuf.Pixbuf | None] = {}
        self.spinner_pixbufs: dict[str, list[GdkPixbuf.Pixbuf]] = {}
        self.press_root: tuple[float, float] | None = None
        self.dragged = False
        self.press_on_switch = False
        self.drag_timeout = 0
        self._updating_menu = False
        self._subscribed = False
        self._quitting = False
        self.provider = None
        self._symbol_svg = self._read_asset("deskawake.svg")
        self._spinner_svg = self._read_asset("spinner.svg")

        self._build_window()
        self._build_layout()
        self._build_menu()
        self._connect_ui_signals()
        self._apply_state("off")

    @staticmethod
    def _open_bus():
        DBusGMainLoop(set_as_default=True)
        try:
            return dbus.SessionBus()
        except (dbus.DBusException, OSError, KeyError):
            return None

    def _read_asset(self, name: str) -> str:
        try:
            return (ASSETS_PATH / name).read_text(encoding="utf-8")
        except OSError:
            return ""

    def _build_window(self) -> None:
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.get_style_context().add_class("deskawake-window")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_default_size(PILL_WIDTH, PILL_HEIGHT)
        self.window.set_size_request(PILL_WIDTH, PILL_HEIGHT)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.window.set_accept_focus(False)
        self.window.set_focus_on_map(False)

        self.composited = self._is_composited()
        if self.composited and not self._enable_rgba_visual():
            self.composited = False

        self._apply_window_hints()
        self.window.connect("realize", lambda *_: self._apply_window_hints())
        self.window.connect("map", lambda *_: self._apply_window_hints())

    def _apply_window_hints(self) -> None:
        self.window.set_keep_below(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.stick()
        self.window.set_accept_focus(False)
        self.window.set_focus_on_map(False)

    def _screen(self):
        screen = self.window.get_screen() if self.window is not None else None
        return screen if screen is not None else Gdk.Screen.get_default()

    def _is_composited(self) -> bool:
        screen = self._screen()
        return bool(screen is not None and screen.is_composited())

    def _enable_rgba_visual(self) -> bool:
        if self.window is None or self.window.get_realized():
            return self.rgba_visual
        screen = self._screen()
        visual = screen.get_rgba_visual() if screen is not None else None
        if visual is None:
            return False
        self.window.set_visual(visual)
        self.window.set_app_paintable(True)
        self.rgba_visual = True
        return True

    def _build_layout(self) -> None:
        self.pill = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=BOX_SPACING
        )
        self.pill.get_style_context().add_class("deskawake-pill")
        self.pill.set_margin_start(SIDE_MARGIN)
        self.pill.set_margin_end(SIDE_MARGIN)

        self.icon_stack = Gtk.Stack(
            width_request=SYMBOL_SIZE, height_request=SYMBOL_SIZE
        )
        self.icon_stack.set_valign(Gtk.Align.CENTER)
        self.icon_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.icon_stack.set_transition_duration(0)
        self.symbol_image = Gtk.Image()
        self.spinner_image = Gtk.Image()
        self.icon_stack.add_named(self.symbol_image, "symbol")
        self.icon_stack.add_named(self.spinner_image, "spinner")
        self.icon_stack.set_visible_child_name("symbol")

        self.name_label = Gtk.Label(
            label="DeskAwake",
            width_chars=8,
            width_request=NAME_SLOT_WIDTH,
        )
        self.name_label.get_style_context().add_class("deskawake-name")
        self.name_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.name_label.set_single_line_mode(True)
        self.name_label.set_halign(Gtk.Align.CENTER)
        self.name_label.set_valign(Gtk.Align.CENTER)
        self.name_label.set_xalign(0.5)

        self.switch = Gtk.Switch(
            width_request=TOGGLE_WIDTH, height_request=TOGGLE_HEIGHT
        )
        self.switch.get_style_context().add_class("deskawake-switch")
        self.switch.set_valign(Gtk.Align.CENTER)

        self.pill.pack_start(self.icon_stack, False, False, 0)
        self.pill.pack_start(self.name_label, False, False, 0)
        self.pill.pack_end(self.switch, False, False, 0)
        self.window.add(self.pill)

    def _build_menu(self) -> None:
        self.menu = Gtk.Menu()
        self.menu.get_style_context().add_class("deskawake-menu")
        self.menu.attach_to_widget(self.window, None)

        self.toggle_item = Gtk.MenuItem(label="Ativar")
        self.toggle_item.connect("activate", self._on_toggle_item)
        self.menu.append(self.toggle_item)

        self.theme_item = Gtk.MenuItem(label="Tema")
        theme_menu = Gtk.Menu()
        theme_menu.get_style_context().add_class("deskawake-menu")
        self.theme_items: dict[str, Gtk.RadioMenuItem] = {}
        group = None
        for value, label in (
            ("auto", "Automático"),
            ("light", "Claro"),
            ("dark", "Escuro"),
        ):
            item = Gtk.RadioMenuItem(label=label)
            if group is None:
                group = item
            else:
                item.join_group(group)
            item.connect("toggled", self._on_theme_toggled, value)
            theme_menu.append(item)
            self.theme_items[value] = item
        self.theme_item.set_submenu(theme_menu)
        self.menu.append(self.theme_item)

        self.autostart_item = Gtk.CheckMenuItem(label="Iniciar com o sistema")
        self.autostart_item.connect("toggled", self._on_autostart_toggled)
        self.menu.append(self.autostart_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.quit_item = Gtk.MenuItem(label="Sair")
        self.quit_item.connect("activate", lambda *_: self._quit())
        self.menu.append(self.quit_item)

    def _connect_ui_signals(self) -> None:
        events = (
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.window.add_events(events)
        self.switch.add_events(events)

        for widget in (self.window, self.switch):
            widget.connect("button-press-event", self._on_button_press)
            widget.connect("button-release-event", self._on_button_release)
            widget.connect("motion-notify-event", self._on_motion_notify)

        self.window.connect("configure-event", self._on_configure)
        self.window.connect("delete-event", self._on_delete)
        self.switch.connect("state-set", self._on_switch_state_set)
        self.switch.connect("activate", self._on_activate)

        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.connect(
                "notify::gtk-theme-name", self._on_gtk_theme_changed
            )
            settings.connect(
                "notify::gtk-application-prefer-dark-theme",
                self._on_gtk_theme_changed,
            )
        screen = self.window.get_screen()
        if screen is not None:
            screen.connect("composited-changed", self._on_composited_changed)

    def show(self) -> None:
        self._subscribe_signals()
        self.theme_setting, position = self._load_and_initialize_config()
        self._apply_theme()
        self._apply_window_hints()
        self.window.move(position[0], position[1])
        self.window.show_all()
        self.icon_stack.set_visible_child_name("symbol")
        self._sync_initial_state()

    def _apply_theme(self) -> None:
        settings = Gtk.Settings.get_default()
        theme_name = None
        prefer_dark = False
        if settings is not None:
            theme_name = settings.props.gtk_theme_name
            prefer_dark = bool(
                settings.props.gtk_application_prefer_dark_theme
            )

        variant = resolve_variant(self.theme_setting, theme_name, prefer_dark)
        if variant != self.variant:
            self.symbol_pixbufs.clear()
            self.spinner_pixbufs.clear()
        self.variant = variant
        screen_composited = self._is_composited()
        if screen_composited:
            self._enable_rgba_visual()
        self.composited = screen_composited and self.rgba_visual

        if self.provider is None:
            self.provider = Gtk.CssProvider()
            screen = self._screen()
            if screen is not None:
                Gtk.StyleContext.add_provider_for_screen(
                    screen,
                    self.provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
        if self.provider is not None:
            css = build_css(self.variant, self.composited)
            self.provider.load_from_data(css.encode("utf-8"))
        self._update_icons()

    def _on_gtk_theme_changed(self, *args) -> None:
        self._apply_theme()

    def _on_composited_changed(self, *args) -> None:
        self._apply_theme()

    def _pixbuf_from_svg(self, svg: str) -> GdkPixbuf.Pixbuf | None:
        if not svg:
            return None
        loader = GdkPixbuf.PixbufLoader()
        try:
            loader.write(svg.encode("utf-8"))
            loader.close()
            return loader.get_pixbuf()
        except Exception:
            # O loader SVG é um limite de terceiros: falha vira imagem vazia.
            try:
                loader.close()
            except Exception:
                pass
            return None

    def _symbol_pixbuf(self, variant: str) -> GdkPixbuf.Pixbuf | None:
        if variant not in self.symbol_pixbufs:
            colored = svg_with_color(self._symbol_svg, icon_color(variant))
            self.symbol_pixbufs[variant] = self._pixbuf_from_svg(colored)
        return self.symbol_pixbufs[variant]

    def _spinner_frames(self, variant: str) -> list[GdkPixbuf.Pixbuf]:
        if variant not in self.spinner_pixbufs:
            color = icon_color(variant)
            frames = []
            for angle in SPINNER_ANGLES:
                try:
                    frame = spinner_frame(self._spinner_svg, angle, color)
                except Exception:
                    # Asset ausente/inválido: segue com imagem vazia.
                    continue
                pixbuf = self._pixbuf_from_svg(frame)
                if pixbuf is not None:
                    frames.append(pixbuf)
            self.spinner_pixbufs[variant] = frames
        return self.spinner_pixbufs[variant]

    def _update_icons(self) -> None:
        pixbuf = self._symbol_pixbuf(self.variant)
        if pixbuf is not None:
            self.symbol_image.set_from_pixbuf(pixbuf)
        else:
            self.symbol_image.clear()
        if self.spinner_source or self.call_pending:
            self.spinner_index = 0
            self._update_spinner_icon()

    def _update_spinner_icon(self) -> None:
        frames = self._spinner_frames(self.variant)
        if frames:
            self.spinner_image.set_from_pixbuf(
                frames[self.spinner_index % len(frames)]
            )
        else:
            self.spinner_image.clear()

    def _start_spinner(self) -> None:
        if self.spinner_source:
            return
        self.spinner_index = 0
        self._update_spinner_icon()
        self.icon_stack.set_visible_child_name("spinner")
        self.spinner_source = GLib.timeout_add(
            SPINNER_INTERVAL_MS, self._advance_spinner_frame
        )

    def _advance_spinner_frame(self) -> bool:
        if not self.call_pending:
            self.spinner_source = 0
            self.icon_stack.set_visible_child_name("symbol")
            return GLib.SOURCE_REMOVE
        self.spinner_index = (self.spinner_index + 1) % SPINNER_FRAME_COUNT
        self._update_spinner_icon()
        return GLib.SOURCE_CONTINUE

    def _stop_spinner(self) -> None:
        if self.spinner_source:
            GLib.source_remove(self.spinner_source)
            self.spinner_source = 0
        self.icon_stack.set_visible_child_name("symbol")

    def _workareas(self) -> list[tuple[int, int, int, int]]:
        screen = self._screen()
        if screen is None:
            return [(0, 0, PILL_WIDTH + 2 * 24, PILL_HEIGHT + 2 * 24)]

        count = screen.get_n_monitors()
        primary = screen.get_primary_monitor()
        order = [primary] + [index for index in range(count) if index != primary]
        workareas = []
        for index in order:
            if index < 0:
                continue
            geometry = screen.get_monitor_workarea(index)
            workareas.append(
                (geometry.x, geometry.y, geometry.width, geometry.height)
            )
        if not workareas:
            return [(0, 0, PILL_WIDTH + 2 * 24, PILL_HEIGHT + 2 * 24)]
        return workareas

    def _load_and_initialize_config(self) -> tuple[str, tuple[int, int]]:
        workareas = self._workareas()
        existed = CONFIG_PATH.exists()
        config = load_config()
        theme = config.get("theme", "auto")
        if theme not in VALID_THEMES:
            theme = "auto"

        if not existed:
            position = default_position(workareas)
            try:
                save_config(
                    {
                        "theme": "auto",
                        "position": {"x": position[0], "y": position[1]},
                    }
                )
            except OSError:
                pass
        else:
            position = validate_position(config.get("position"), workareas)
        return theme, position

    def _save_position(self, pos: tuple[int, int]) -> None:
        if validate_position(pos, self._workareas()) != pos:
            return
        try:
            save_config(
                {
                    "theme": self.theme_setting,
                    "position": {"x": pos[0], "y": pos[1]},
                }
            )
        except OSError:
            pass

    def _save_theme(self, theme: str) -> None:
        self.theme_setting = theme
        data: dict = {"theme": theme}
        position = self.window.get_position()
        if validate_position(position, self._workareas()) == position:
            data["position"] = {"x": position[0], "y": position[1]}
        try:
            save_config(data)
        except OSError:
            pass

    def _subscribe_signals(self) -> None:
        if self.bus is None or self._subscribed:
            return
        try:
            self.bus.add_signal_receiver(
                self._on_state_changed,
                signal_name="StateChanged",
                dbus_interface=INTERFACE,
                bus_name=DBUS_NAME,
            )
            self.bus.add_signal_receiver(
                self._on_name_owner_changed,
                signal_name="NameOwnerChanged",
                dbus_interface="org.freedesktop.DBus",
                bus_name="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                arg0=DBUS_NAME,
            )
            self._subscribed = True
        except (dbus.DBusException, OSError):
            self._subscribed = False

    def _has_owner(self) -> bool:
        if self.bus is None:
            return False
        try:
            return bool(self.bus.name_has_owner(DBUS_NAME))
        except (dbus.DBusException, OSError):
            return False

    def _proxy_method(self, name: str):
        if self.bus is None:
            raise dbus.DBusException("barramento de sessão indisponível")
        proxy = self.bus.get_object(DBUS_NAME, OBJECT_PATH)
        return proxy.get_dbus_method(name, INTERFACE)

    def _sync_initial_state(self) -> None:
        if not self._has_owner():
            self._apply_state("off")
            return
        self._request_state()

    def _request_state(self) -> None:
        if not self._has_owner():
            self._apply_state("off")
            return
        generation = self.call_generation
        try:
            method = self._proxy_method("GetState")
            method(
                reply_handler=lambda state: self._on_state_reply(
                    generation, state
                ),
                error_handler=lambda error: self._on_query_error(
                    generation, error
                ),
                timeout=2,
            )
        except (dbus.DBusException, OSError):
            self._on_query_error(generation, None)

    def _on_state_reply(self, generation: int, state) -> None:
        if generation != self.call_generation:
            return
        text = str(state)
        if text not in PUBLIC_STATES:
            return
        self._apply_state(text)
        if text == "error":
            self._request_last_error()

    def _on_query_error(self, generation: int, _error) -> None:
        if generation != self.call_generation:
            return
        if not self._has_owner():
            self._apply_state("off")

    def _request_last_error(self) -> None:
        if not self._has_owner():
            return
        generation = self.call_generation
        try:
            method = self._proxy_method("GetLastError")
            method(
                reply_handler=lambda error: self._on_last_error_reply(
                    generation, error
                ),
                error_handler=lambda _error: None,
                timeout=2,
            )
        except (dbus.DBusException, OSError):
            pass

    def _on_last_error_reply(self, generation: int, error) -> None:
        if generation != self.call_generation:
            return
        self.last_error = str(error).strip()
        if self.state == "error":
            self._apply_state("error")

    def _send_set_active(self, active: bool) -> None:
        if self.call_pending:
            return
        self.call_generation += 1
        generation = self.call_generation
        self.call_pending = True
        self._update_busy_state()
        self._start_spinner()
        try:
            method = self._proxy_method("SetActive")
            method(
                dbus.Boolean(active),
                reply_handler=lambda state: self._on_call_reply(
                    generation, state
                ),
                error_handler=lambda error: self._on_call_error(
                    generation, error
                ),
                timeout=5,
            )
        except (dbus.DBusException, OSError):
            self._on_call_error(generation, None)

    def _on_call_reply(self, generation: int, state) -> None:
        if generation != self.call_generation:
            return
        self.call_pending = False
        self._stop_spinner()
        text = str(state)
        if text in PUBLIC_STATES:
            self._apply_state(text)
            if text == "error":
                self._request_last_error()
        else:
            self._update_busy_state()

    def _on_call_error(self, generation: int, _error) -> None:
        if generation != self.call_generation:
            return
        self.call_pending = False
        self._stop_spinner()
        if self._has_owner():
            self._update_busy_state()
            self._request_state()
        else:
            self._apply_state("off")

    def _on_state_changed(self, state) -> None:
        text = str(state)
        if text not in PUBLIC_STATES:
            return
        self._apply_state(text)
        if text == "error":
            self._request_last_error()

    def _on_name_owner_changed(self, name, old_owner, new_owner) -> None:
        if str(name) != DBUS_NAME:
            return
        self.call_generation += 1
        self.call_pending = False
        self._stop_spinner()
        if str(new_owner):
            self._update_busy_state()
            self._request_state()
        else:
            self.last_error = ""
            self._apply_state("off")
            if self._quitting:
                self._close()

    def _apply_state(self, state: str) -> None:
        if state not in PUBLIC_STATES:
            return
        self.state = state
        context = self.pill.get_style_context()
        for name in STATE_CLASSES:
            context.remove_class(name)
        context.add_class(f"state-{state}")
        self.switch.set_active(state == "on")
        self._update_busy_state()
        if state == "error":
            self.window.set_tooltip_text(self.last_error or ERROR_FALLBACK)
        else:
            self.window.set_tooltip_text(None)
        if not self.call_pending:
            self.icon_stack.set_visible_child_name("symbol")
        self._update_menu()

    def _update_busy_state(self) -> None:
        self.switch.set_sensitive(not self.call_pending)
        self.toggle_item.set_sensitive(not self.call_pending)
        self.quit_item.set_sensitive(not self.call_pending)

    def _update_menu(self) -> None:
        self.toggle_item.set_label(
            "Desativar" if self.state == "on" else "Ativar"
        )
        self._updating_menu = True
        try:
            for value, item in self.theme_items.items():
                item.set_active(value == self.theme_setting)
            self.autostart_item.set_active(self._autostart_enabled())
        finally:
            self._updating_menu = False
        self._update_busy_state()

    def _event_on_switch(self, widget, event) -> bool:
        if widget is self.switch:
            return True
        pill_allocation = self.pill.get_allocation()
        switch_allocation = self.switch.get_allocation()
        origin_x = pill_allocation.x + switch_allocation.x
        origin_y = pill_allocation.y + switch_allocation.y
        x = int(event.x)
        y = int(event.y)
        return (
            origin_x <= x < origin_x + switch_allocation.width
            and origin_y <= y < origin_y + switch_allocation.height
        )

    def _on_switch_state_set(self, switch, desired: bool) -> bool:
        if self.dragged or self.call_pending:
            return True
        if bool(desired) == (self.state == "on"):
            return True
        self._send_set_active(bool(desired))
        return True

    def _on_activate(self, switch) -> bool:
        return True if (self.dragged or self.call_pending) else False

    def _on_button_press(self, widget, event) -> bool:
        if event.button == 3:
            return self._popup_menu(event)
        if event.button != 1:
            return False
        self.press_root = (event.x_root, event.y_root)
        self.dragged = False
        self.press_on_switch = self._event_on_switch(widget, event)
        return False

    def _on_motion_notify(self, widget, event) -> bool:
        if self.press_root is None:
            return False
        if not (event.state & Gdk.ModifierType.BUTTON1_MASK):
            return False
        if self.dragged:
            return True
        delta_x = event.x_root - self.press_root[0]
        delta_y = event.y_root - self.press_root[1]
        if (delta_x * delta_x + delta_y * delta_y) ** 0.5 <= DRAG_THRESHOLD:
            return False
        self.dragged = True
        self.window.begin_move_drag(
            1, int(event.x_root), int(event.y_root), event.time
        )
        return True

    def _on_button_release(self, widget, event) -> bool:
        if event.button == 3:
            return False
        if event.button != 1:
            return False
        if self.dragged:
            self._finish_drag()
            self.press_root = None
            return True
        on_switch = self.press_on_switch or self._event_on_switch(
            widget, event
        )
        self.press_root = None
        self.press_on_switch = False
        return not on_switch

    def _on_configure(self, widget, event) -> bool:
        if not self.dragged:
            return False
        if self.drag_timeout:
            GLib.source_remove(self.drag_timeout)
            self.drag_timeout = 0
        self.drag_timeout = GLib.timeout_add(250, self._on_drag_timeout)
        return False

    def _on_drag_timeout(self) -> bool:
        self.drag_timeout = 0
        self._finish_drag()
        return GLib.SOURCE_REMOVE

    def _finish_drag(self) -> None:
        if self.drag_timeout:
            GLib.source_remove(self.drag_timeout)
            self.drag_timeout = 0
        if self.window is not None:
            position = self.window.get_position()
            if validate_position(position, self._workareas()) == position:
                self._save_position(position)
        self.dragged = False
        self.press_on_switch = False
        self.press_root = None
        self._apply_state(self.state)

    def _popup_menu(self, event) -> bool:
        self._update_menu()
        if self.state == "error":
            self._request_last_error()
        self.menu.show_all()
        self.menu.popup_at_pointer(event)
        return True

    def _on_toggle_item(self, widget) -> None:
        self._send_set_active(self.state != "on")

    def _on_theme_toggled(self, item, value: str) -> None:
        if self._updating_menu or not item.get_active():
            return
        self._save_theme(value)
        self._apply_theme()

    def _on_autostart_toggled(self, item) -> None:
        if self._updating_menu:
            return
        enabled = bool(item.get_active())
        try:
            self._set_autostart(enabled)
        except OSError:
            self._updating_menu = True
            try:
                item.set_active(not enabled)
            finally:
                self._updating_menu = False

    def _autostart_enabled(self) -> bool:
        try:
            text = AUTOSTART_PATH.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        for line in text.splitlines():
            normalized = line.strip().lower()
            if normalized in DISABLED_AUTOSTART_LINES:
                return False
        return True

    def _exec_line(self) -> str:
        binary = ROOT / "bin" / "deskawake"
        path = str(binary)
        if any(character.isspace() for character in path):
            path = f'"{path}"'
        return f"{path} ui"

    def _set_autostart(self, enabled: bool) -> None:
        if not enabled:
            AUTOSTART_PATH.unlink(missing_ok=True)
            return

        exec_line = self._exec_line()
        try:
            template = TEMPLATE_PATH.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            template = None

        if template is None:
            lines = [
                "[Desktop Entry]",
                "Type=Application",
                "Name=DeskAwake",
                "Comment=Widget DeskAwake",
                f"Exec={exec_line}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
            ]
        else:
            lines = template.splitlines()
            if not any(
                line.strip() == "[Desktop Entry]" for line in lines
            ):
                lines.insert(0, "[Desktop Entry]")
            updated = []
            has_exec = False
            has_enabled = False
            for line in lines:
                if "=" not in line:
                    updated.append(line)
                    continue
                key, value = line.split("=", 1)
                normalized = key.strip().lower()
                if normalized == "hidden" and value.strip().lower() == "true":
                    continue
                if normalized == "exec":
                    updated.append(f"Exec={exec_line}")
                    has_exec = True
                    continue
                if normalized == "x-gnome-autostart-enabled":
                    updated.append("X-GNOME-Autostart-enabled=true")
                    has_enabled = True
                    continue
                updated.append(line)
            if not has_exec:
                updated.append(f"Exec={exec_line}")
            if not has_enabled:
                updated.append("X-GNOME-Autostart-enabled=true")
            lines = updated

        content = "\n".join(lines) + "\n"
        AUTOSTART_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = AUTOSTART_PATH.with_name(AUTOSTART_PATH.name + ".tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, AUTOSTART_PATH)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _quit(self) -> None:
        self._quitting = True
        if self.bus is None or not self._has_owner():
            self._close()
            return
        self.call_generation += 1
        generation = self.call_generation
        self.call_pending = True
        self._stop_spinner()
        self._update_busy_state()
        try:
            method = self._proxy_method("SetActive")
            method(
                dbus.Boolean(False),
                reply_handler=lambda state: self._request_quit(generation),
                error_handler=lambda error: self._request_quit(generation),
                timeout=5,
            )
        except (dbus.DBusException, OSError):
            self._request_quit(generation)

    def _request_quit(self, generation: int) -> None:
        # SetActive(false) já liberou os inibidores; Quit() encerra o daemon.
        if generation != self.call_generation:
            return
        if not self._has_owner():
            self._close()
            return
        try:
            method = self._proxy_method("Quit")
            method(
                reply_handler=lambda: self._close(),
                error_handler=lambda error: self._close(),
                timeout=2,
            )
        except (dbus.DBusException, OSError):
            self._close()

    def _close(self) -> None:
        self.call_generation += 1
        self._stop_spinner()
        Gtk.main_quit()

    def _on_delete(self, widget, event) -> bool:
        self._quit()
        return True


def _gtk_initialized() -> bool:
    result = Gtk.init_check()
    if isinstance(result, tuple):
        return bool(result[0])
    return bool(result)


def main() -> int:
    DBusGMainLoop(set_as_default=True)
    if not _gtk_initialized():
        raise RuntimeError("não foi possível abrir o display")
    widget = DeskAwakeWidget()
    widget.show()
    Gtk.main()
    return 0
