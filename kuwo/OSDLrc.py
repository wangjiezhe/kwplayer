# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


'''
用于显示桌面歌词
'''

import json
import os
import sys
import time
import traceback

import cairo
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from kuwo import Config
_ = Config._
from kuwo import Widgets
from kuwo.log import logger

ACTIVATE = 'activated'
SIZE_MAX = 72
SIZE_MIN = 4
HIDE_TOOLBAR_AFTER = 2000  # 2 secs

class RightLabel(Gtk.Label):

    def __init__(self, label):
        super().__init__(label)
        self.props.halign = Gtk.Align.END
        self.props.xalign = 1


class OSDLrc(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app.app, type=Gtk.WindowType.POPUP)
        self.props.decorated = False
        self.props.resizable = False
        self.app = app

        self.has_shown = False
        self.old_provider = None

        # set main window opacity
        screen = self.get_screen()
        self.root_window = screen.get_root_window()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(box)

        self.da = Gtk.Label()
        self.da.old_provider = None
        self.da.props.xalign = 0
        box.pack_start(self.da, False, False, 0)
        self.da2 = Gtk.Label()
        self.da2.old_provider = None
        #self.da2.props.justify = Gtk.Justification.RIGHT
        #self.da2.props.halign = Gtk.Align.END
        #self.da2.props.xalign = 1
        self.da2.props.xalign = 0
        box.pack_start(self.da2, False, False, 0)

        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        #self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_TOOLBAR)
        self.toolbar.set_show_arrow(False)
        self.toolbar.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        box.pack_start(self.toolbar, False, False, 0)

        # 鼠标点击拖放事件
        self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        #Gdk.EventMask.BUTTON_MOTION_MASK |
                        #Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.mouse_pressed = False

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

        zoom_in_button = Gtk.ToolButton()
        zoom_in_button.set_label(_('Zoom In'))
        zoom_in_button.set_icon_name('zoom-in-symbolic')
        zoom_in_button.connect('clicked', self.on_zoom_in_button_clicked)
        self.toolbar.insert(zoom_in_button, 3)

        zoom_out_button = Gtk.ToolButton()
        zoom_out_button.set_label(_('Zoom Out'))
        zoom_out_button.set_icon_name('zoom-out-symbolic')
        zoom_out_button.connect('clicked', self.on_zoom_out_button_clicked)
        self.toolbar.insert(zoom_out_button, 4)

        color_button = Gtk.ToolButton()
        color_button.set_label(_('Styles'))
        color_button.set_icon_name('preferences-system-symbolic')
        color_button.connect('clicked', self.on_color_button_clicked)
        self.toolbar.insert(color_button, 5)

        lock_button = Gtk.ToolButton()
        lock_button.set_label(_('Lock'))
        lock_button.set_icon_name('lock')
        lock_button.connect('clicked', self.on_lock_button_clicked)
        self.toolbar.insert(lock_button, 6)

        close_button = Gtk.ToolButton()
        close_button.set_label(_('Close'))
        close_button.set_icon_name('window-close-symbolic')
        close_button.connect('clicked', self.on_close_button_clicked)
        self.toolbar.insert(close_button, 7)

        # 切换窗口显隐动作
        self.show_window_action = Gtk.ToggleAction('show-window-action',
                _('Show OSD Window'), _('Show OSD lyric'), None)
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
        self.update_style()
        if self.app.conf['osd-show']:
            self.show_window_action.set_active(True)
        self.play_button.props.related_action = self.app.player.playback_action
        self.arrow_cursor = Gdk.Cursor(Gdk.CursorType.ARROW)
        self.fleur_cursor = Gdk.Cursor(Gdk.CursorType.FLEUR)

    def update_style(self):
        conf = self.app.conf
        if Config.GTK_LE_36:
            css = '\n'.join([
                'GtkWindow {',
                    'background-color:{0};'.format(
                        conf['osd-background-color']),
                '}',
                '.activated {',
                    'color: {0};'.format(conf['osd-activated-color']),
                    'font-size: {0};'.format(conf['osd-activated-size']),
                '}',
                'GtkLabel {',
                    'color: {0};'.format(conf['osd-inactivated-color']),
                    'font-size: {0};'.format(conf['osd-inactivated-size']),
                '}',
            ])
        else:
            css = '\n'.join([
                'GtkWindow {',
                    'background-color:{0};'.format(
                        conf['osd-background-color']),
                '}',
                '.activated {',
                    'color: {0};'.format(conf['osd-activated-color']),
                    'font-size: {0}px;'.format(conf['osd-activated-size']),
                '}',
                'GtkLabel {',
                    'color: {0};'.format(conf['osd-inactivated-color']),
                    'font-size: {0}px;'.format(conf['osd-inactivated-size']),
                    'transition-property: font-size;',
                    'transition: 200ms ease-in;',
                '}',
            ])
        self.old_provider = Widgets.apply_css(self, css,
                old_provider=self.old_provider)
        self.da.old_provider = Widgets.apply_css(self.da, css,
                old_provider=self.da.old_provider)
        self.da2.old_provider = Widgets.apply_css(self.da2, css,
                old_provider=self.da2.old_provider)

    def set_lrc(self, lrc_obj):
        self.lrc_obj = lrc_obj
        if not lrc_obj:
            self.da.set_text('No lyric available')

    def sync_lrc(self, line_num):
        '''同步歌词'''
        if not self.lrc_obj or line_num >= len(self.lrc_obj):
            return
        elif line_num == 0:
            self.da.set_text(self.lrc_obj[0][1])
            self.da2.set_text(self.lrc_obj[1][1])
            self.da.get_style_context().add_class(ACTIVATE)
        elif line_num % 2 == 1:
            next_line = line_num + 1
            if next_line < len(self.lrc_obj):
                self.da.set_text(self.lrc_obj[next_line][1])
            self.da.get_style_context().remove_class(ACTIVATE)
            self.da2.set_text(self.lrc_obj[line_num][1])
            self.da2.get_style_context().add_class(ACTIVATE)
        else:
            next_line = line_num + 1
            if next_line < len(self.lrc_obj):
                self.da2.set_text(self.lrc_obj[next_line][1])
            self.da2.get_style_context().remove_class(ACTIVATE)
            self.da.set_text(self.lrc_obj[line_num][1])
            self.da.get_style_context().add_class(ACTIVATE)

    def reload(self):
        '''重新设定属性, 然后重绘'''
        if self.app.conf['osd-locked']:
            self.toolbar.hide()
            try:
                region = cairo.Region()
            except AttributeError:
                print('Error: cairo too old, cairo.Region missing')
                logger.error(traceback.format_exc())
                return
            gdk_window = self.get_window()
            if not gdk_window:
                logger.warn('OSDLrc.reload(), gdk_window is None')
                return
            gdk_window.input_shape_combine_region(region, 0, 0)
        else:
            self.toolbar.show_all()
            self.app.conf['osd-toolbar-y'] = self.toolbar.get_allocated_height()
            self.auto_hide_toolbar()
            self.input_shape_combine_region(None)
        self.move(self.app.conf['osd-x'], self.app.conf['osd-y'])

    def auto_hide_toolbar(self):
        def hide_toolbar(timestamp):
            if timestamp == self.toolbar.timestamp:
                self.toolbar.timestamp = 0
                self.toolbar.hide()

        if self.toolbar.get_visible():
            timestamp = time.time()
            self.toolbar.timestamp = timestamp
            GLib.timeout_add(HIDE_TOOLBAR_AFTER, hide_toolbar, timestamp)

    def show_window(self, show):
        '''是否显示歌词窗口'''
        self.app.conf['osd-show'] = show
        if show:
            if self.has_shown:
                self.present()
            else:
                self.has_shown = True
                self.show_all()
            self.reload()
        else:
            self.hide()

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
            # Note that gdk_window_set_type_hint() must be set before the
            # gdk window is mapped
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
        if self.app.conf['osd-inactivated-size'] < SIZE_MAX:
            self.app.conf['osd-inactivated-size'] += 1
        if self.app.conf['osd-activated-size'] < SIZE_MAX:
            self.app.conf['osd-activated-size'] += 1
        self.update_style()

    def on_zoom_out_button_clicked(self, button):
        if self.app.conf['osd-inactivated-size'] > SIZE_MIN:
            self.app.conf['osd-inactivated-size'] -= 1
        if self.app.conf['osd-activated-size'] > SIZE_MIN:
            self.app.conf['osd-activated-size'] -= 1
        self.update_style()

    def on_color_button_clicked(self, button):
        def on_background_color_set(color_button):
            color_rgba = color_button.get_rgba()
            if color_rgba.alpha == 1:
                color_rgba.alpha = 0.999
            self.app.conf['osd-background-color'] = color_rgba.to_string()
            self.update_style()

        def on_inactivated_color_set(color_button):
            color_rgba = color_button.get_rgba()
            if color_rgba.alpha == 1:
                color_rgba.alpha = 0.999
            self.app.conf['osd-inactivated-color'] = color_rgba.to_string()
            self.update_style()

        def on_activated_color_set(color_button):
            color_rgba = color_button.get_rgba()
            if color_rgba.alpha == 1:
                color_rgba.alpha = 0.999
            self.app.conf['osd-activated-color'] = color_rgba.to_string()
            self.update_style()

        def on_inactivated_size_changed(spin):
            self.app.conf['osd-inactivated-size'] = spin.get_value()
            self.update_style()

        def on_activated_size_changed(spin):
            self.app.conf['osd-activated-size'] = spin.get_value()
            self.update_style()

        dialog = Gtk.Dialog(_('OSD Styles'), self, 0,
                            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        dialog.set_modal(False)
        dialog.set_default_size(480, 320)
        dialog.set_border_width(5)
        box = dialog.get_content_area()

        grid = Gtk.Grid()
        grid.props.halign = Gtk.Align.CENTER
        grid.props.column_spacing = 15
        grid.props.row_spacing = 10
        box.pack_start(grid, False, False, 0)

        grid.attach(RightLabel(_('Background Color:')), 0, 0, 1, 1)
        rgba = Gdk.RGBA()
        rgba.parse(self.app.conf['osd-background-color'])
        background_color = Gtk.ColorButton.new_with_rgba(rgba)
        background_color.props.use_alpha = True
        background_color.connect('color-set', on_background_color_set)
        grid.attach(background_color, 1, 0, 1, 1)

        grid.attach(RightLabel(_('Inativated Text Color:')), 0, 1, 1, 1)
        rgba.parse(self.app.conf['osd-inactivated-color'])
        inactivated_color = Gtk.ColorButton.new_with_rgba(rgba)
        inactivated_color.props.use_alpha = True
        inactivated_color.connect('color-set', on_inactivated_color_set)
        grid.attach(inactivated_color, 1, 1, 1, 1)

        grid.attach(RightLabel(_('Activated Text Color:')), 0, 2, 1, 1)
        rgba.parse(self.app.conf['osd-activated-color'])
        activated_color = Gtk.ColorButton.new_with_rgba(rgba)
        activated_color.props.use_alpha = True
        activated_color.connect('color-set', on_activated_color_set)
        grid.attach(activated_color, 1, 2, 1, 1)

        grid.attach(RightLabel(_('Inactivated Font Size:')), 0, 3, 1, 1)
        inactivated_size = Gtk.SpinButton.new_with_range(SIZE_MIN, SIZE_MAX, 1)
        inactivated_size.set_value(self.app.conf['osd-inactivated-size'])
        inactivated_size.connect('value-changed', on_inactivated_size_changed)
        grid.attach(inactivated_size, 1, 3, 1, 1)

        grid.attach(RightLabel(_('Activated Font Size:')), 0, 4, 1, 1)
        activated_size = Gtk.SpinButton.new_with_range(SIZE_MIN, SIZE_MAX, 1)
        activated_size.set_value(self.app.conf['osd-activated-size'])
        activated_size.connect('value-changed', on_activated_size_changed)
        grid.attach(activated_size, 1, 4, 1, 1)

        box.show_all()
        dialog.run()
        dialog.destroy()

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
            action.set_tooltip(_('Hide OSD Window'))
        else:
            action.set_label(_('Show OSD Window'))
            action.set_tooltip(_('Show OSD Window'))

    def on_lock_window_action_toggled(self, action):
        if not self.app.conf['osd-show']:
            return
        self.lock_window(action.get_active())
        if action.get_active():
            action.set_label(_('UnLock OSD Window'))
        else:
            action.set_label(_('Lock OSD Window'))

    # 以下两个事件用于自动隐去工具栏
    def do_enter_notify_event(self, event):
        self.toolbar.show_all()

    def do_leave_notify_event(self, event):
        self.auto_hide_toolbar()

    # 以下事件用于处理窗口拖放移动
    def do_button_press_event(self, event):
        self.mouse_pressed = True
        self.start_x, self.start_y = event.x, event.y
        self.get_window().set_cursor(self.fleur_cursor)

    def do_button_release_event(self, event):
        self.app.conf['osd-x'], self.app.conf['osd-y'] = self.get_position()
        self.mouse_pressed = False
        self.get_window().set_cursor(self.arrow_cursor)

    def do_motion_notify_event(self, event):
        if not self.mouse_pressed:
            return
        x = int(event.x_root - self.start_x)
        y = int(event.y_root - self.start_y)
        self.move(x, y)
