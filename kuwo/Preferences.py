
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import os
import shutil
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from kuwo import Config
_ = Config._
from kuwo import Widgets

MARGIN_LEFT = 15
MARGIN_TOP = 20
ShortcutMode = Config.ShortcutMode

DISNAME_COL, NAME_COL, KEY_COL, MOD_COL = list(range(4))


class NoteTab(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(10)


class ColorBox(Gtk.Box):

    def __init__(self, label, conf, color_name, use_margin=False):
        super().__init__()
        self.conf = conf
        self.color_name = color_name
        left_label = Gtk.Label(label)
        self.pack_start(left_label, False, True, 0)

        color_button = Gtk.ColorButton()
        color_button.set_use_alpha(True)
        color_rgba = Gdk.RGBA()
        color_rgba.parse(conf[color_name])
        color_button.set_rgba(color_rgba)
        color_button.connect('color-set', self.on_color_set)
        self.pack_end(color_button, False, True, 0)

        if use_margin:
            self.props.margin_left = 20

    def on_color_set(self, color_button):
        color_rgba = color_button.get_rgba()
        if color_rgba.alpha == 1:
            color_rgba.alpha = 0.999
        self.conf[self.color_name] = color_rgba.to_string()


class FontBox(Gtk.Box):

    def __init__(self, label, conf, font_name, use_margin=True):
        super().__init__()
        self.conf = conf
        self.font_name = font_name
        left_label = Gtk.Label(label)
        self.pack_start(left_label, False, True, 0)

        font_button = Gtk.SpinButton.new_with_range(4, 72, 1)
        font_button.set_value(conf[font_name])
        font_button.connect('value-changed', self.on_font_set)
        self.pack_end(font_button, False, True, 0)

        if use_margin:
            self.props.margin_left = 20

    def on_font_set(self, font_button):
        self.conf[self.font_name] = font_button.get_value()


class ChooseFolder(Gtk.Box):

    def __init__(self, parent, conf_name, toggle_label):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.props.margin_left = MARGIN_LEFT
        self.props.margin_top = 5
        self.parent = parent
        self.app = parent.app
        self.conf_name = conf_name
        self.old_dir = self.app.conf[conf_name]

        hbox = Gtk.Box(spacing=5)
        self.pack_start(hbox, False, True, 0)

        self.dir_entry = Gtk.Entry()
        self.dir_entry.set_text(self.old_dir)
        self.dir_entry.props.editable = False
        self.dir_entry.props.can_focus = False
        self.dir_entry.props.width_chars = 20
        hbox.pack_start(self.dir_entry, True, True, 0)

        choose_button = Gtk.Button('...')
        choose_button.connect('clicked', self.on_choose_button_clicked)
        hbox.pack_start(choose_button, False, False, 0)

    def on_choose_button_clicked(self, button):
        def on_dialog_file_activated(dialog):
            new_dir = dialog.get_filename()
            dialog.destroy()
            self.dir_entry.set_text(new_dir)
            if new_dir != self.app.conf[self.conf_name]:
                self.app.conf[self.conf_name] = new_dir
            return

        dialog = Gtk.FileChooserDialog(_('Choose a Folder'), self.parent,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))

        dialog.connect('file-activated', on_dialog_file_activated)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            on_dialog_file_activated(dialog)
            return
        dialog.destroy()


