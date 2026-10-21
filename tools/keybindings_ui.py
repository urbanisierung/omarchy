"""Native, single-instance shortcut reference. Rows never execute their actions."""

import importlib.util
import os
from collections import Counter
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, Gtk, Pango

spec = importlib.util.spec_from_file_location(
    "keybindings", Path(__file__).with_name("keybindings.py")
)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

CSS = b"""
#shortcuts { background: #151923; color: #e4e9f2; font-family: sans-serif; font-size: 14px; }
#shortcuts headerbar { background: #1b202d; border: 0; box-shadow: none; color: #e4e9f2; }
#shortcuts button { background: #252c3b; color: #e4e9f2; border: 1px solid #394356;
  border-radius: 8px; box-shadow: none; text-shadow: none; padding: 7px 12px; }
#shortcuts button:hover { background: #354158; }
#shortcuts button:focus { border-color: #92b8ed; }
#shortcuts .title { font-size: 28px; font-weight: 700; }
#shortcuts .muted { color: #a6b2c6; font-size: 12px; }
#shortcuts .eyebrow { color: #9dc6fa; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
#shortcuts entry { background: #202737; color: #edf3ff; border: 1px solid #43516b;
  border-radius: 10px; padding: 12px; box-shadow: none; caret-color: #9dc6fa; }
#shortcuts entry:focus { border-color: #9dc6fa; }
#shortcuts list { background: transparent; }
#shortcuts .sidebar row { border-radius: 8px; margin: 2px 0; padding: 11px 10px; }
#shortcuts .sidebar row:selected { background: #2c3b53; color: #b9d6ff; }
#shortcuts .sidebar row:hover { background: #252e40; }
#shortcuts .card { background: #1e2533; border: 1px solid #303c50;
  border-radius: 10px; margin: 0 0 8px 0; padding: 14px; }
#shortcuts .card:hover { background: #252e40; }
#shortcuts .action { font-weight: 600; font-size: 15px; }
#shortcuts .keycap { background: #303b50; color: #d2e4ff; border: 1px solid #4a5972;
  border-bottom-width: 3px; border-radius: 6px; padding: 5px 9px;
  font-family: monospace; font-size: 12px; font-weight: 600; }
#shortcuts .details { color: #bcc9dc; font-family: monospace; font-size: 12px; }
#shortcuts .warning { color: #f0c991; }
#shortcuts .empty { color: #a6b2c6; padding: 45px; font-size: 18px; }
"""


def label(text, style=None, wrap=False):
    widget = Gtk.Label(label=text, xalign=0)
    if style:
        widget.get_style_context().add_class(style)
    if wrap:
        widget.set_line_wrap(True)
        widget.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        widget.set_max_width_chars(65)
    return widget


def box(vertical=False, spacing=0):
    return Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL
        if vertical
        else Gtk.Orientation.HORIZONTAL,
        spacing=spacing,
    )


