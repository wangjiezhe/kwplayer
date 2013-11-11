
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk
import os
import sys

from kuwo import Config
# ~/.config/kuwo and ~/.cache/kuwo need to be created at first time
Config.check_first()
_ = Config._

from kuwo.Artists import Artists
from kuwo.Lrc import Lrc
from kuwo.MV import MV
from kuwo.Player import Player
from kuwo.PlayList import PlayList
from kuwo.Radio import Radio
from kuwo.Search import Search
from kuwo.Themes import Themes
from kuwo.TopCategories import TopCategories
from kuwo.TopList import TopList
from kuwo.Shortcut import Shortcut

GObject.threads_init()
DBUS_APP_NAME = 'org.liulang.kwplayer'

class App:
    def __init__(self):
        self.app = Gtk.Application.new(DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

        self.conf = Config.load_conf()
        self.theme, self.theme_path = Config.load_theme()

    def on_app_startup(self, app):
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.props.hide_titlebar_when_maximized = True
        self.window.set_icon(self.theme['app-logo'])
        app.add_window(self.window)
        self.window.connect('check-resize', self.on_main_window_resized)
        self.window.connect('delete-event', self.on_main_window_deleted)

        self.accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.player = Player(self)
        box.pack_start(self.player, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.tab_pos = Gtk.PositionType.BOTTOM
        self.notebook.get_style_context().add_class('main_tab')
        box.pack_start(self.notebook, True, True, 0)

        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switch_page)
        self.init_status_icon()

        # load styles
        self.load_styles()

    def on_app_activate(self, app):
        self.window.show_all()
        # make some changes after main window is shown.
        self.lrc.after_init()
        self.player.after_init()
        self.search.after_init()
        self.shortcut = Shortcut(self.player)

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        self.window.destroy()
        self.shortcut.quit()
        self.app.quit()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_main_window_deleted(self, window, event):
        if self.conf['use-status-icon']:
            window.hide()
            return True
        else:
            return False

    def init_notebook(self):
        self.lrc = Lrc(self)
        self.lrc.app_page = self.notebook.append_page(
                self.lrc, Gtk.Label(_('Lyrics')))

        self.playlist = PlayList(self)
        self.playlist.app_page = self.notebook.append_page(
                self.playlist, Gtk.Label(_('Playlist')))

        self.search = Search(self)
        self.search.app_page = self.notebook.append_page(
                self.search, Gtk.Label(_('Search')))

        self.toplist = TopList(self)
        self.toplist.app_page = self.notebook.append_page(
                self.toplist, Gtk.Label(_('Top List')))

        self.radio = Radio(self)
        self.radio.app_page = self.notebook.append_page(
                self.radio, Gtk.Label(_('Radio')))

        self.mv = MV(self)
        self.mv.app_page = self.notebook.append_page(
                self.mv, Gtk.Label(_('MV')))

        self.artists = Artists(self)
        self.artists.app_page = self.notebook.append_page(
                self.artists, Gtk.Label(_('Artists')))

        self.topcategories = TopCategories(self)
        self.topcategories.app_page = self.notebook.append_page(
                self.topcategories, Gtk.Label(_('Categories')))

        self.themes = Themes(self)
        self.themes.app_page = self.notebook.append_page(
                self.themes, Gtk.Label(_('Themes')))

    def on_notebook_switch_page(self, notebook, page, page_num):
        page.first()

    def popup_page(self, page):
        self.notebook.set_current_page(page)

    def apply_css(self, widget, css, old_provider=None, overall=False):
        # CssProvider needs bytecode
        style_provider = Gtk.CssProvider()
        _css = css.encode()
        style_provider.load_from_data(_css)
        if overall:
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            if old_provider is not None:
                Gtk.StyleContext.remove_provider_for_screen(
                    Gdk.Screen.get_default(), style_provider)
        else:
            widget.get_style_context().add_provider(style_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            if old_provider is not None:
                widget.get_style_context().remove_provider(old_provider)
        return style_provider

    def load_styles(self):
        font_size = str(int(self.conf['lrc-text-size']))
        px = ''
        if Gtk.MINOR_VERSION > 6:
            px = 'px'
        css = '\n'.join([
            'GtkScrolledWindow.lrc_window {',
                'transition-property: background-image;',
                'transition-duration: 1s;',
                '}',
            'GtkScale {',
                #'border-style: none;',
                'outline-color: transparent;',
                'outline-offset: 0;',
                'outline-style: none;',
                'outline-width: 0;',
                '}',
            'GtkTextView.lrc_tv {',
                'font-size: {0}{1};'.format(font_size, px),
                'color: {0};'.format(self.conf['lrc-text-color']),
                'border-radius: 0 25{0} 0 50{0};'.format(px),
                'border-width: 5{0};'.format(px),
                'background-color: {0};'.format(
                    self.conf['lrc-back-color']),
                '}',
            '.info-label {',
                'color: rgb(136, 139, 132);',
                'font-size: 9{0};'.format(px),
                '}',
            ])
        self.apply_css(self.window, css, overall=True)

    def init_status_icon(self):
        # set status_icon as class property, to keep its life
        # after function exited
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_pixbuf(self.theme['app-logo'])
        # left click
        self.status_icon.connect('activate', self.on_status_icon_activate)
        # right click
        self.status_icon.connect('popup_menu', 
                self.on_status_icon_popup_menu)

    def on_status_icon_activate(self, status_icon):
        is_visible = self.window.is_visible()
        if is_visible:
            self.window.hide()
        else:
            self.window.present()

    def on_status_icon_popup_menu(self, status_icon, event_button, 
            event_time):
        menu = Gtk.Menu()
        show_item = Gtk.MenuItem(label=_('Show App') )
        show_item.connect('activate', self.on_status_icon_show_app_activate)
        menu.append(show_item)

        pause_item = Gtk.MenuItem(label=_('Pause/Resume'))
        pause_item.connect('activate', self.on_status_icon_pause_activate)
        menu.append(pause_item)

        next_item = Gtk.MenuItem(label=_('Next Song'))
        next_item.connect('activate', self.on_status_icon_next_activate)
        menu.append(next_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        
        quit_item = Gtk.MenuItem(label=_('Quit'))
        quit_item.connect('activate', self.on_status_icon_quit_activate)
        menu.append(quit_item)

        menu.show_all()
        menu.popup(None, None,
                lambda a,b: Gtk.StatusIcon.position_menu(menu, status_icon),
                None, event_button, event_time)

    def on_status_icon_show_app_activate(self, menuitem):
        self.window.present()

    def on_status_icon_pause_activate(self, menuitem):
        self.player.play_pause()

    def on_status_icon_next_activate(self, menuitem):
        self.player.load_next()

    def on_status_icon_quit_activate(self, menuitem):
        self.quit()
