# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


'''
用于显示桌面歌词
'''

import json
import os
import sys

import cairo
from gi.repository import Gdk
from gi.repository import Gtk

from kuwo import Config
_ = Config._
from kuwo import Widgets
from kuwo.log import logger


class OSDLrc(Gtk.Window):

    def __init__(self, app):
        super().__init__(self, type=Gtk.WindowType.POPUP)
        self.props.decorated = False
        self.props.opacity = 0
        self.props.resizable = False
        self.app = app

        self.style_types = {
            'default': _('Default'),
        }
        self.set_name('default')
        self.has_shown = False

        # set main window opacity
        screen = self.get_screen()
        self.root_window = screen.get_root_window()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            self.set_app_paintable(True)

        # 鼠标点击拖放事件
        self.add_events(Gdk.EventType.BUTTON_PRESS |
                        Gdk.EventType.BUTTON_RELEASE |
                        Gdk.EventType.MOTION_NOTIFY)
        self.mouse_pressed = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(box)

        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        self.toolbar.set_show_arrow(False)
        self.toolbar.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        box.pack_start(self.toolbar, False, False, 0)

        prev_button = Gtk.ToolButton()
        prev_button.set_label(_('Previous'))
        prev_button.set_icon_name('media-skip-backward-symbolic')
        prev_button.connect('clicked', self.on_prev_button_clicked)
        self.toolbar.insert(prev_button, 0)

        self.play_button = Gtk.ToolButton()
        self.toolbar.insert(self.play_button, 1)

        next_button = Gtk.ToolButton()
        next_button.set_label(_('Next'))
        next_button.set_icon_name('media-skip-forward-symbolic')
        next_button.connect('clicked', self.on_next_button_clicked)
        self.toolbar.insert(next_button, 2)

        sep_item = Gtk.SeparatorToolItem()
        self.toolbar.insert(sep_item, 3)

        zoom_in_button = Gtk.ToolButton()
        zoom_in_button.set_label(_('Zoom In'))
        zoom_in_button.set_icon_name('zoom-in-symbolic')
        zoom_in_button.connect('clicked', self.on_zoom_in_button_clicked)
        self.toolbar.insert(zoom_in_button, 4)

        zoom_out_button = Gtk.ToolButton()
        zoom_out_button.set_label(_('Zoom Out'))
        zoom_out_button.set_icon_name('zoom-out-symbolic')
        zoom_out_button.connect('clicked', self.on_zoom_out_button_clicked)
        self.toolbar.insert(zoom_out_button, 5)

        self.color_menu = Gtk.Menu()
        for name in self.style_types:
            menu_item = Gtk.MenuItem()
            menu_item.set_label(self.style_types[name])
            menu_item.connect('activate', self.on_color_menu_item_activate,
                              name)
            self.color_menu.append(menu_item)

        color_tool_item = Gtk.ToolItem()
        self.toolbar.insert(color_tool_item, 6)
        if Config.GTK_LE_36:
            color_button = Gtk.Button()
            color_button.connect('clicked', self.on_color_button_clicked)
        else:
            color_button = Gtk.MenuButton()
            color_button.set_popup(self.color_menu)
            color_button.set_always_show_image(True)
        color_button.props.relief = Gtk.ReliefStyle.NONE
        color_image = Gtk.Image()
        color_image.set_from_icon_name('preferences-color-symbolic',
                                       Gtk.IconSize.LARGE_TOOLBAR)
        color_button.set_image(color_image)
        self.color_menu.show_all()
        color_tool_item.add(color_button)

        lock_button = Gtk.ToolButton()
        lock_button.set_label(_('Lock'))
        lock_button.set_icon_name('lock')
        lock_button.connect('clicked', self.on_lock_button_clicked)
        self.toolbar.insert(lock_button, 7)

        close_button = Gtk.ToolButton()
        close_button.set_label(_('Close'))
        close_button.set_icon_name('window-close-symbolic')
        close_button.connect('clicked', self.on_close_button_clicked)
        self.toolbar.insert(close_button, 8)

        self.da = Gtk.DrawingArea()
        self.da.set_size_request(400, 200)
        box.pack_start(self.da, False, False, 0)

        img = Gtk.Image.new_from_file('/tmp/fuck.png')
        box.pack_start(img, False, False, 0)

        with open(Config.OSD_STYLE) as fh:
            css = fh.read()
            Widgets.apply_css(self, css)

        # 切换窗口显隐动作
        self.show_window_action = Gtk.ToggleAction('show-window-action',
                _('Show OSD Window'), _('Show OSD lyric window'), None)
        self.show_window_action.set_icon_name(
                'accessories-text-editor-symbolic')
        self.show_window_action.connect('toggled',
                self.on_show_window_action_toggled)

        # 切换窗口锁定状态
        if self.app.conf['osd-locked']:
            self.lock_window_action = Gtk.ToggleAction('lock-window-action',
                    _('UnLock OSD Window'), _('UnLock OSD lyric window'), None)
            self.lock_window_action.set_active(True)
        else:
            self.lock_window_action = Gtk.ToggleAction('lock-window-action',
                    _('Lock OSD Window'), _('Lock OSD lyric window'), None)
            self.lock_window_action.set_active(False)
        self.lock_window_action.set_icon_name('lock')
        self.lock_window_action.set_sensitive(self.app.conf['osd-show'])
        self.lock_window_action.connect('toggled',
                                        self.on_lock_window_action_toggled)

    def after_init(self):
        if self.app.conf['osd-show']:
            self.show_window_action.set_active(True)
        self.play_button.props.related_action = self.app.player.playback_action

    def reload(self):
        '''重新设定属性, 然后重绘'''
        if self.app.conf['osd-locked']:
            self.toolbar.hide()
            region = cairo.Region()
            gdk_window = self.get_window()
            if not gdk_window:
                logger.warn('OSDLrc.reload(), gdk_window is None')
                return
            gdk_window.input_shape_combine_region(region, 0, 0)
        else:
            self.toolbar.show_all()
            self.app.conf['osd-toolbar-y'] = self.toolbar.get_allocated_height()
            self.input_shape_combine_region(None)
        self.resize_window()

    def show_window(self, show):
        '''是否显示歌词窗口'''
        self.app.conf['osd-show'] = show
        if show:
            if self.has_shown:
                self.present()
            else:
                self.has_shown = True
                self.show_all()
                if self.app.conf['osd-locked']:
                    self.toolbar.hide()
            self.reload()
        else:
            self.hide()

    def resize_window(self):
        if self.app.conf['osd-locked']:
            self.move(self.app.conf['osd-x'],
                      self.app.conf['osd-y'] + self.app.conf['osd-toolbar-y'])
        else:
            self.move(self.app.conf['osd-x'], self.app.conf['osd-y'])

    def lock_window(self, locked):
        if not self.app.conf['osd-show']:
            return
        self.app.conf['osd-locked'] = locked
        mapped = self.get_mapped()
        realized = self.get_realized()
        if mapped:
            self.unmap()
        if realized:
            self.unrealize()
        if locked:
            self.props.type_hint = Gdk.WindowTypeHint.DOCK
        else:
            self.props.type_hint = Gdk.WindowTypeHint.NORMAL
        if realized:
            self.realize()
        if mapped:
            self.map()
            self.queue_resize()
        self.reload()

    def on_prev_button_clicked(self, button):
        self.app.player.load_prev()

    def on_next_button_clicked(self, button):
        self.app.player.load_next()

    def on_zoom_in_button_clicked(self, button):
        pass

    def on_zoom_out_button_clicked(self, button):
        pass

    def on_color_menu_item_activate(self, menu_item, name):
        self.set_name(name)

    def on_color_button_clicked(self, button):
        self.color_menu.popup(None, None, None, None, 1,
                              Gtk.get_current_event_time())

    def on_lock_button_clicked(self, button):
        self.lock_window_action.set_active(True)

    def on_close_button_clicked(self, button):
        self.show_window_action.set_active(False)

    def on_show_window_action_toggled(self, action):
        status = action.get_active()
        self.show_window(status)
        self.lock_window_action.set_sensitive(status)
        if status:
            action.set_label(_('Hide OSD Window'))
        else:
            action.set_label(_('Show OSD Window'))

    def on_lock_window_action_toggled(self, action):
        if not self.app.conf['osd-show']:
            return
        self.lock_window(action.get_active())
        if action.get_active():
            action.set_label(_('UnLock OSD Window'))
        else:
            action.set_label(_('Lock OSD Window'))

    # 以下三个事件用于处理窗口拖放移动
    def do_button_press_event(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.mouse_pressed = True
        cursor = Gdk.Cursor(Gdk.CursorType.FLEUR)
        self.root_window.set_cursor(cursor)

    def do_button_release_event(self, event):
        cursor = Gdk.Cursor(Gdk.CursorType.ARROW)
        self.root_window.set_cursor(cursor)
        if self.mouse_pressed:
            self.app.conf['osd-x'], self.app.conf['osd-y'] = self.get_position()
            self.mouse_pressed = False

    def do_motion_notify_event(self, event):
        if not self.mouse_pressed:
            return
        x = int(event.x_root - self.start_x)
        y = int(event.y_root - self.start_y)
        self.move(x, y)