class ShortcutWindow(Gtk.ApplicationWindow):
    def __init__(self, app, load, export):
        super().__init__(application=app, title="Keyboard shortcuts")
        self.set_name("shortcuts")
        self.set_wmclass("omarchy-keybindings", "OmarchyKeybindings")
        self.set_default_size(1080, 780)
        self.load = load
        self.export = export
        self.category = "All shortcuts"
        self.rows = []
        self.cache = (
            Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            / "omarchy/keybindings.json"
        )

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        header = Gtk.HeaderBar(title="Shortcut library", show_close_button=True)
        self.set_titlebar(header)
        self.export_button = Gtk.Button(label="Export JSON…", sensitive=False)
        self.export_button.connect("clicked", self.save_dialog)
        header.pack_end(self.export_button)
        refresh = Gtk.Button(label="Refresh")
        refresh.connect("clicked", lambda _: self.reload())
        header.pack_end(refresh)

        layout = box(True, 16)
        layout.set_border_width(24)
        self.add(layout)
        layout.pack_start(label("OMARCHY / KEYBOARD", "eyebrow"), False, False, 0)
        layout.pack_start(
            label("Your desktop, at your fingertips.", "title"), False, False, 0
        )
        self.summary = label("", "muted")
        layout.pack_start(self.summary, False, False, 0)
        self.search = Gtk.SearchEntry(
            placeholder_text="Search actions, keys, commands or source files…"
        )
        self.search.connect("search-changed", lambda _: self.filter_rows())
        self.search.connect("key-press-event", self.on_key)
        layout.pack_start(self.search, False, False, 0)

        body = box(spacing=22)
        layout.pack_start(body, True, True, 0)
        self.categories = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.categories.get_style_context().add_class("sidebar")
        self.categories.set_valign(Gtk.Align.START)
        self.categories.set_size_request(195, -1)
        self.categories.connect("row-selected", self.select_category)
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_size_request(210, -1)
        sidebar_scroll.add(self.categories)
        body.pack_start(sidebar_scroll, False, False, 0)

        self.listing = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.listing.set_filter_func(self.visible)
        self.listing.set_placeholder(
            label("No matching shortcuts. Try another search.", "empty", True)
        )
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.listing)
        body.pack_start(self.scroll, True, True, 0)

        footer = box(spacing=16)
        self.count = label("", "muted")
        footer.pack_start(self.count, True, True, 0)
        footer.pack_end(
            label("Ctrl+F  Search     Esc  Close · Read-only reference", "muted"),
            False,
            False,
            0,
        )
        layout.pack_end(footer, False, False, 0)
        self.notice = label("", "warning", True)
        self.notice.set_no_show_all(True)
        layout.pack_end(self.notice, False, False, 0)
        self.connect("key-press-event", self.on_key)
        self.reload()
        self.show_all()
        self.search.grab_focus()

    def reload(self):
        try:
            self.data = self.load()
        except (OSError, ValueError) as error:
            self.notify(str(error))
            return
        self.export_button.set_sensitive(True)
        for container in (self.categories, self.listing):
            for child in container.get_children():
                container.remove(child)
        self.rows = []
        bindings = self.data["bindings"]
        counts = Counter(b["category"] for b in bindings)
        for name in ["All shortcuts"] + sorted(counts):
            row = Gtk.ListBoxRow()
            row.category = name
            content = box(spacing=8)
            content.pack_start(label(name), True, True, 0)
            content.pack_end(
                label(
                    str(len(bindings) if name == "All shortcuts" else counts[name]),
                    "muted",
                ),
                False,
                False,
                0,
            )
            row.add(content)
            self.categories.add(row)
        for binding in sorted(
            bindings, key=lambda b: (b["category"], b["description"], b["keys"])
        ):
            self.add_binding(binding)
        self.categories.show_all()
        self.listing.show_all()
        self.categories.select_row(self.categories.get_row_at_index(0))
        state = (
            "Checked against live Hyprland"
            if self.data["live_checked"]
            else "Configuration snapshot"
        )
        self.summary.set_text(
            f"{len(bindings)} shortcuts · {len(self.data['sources'])} source files · {state}"
        )
        warnings = list(self.data["warnings"])
        try:
            self.export(self.data, self.cache)
        except OSError as error:
            warnings.append(f"Could not update JSON cache: {error}")
        self.notify("\n".join(warnings))
        self.filter_rows()

    def add_binding(self, binding):
        row = Gtk.ListBoxRow()
        row.binding = binding
        row.get_style_context().add_class("card")
        content = box(True, 10)
        top = box(spacing=16)
        text = box(True, 5)
        text.pack_start(label(binding["description"], "action", True), False, False, 0)
        mode = binding["submap"]
        mode_label = (
            "Power menu"
            if "shutdown" in mode
            else f"{mode.capitalize()} mode"
            if mode
            else "Global"
        )
        subtitle = f"{binding['category']} · {mode_label}"
        if binding["context"]:
            subtitle += f" · {binding['context']}"
        if binding["status"] == "configured_only":
            subtitle += " · Not registered in the running session"
        elif binding["status"] == "unverified":
            subtitle += " · Key from configuration"
        text.pack_start(label(subtitle, "muted", True), False, False, 0)
        top.pack_start(text, True, True, 0)
        keys = box(spacing=5)
        keys.set_valign(Gtk.Align.CENTER)
        for key in binding["keycaps"]:
            keys.pack_start(label(key, "keycap"), False, False, 0)
        keys.set_tooltip_text(binding["keys"])
        top.pack_end(keys, False, False, 0)
        content.pack_start(top, False, False, 0)
        expander = Gtk.Expander(label="Source & action")
        source = (
            f"{binding['source']}:{binding['line']}"
            if binding["source"]
            else "Runtime registration"
        )
        details = label(
            f"{source}\n{binding['command'] or binding['action']}\n"
            f"Binding: {binding['keys']}\nMode: {mode or 'global'}\n"
            f"Flags: {', '.join(binding['flags']) or 'none'} · Status: {binding['status']}",
            "details",
            True,
        )
        details.set_selectable(True)
        expander.add(details)
        content.pack_start(expander, False, False, 0)
        row.add(content)
        self.rows.append(row)
        self.listing.add(row)

    def visible(self, row):
        return (
            self.category == "All shortcuts" or row.binding["category"] == self.category
        ) and catalog.matches(row.binding, self.search.get_text())

    def filter_rows(self):
        self.listing.invalidate_filter()
        self.count.set_text(
            f"{sum(self.visible(row) for row in self.rows)} of {len(self.rows)} shortcuts"
        )
        self.scroll.get_vadjustment().set_value(0)

    def select_category(self, _list, row):
        if row:
            self.category = row.category
            self.filter_rows()

    def on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if (
            event.keyval in (Gdk.KEY_f, Gdk.KEY_F)
            and event.state & Gdk.ModifierType.CONTROL_MASK
        ):
            self.search.grab_focus()
            return True
        return False

    def notify(self, message):
        self.notice.set_text(message)
        self.notice.set_visible(bool(message))

    def save_dialog(self, _button):
        dialog = Gtk.FileChooserNative.new(
            "Export shortcut catalog",
            self,
            Gtk.FileChooserAction.SAVE,
            "Export",
            "Cancel",
        )
        dialog.set_current_name("keybindings.json")
        dialog.set_do_overwrite_confirmation(True)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            try:
                self.export(self.data, dialog.get_filename())
                self.notify(f"Exported to {dialog.get_filename()}")
            except OSError as error:
                self.notify(f"Export failed: {error}")
        dialog.destroy()


def show(load, export):
    app = Gtk.Application(
        application_id="org.omarchy.Keybindings", flags=Gio.ApplicationFlags.FLAGS_NONE
    )

    def activate(application):
        window = application.get_active_window()
        if window is None:
            window = ShortcutWindow(application, load, export)
        else:
            window.reload()
        window.present()
        window.search.grab_focus()

    app.connect("activate", activate)
    app.run([])