class Preferences(Gtk.Dialog):

    def __init__(self, app):
        self.app = app
        super().__init__(_('Preferences'), app.window, 0,
                         (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,))
        self.set_modal(True)
        self.set_transient_for(app.window)
        self.set_default_size(600, 320)
        self.set_border_width(5)
        box = self.get_content_area()

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # generic tab
        generic_box = NoteTab()
        notebook.append_page(generic_box, Gtk.Label(_('Generic')))

        status_button = Gtk.CheckButton(_('Close to system tray'))
        status_button.set_active(app.conf['use-status-icon'])
        status_button.connect('toggled', self.on_status_button_toggled)
        generic_box.pack_start(status_button, False, False, 0)

        notify_button = Gtk.CheckButton(_('Show kwplayer on lock screen'))
        notify_button.set_tooltip_text(
            _('Only works with gdm3/gnome3.8+\n') + 
            _('Please disable it on other desktop environments (like KDE)'))
        notify_button.set_active(app.conf['use-notify'])
        notify_button.connect('toggled', self.on_notify_button_toggled)
        generic_box.pack_start(notify_button, False, False, 0)

        show_pls_button = Gtk.CheckButton(_('Show playlist tab on startup'))
        show_pls_button.set_active(app.conf['show-pls'])
        show_pls_button.connect('toggled', self.on_show_pls_button_toggled)
        generic_box.pack_start(show_pls_button, False, False, 0)

        dark_theme_button = Gtk.CheckButton(_('Use dark theme'))
        dark_theme_button.set_active(app.conf['use-dark-theme'])
        dark_theme_button.connect('toggled', self.on_dark_theme_button_toggled)
        generic_box.pack_start(dark_theme_button, False, False, 0)

        # format tab
        format_box = NoteTab()
        notebook.append_page(format_box, Gtk.Label(_('Format')))

        audio_label = Widgets.BoldLabel(_('Prefered Audio Format'))
        format_box.pack_start(audio_label, False, False, 0)
        audio_128k = Gtk.RadioButton(_('128K MP3 (Fastest)'))
        audio_128k.order = 0
        audio_128k.props.margin_left = MARGIN_LEFT
        audio_128k.connect('toggled', self.on_audio_toggled)
        format_box.pack_start(audio_128k, False, False, 0)
        audio_192k = Gtk.RadioButton(_('192K MP3'))
        audio_192k.order = 1
        audio_192k.join_group(audio_128k)
        audio_192k.props.margin_left = MARGIN_LEFT
        audio_192k.connect('toggled', self.on_audio_toggled)
        format_box.pack_start(audio_192k, False, False, 0)
        audio_320k = Gtk.RadioButton(_('320K MP3'))
        audio_320k.order = 2
        audio_320k.props.margin_left = MARGIN_LEFT
        audio_320k.connect('toggled', self.on_audio_toggled)
        audio_320k.join_group(audio_128k)
        format_box.pack_start(audio_320k, False, False, 0)
        audio_flac = Gtk.RadioButton(_('Flac Lossless (Best Quality)'))
        audio_flac.order = 3
        audio_flac.props.margin_left = MARGIN_LEFT
        audio_flac.connect('toggled', self.on_audio_toggled)
        audio_flac.join_group(audio_128k)
        format_box.pack_start(audio_flac, False, False, 0)
        for btn in audio_flac.get_group():
            btn.set_active(btn.order == self.app.conf['audio'])

        video_label = Widgets.BoldLabel(_('Prefered Video Format'))
        video_label.props.margin_top = MARGIN_TOP
        format_box.pack_start(video_label, False, False, 0)
        video_mp4l = Gtk.RadioButton(_('MP4L (Faster)'))
        video_mp4l.props.margin_left = MARGIN_LEFT
        video_mp4l.connect('toggled', self.on_video_toggled)
        video_mp4l.order = 0
        format_box.pack_start(video_mp4l, False, False, 0)
        video_mp4 = Gtk.RadioButton(_('MP4 (Better)'))
        video_mp4.props.margin_left = MARGIN_LEFT
        video_mp4.join_group(video_mp4l)
        video_mp4.connect('toggled', self.on_video_toggled)
        video_mp4.order = 1
        format_box.pack_start(video_mp4, False, False, 0)
        video_mp4.set_active(self.app.conf['video'] == video_mp4.order)

        # lyrics tab
        lrc_box = NoteTab()
        notebook.append_page(lrc_box, Gtk.Label(_('Lyrics')))

        lrc_normal_text_label = Widgets.BoldLabel(_('Normal Text'))
        lrc_box.pack_start(lrc_normal_text_label, False, True, 0)

        lrc_normal_text_size = FontBox(_('text size'), app.conf,
                                       'lrc-text-size', use_margin=True)
        lrc_box.pack_start(lrc_normal_text_size, False, True, 0)

        lrc_normal_text_color = ColorBox(_('text color'), app.conf,
                                         'lrc-text-color', use_margin=True)
        lrc_box.pack_start(lrc_normal_text_color, False, True, 0)
        lrc_normal_text_color.props.margin_bottom = 10

        lrc_highlighted_text_label = Widgets.BoldLabel(_('Highlighted Text'))
        lrc_box.pack_start(lrc_highlighted_text_label, False, True, 0)

        lrc_highlighted_text_size = FontBox(_('text size'), app.conf,
                                            'lrc-highlighted-text-size',
                                            use_margin=True)
        lrc_box.pack_start(lrc_highlighted_text_size, False, True, 0)

        lrc_highlighted_text_color = ColorBox(_('text color'), app.conf,
                                              'lrc-highlighted-text-color',
                                              use_margin=True)
        lrc_highlighted_text_color.props.margin_bottom = 10
        lrc_box.pack_start(lrc_highlighted_text_color, False, True, 0)

        lrc_word_back_color = ColorBox(_('Lyrics Text Background color'),
                                       app.conf, 'lrc-back-color')
        lrc_box.pack_start(lrc_word_back_color, False, True, 0)

        # folders tab
        folder_box = NoteTab()
        notebook.append_page(folder_box, Gtk.Label(_('Folders')))

        song_folder_label = Widgets.BoldLabel(_('Place to store sogns'))
        folder_box.pack_start(song_folder_label, False, False, 0)
        song_folder = ChooseFolder(self, 'song-dir',
                                   _('Moving cached songs to new folder'))
        folder_box.pack_start(song_folder, False, False, 0)

        mv_folder_label = Widgets.BoldLabel(_('Place to store MVs'))
        mv_folder_label.props.margin_top = MARGIN_TOP
        folder_box.pack_start(mv_folder_label, False, False, 0)
        mv_folder = ChooseFolder(self, 'mv-dir',
                                 _('Moving cached MVs to new folder'))
        folder_box.pack_start(mv_folder, False, False, 0)

        self.notebook = notebook

        # shortcut tab
        self.init_shortcut_tab()

    def init_shortcut_tab(self):
        curr_mode = self.app.conf['shortcut-mode']

        box = NoteTab()
        self.notebook.append_page(box, Gtk.Label(_('Shortcut')))

        self.shortcut_win = Gtk.ScrolledWindow()

        disable_btn = Gtk.RadioButton(_('Disable Keyboard Shortcut'))
        disable_btn.connect('toggled', self.on_shortcut_btn_toggled,
                            ShortcutMode.NONE)
        disable_btn.set_active(curr_mode == ShortcutMode.NONE)
        box.pack_start(disable_btn, False, False, 0)

        default_btn = Gtk.RadioButton(_('Use Default MultiMedia Key'))
        default_btn.connect('toggled', self.on_shortcut_btn_toggled,
                            ShortcutMode.DEFAULT)
        default_btn.join_group(disable_btn)
        default_btn.set_active(curr_mode == ShortcutMode.DEFAULT)
        box.pack_start(default_btn, False, False, 0)

        custom_btn = Gtk.RadioButton(_('Use Custom Keyboard Shortcut'))
        custom_btn.connect('toggled', self.on_shortcut_btn_toggled,
                           ShortcutMode.CUSTOM)
        custom_btn.join_group(default_btn)
        custom_btn.set_active(curr_mode == ShortcutMode.CUSTOM)
        box.pack_start(custom_btn, False, False, 0)

        self.shortcut_win.props.margin_left = 10
        self.shortcut_win.set_sensitive(curr_mode == ShortcutMode.CUSTOM)
        box.pack_start(self.shortcut_win, True, True, 0)

        # disname, name, shortct key, shortcut modifiers
        self.shortcut_liststore = Gtk.ListStore(str, str, int, int)
        tv = Gtk.TreeView(model=self.shortcut_liststore)
        self.shortcut_win.add(tv)

        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn('Action', name_cell, text=DISNAME_COL)
        tv.append_column(name_col)

        key_cell = Gtk.CellRendererAccel(editable=True)
        key_cell.connect('accel-edited', self.on_shortcut_key_cell_edited)
        key_col = Gtk.TreeViewColumn('Shortcut Key', key_cell,
                                     accel_key=KEY_COL, accel_mods=MOD_COL)
        tv.append_column(key_col)
        
        for name in self.app.conf['custom-shortcut']:
            key = self.app.conf['custom-shortcut'][name]
            i18n_name = Config.SHORT_CUT_I18N[name]
            k, m = Gtk.accelerator_parse(key)
            self.shortcut_liststore.append([i18n_name, name, k, m])

    def run(self):
        self.get_content_area().show_all()
        super().run()

    def on_destroy(self):
        Config.dump_conf(self.app.conf)

    # generic tab signal handlers
    def on_status_button_toggled(self, button):
        self.app.conf['use-status-icon'] = button.get_active()

    def on_notify_button_toggled(self, button):
        self.app.conf['use-notify'] = button.get_active()

    def on_show_pls_button_toggled(self, button):
        self.app.conf['show-pls'] = button.get_active()

    def on_dark_theme_button_toggled(self, button):
        self.app.conf['use-dark-theme'] = button.get_active()

    # format tab signal handlers
    def on_audio_toggled(self, radiobtn):
        if radiobtn.get_active():
            self.app.conf['audio'] = radiobtn.order

    def on_video_toggled(self, radiobtn):
        if radiobtn.get_active():
            self.app.conf['video'] = radiobtn.order

    def on_shortcut_btn_toggled(self, button, mode):
        if button.get_active() is False:
            return
        self.app.conf['shortcut-mode'] = mode
        self.shortcut_win.set_sensitive(mode == ShortcutMode.CUSTOM)

    def on_shortcut_key_cell_edited(self, accel, path, key, mod,
                                    hardware_keycode):
        accel_key = Gtk.accelerator_name(key, mod)
        name = self.shortcut_liststore[path][NAME_COL]
        self.shortcut_liststore[path][KEY_COL] = key
        self.shortcut_liststore[path][MOD_COL] = int(mod)
        self.app.conf['custom-shortcut'][name] = accel_key
