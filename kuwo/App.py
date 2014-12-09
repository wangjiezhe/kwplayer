
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import os
import sys
import traceback

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

from kuwo import Config
# ~/.config/kuwo and ~/.cache/kuwo need to be created at first time
Config.check_first()
_ = Config._
Notify.init(Config.APPNAME)
from kuwo.log import logger
from kuwo import Widgets
from kuwo.Artists import Artists
from kuwo.Lrc import Lrc
from kuwo.MV import MV
from kuwo.OSDLrc import OSDLrc
from kuwo.Player import Player
from kuwo.PlayList import PlayList
from kuwo.Radio import Radio
from kuwo.Search import Search
from kuwo.Shortcut import Shortcut
from kuwo.Themes import Themes
from kuwo.TopCategories import TopCategories
from kuwo.TopList import TopList
try:
    # Ubuntu Unity uses AppIndicator instead of Gtk.StatusIcon
    from gi.repository import AppIndicator3 as AppIndicator
except ImportError:
    logger.debug(traceback.format_exc())

if Gtk.MAJOR_VERSION <= 3 and Gtk.MINOR_VERSION < 10:
    GObject.threads_init()
DBUS_APP_NAME = 'org.liulang.kwplayer'


class App:

    def __init__(self):
        self.app = Gtk.Application.new(DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

    def on_app_startup(self, app):
        self.conf = Config.load_conf()
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon_theme.append_search_path(Config.ICON_PATH)

        GLib.set_application_name(Config.APPNAME)
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.set_default_icon_name(Config.NAME)
        self.window.props.hide_titlebar_when_maximized = True
        app.add_window(self.window)
        self.window.connect('check-resize', self.on_main_window_resized)
        self.window.connect('delete-event', self.on_main_window_deleted)

        self.accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.osdlrc = OSDLrc(self)
        self.notify = None
        self.init_notify()

        self.player = Player(self)
        box.pack_start(self.player, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.tab_pos = Gtk.PositionType.BOTTOM
        self.notebook.get_style_context().add_class('main_tab')
        box.pack_start(self.notebook, True, True, 0)
        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switch_page)
        self.init_status_icon()

        # load default styles when all widgets have been constructed.
        self.load_styles()

    def on_app_activate(self, app):
        self.window.show_all()
        # Make some changes after main window is shown.
        # Like hiding some unnecessory widgets.
        self.artists.after_init()
        self.player.after_init()
        self.search.after_init()
        self.shortcut = Shortcut(self.player)
        self.osdlrc.after_init()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        gdk_win = self.window.get_window()
        if gdk_win and not gdk_win.is_destroyed():
            if self.player.default_cursor:
                gdk_win.set_cursor(self.player.default_cursor)
            self.window.destroy()
        self.shortcut.quit()
        self.app.quit()

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_main_window_deleted(self, window, event):
        if self.conf['use-status-icon']:
            window.hide()
            return True
        else:
            return False

    def init_notebook(self):
        self.tab_first_show = []
        self.lrc = Lrc(self)
        self.append_page(self.lrc)

        self.playlist = PlayList(self)
        self.append_page(self.playlist)

        self.search = Search(self)
        self.append_page(self.search)

        self.toplist = TopList(self)
        self.append_page(self.toplist)

        self.radio = Radio(self)
        self.append_page(self.radio)

        self.mv = MV(self)
        self.append_page(self.mv)

        self.artists = Artists(self)
        self.append_page(self.artists)

        self.topcategories = TopCategories(self)
        self.append_page(self.topcategories)

        self.themes = Themes(self)
        self.append_page(self.themes)

    def append_page(self, widget):
        '''Append a new widget to notebook.'''
        label = Gtk.Label(widget.title)
        widget.app_page = self.notebook.append_page(widget, label)

    def popup_page(self, page):
        '''Switch to this widget in notebook.'''
        self.notebook.set_current_page(page)

    def load_styles(self):
        '''Load default CssStyle.'''
        if Config.GTK_LE_36:
            css = '\n'.join([
                'GtkScale {',
                    'outline-color: transparent;',
                    'outline-offset: 0;',
                    'outline-style: none;',
                    'outline-width: 0;',
                '}',
                'GtkTextView.lrc_tv {',
                    'font-size: {0};'.format(self.conf['lrc-text-size']),
                    'color: {0};'.format(self.conf['lrc-text-color']),
                    'border-radius: 0 25 0 50;',
                    'border-width: 5;',
                    'background-color: {0};'.format(
                        self.conf['lrc-back-color']),
                '}',
                '.info-label {',
                    'color: rgb(136, 139, 132);',
                    'font-size: 9;',
                '}',
                ])
        else:
            css = '\n'.join([
                'GtkScrolledWindow.lrc_window {',
                    'transition-property: background-image;',
                    'transition-duration: 1s;',
                '}',
                'GtkScale {',
                    'outline-color: transparent;',
                    'outline-offset: 0;',
                    'outline-style: none;',
                    'outline-width: 0;',
                '}',
                'GtkTextView.lrc_tv {',
                    'transition-property: font-size;',
                    'transition: 500ms ease-in-out;',
                    'font-size: {0}px;'.format(self.conf['lrc-text-size']),
                    'color: {0};'.format(self.conf['lrc-text-color']),
                    'border-radius: 0px 25px 0px 50px;',
                    'border-width: 5px;',
                    'background-color: {0};'.format(
                        self.conf['lrc-back-color']),
                '}',
                '.info-label {',
                    'color: rgb(136, 139, 132);',
                    'font-size: 9px;',
                '}',
                ])

        Widgets.apply_css(self.window, css, overall=True)

        settings = Gtk.Settings.get_default()
        settings.props.gtk_application_prefer_dark_theme = \
                self.conf.get('use-dark-theme', False)

    def init_status_icon(self):
        def on_status_icon_popup_menu(status_icon, event_button,
                                      event_time):
            menu.popup(None, None,
                    lambda a,b: Gtk.StatusIcon.position_menu(menu, status_icon),
                    None, event_button, event_time)

        def on_status_icon_activate(tatus_icon):
            if self.window.props.visible:
                self.window.hide()
            else:
                self.window.present()

        if not self.conf['use-status-icon']:
            return

        menu = Gtk.Menu()

        show_item = Gtk.MenuItem(_('Show App'))
        show_item.connect('activate', lambda item: self.window.present())
        menu.append(show_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)

        previous_item = Gtk.MenuItem(_('Previous Song'))
        previous_item.connect('activate', lambda item: self.player.load_prev())
        menu.append(previous_item)

        play_item = Gtk.MenuItem()
        play_item.props.related_action = self.player.playback_action
        menu.append(play_item)

        next_item = Gtk.MenuItem(_('Next Song'))
        next_item.connect('activate', lambda item: self.player.load_next())
        menu.append(next_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)

        show_osd_item = Gtk.MenuItem()
        show_osd_item.props.related_action = self.osdlrc.show_window_action
        menu.append(show_osd_item)

        lock_osd_item = Gtk.MenuItem()
        lock_osd_item.props.related_action = self.osdlrc.lock_window_action
        menu.append(lock_osd_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        
        quit_item = Gtk.MenuItem(_('Quit'))
        quit_item.connect('activate', lambda item: self.quit())
        menu.append(quit_item)

        menu.show_all()
        self.status_menu = menu

        if 'AppIndicator' in globals():
            self.status_icon = AppIndicator.Indicator.new(Config.NAME,
                    Config.NAME,
                    AppIndicator.IndicatorCategory.APPLICATION_STATUS)
            self.status_icon.set_menu(menu)
            self.status_icon.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        else: 
            self.status_icon = Gtk.StatusIcon.new_from_icon_name(Config.NAME)
            # left click
            self.status_icon.connect('activate', on_status_icon_activate)
            # right click
            self.status_icon.connect('popup_menu', on_status_icon_popup_menu)

    def on_notebook_switch_page(self, notebook, page, page_num):
        if page not in self.tab_first_show:
            page.first()
            self.tab_first_show.append(page)

    def init_notify(self):
        try:
            self.notify = Notify.Notification.new(Config.APPNAME, '',
                                                  Config.NAME)
        except Exception:
            logger.warn('App.init_notify: %s' % traceback.format_exc())
            self.notify = None

    # Open API
    def toast(self, text):
        '''在用户界面显示一个消息通知.

        可以使用系统提供的Notification工具, 也可以在窗口的最下方滚动弹出
        这个消息
        '''
        if self.notify:
            self.notify.update(Config.APPNAME, text, Config.NAME)
            self.notify.show()
