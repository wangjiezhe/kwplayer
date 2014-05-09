
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import os
import re
import time
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GdkX11
from gi.repository import Gtk

from kuwo import Config
_ = Config._

LRC_WINDOW, MV_WINDOW = 0, 1

def list_to_time(time_tags):
    mm, ss, ml = time_tags
    if ml is None:
        curr_time = int(mm) * 60 + int(ss)
    else:
        curr_time = int(mm) * 60 + int(ss) + float(ml)
    return int(curr_time * 10 ** 9)

def lrc_parser(lrc_txt):
    lines = lrc_txt.split('\n')
    lrc_obj = [(-4, ''), (-3, ''), (-2, ''), ]

    reg_time = re.compile('\[([0-9]{2}):([0-9]{2})(\.[0-9]{1,3})?\]')
    for line in lines:
        offset = 0
        match = reg_time.match(line)
        tags = []
        while match:
            time = list_to_time(match.groups())
            tags.append(time)
            offset = match.end()
            match = reg_time.match(line, offset)
        content = line[offset:]
        for tag in tags:
            lrc_obj.append((tag, content))
    last_time = lrc_obj[-1][0]
    for i in range(last_time, last_time * 2 + 5, last_time // 4 + 1):
        lrc_obj.append((i, '', ))
    return sorted(lrc_obj)

class Lrc(Gtk.Notebook):
    '''Lyrics tab in notebook.'''

    title = _('Lyrics')

    def __init__(self, app):
        super().__init__()
        self.set_show_tabs(False)
        self.app = app
        self.lrc_obj = None
        self.lrc_default_background = os.path.join(
                Config.THEME_DIR, 'lrc-background.jpg')
        self.lrc_background = None
        self.old_provider = None

        # lyrics window
        self.lrc_window = Gtk.ScrolledWindow()
        self.lrc_window.get_style_context().add_class('lrc_window')
        self.append_page(self.lrc_window, Gtk.Label.new('Lrc'))

        self.lrc_buf = Gtk.TextBuffer()
        self.lrc_buf.set_text('')
        fore_rgba = Gdk.RGBA()
        fore_rgba.parse(app.conf['lrc-highlighted-text-color'])
        font_size = app.conf['lrc-highlighted-text-size']
        # Need to use size_points, not size property
        self.highlighted_tag = self.lrc_buf.create_tag(
                size_points=font_size, foreground_rgba=fore_rgba)

        self.lrc_tv = Gtk.TextView(buffer=self.lrc_buf)
        self.lrc_tv.get_style_context().add_class('lrc_tv')
        self.lrc_tv.props.editable = False
        self.lrc_tv.props.margin_top = 15
        self.lrc_tv.props.margin_right = 35
        self.lrc_tv.props.margin_bottom = 15
        self.lrc_tv.props.margin_left = 35
        self.lrc_tv.props.cursor_visible = False
        self.lrc_tv.props.justification = Gtk.Justification.CENTER
        self.lrc_tv.props.pixels_above_lines = 10
        self.lrc_tv.connect(
                'button-press-event', self.on_lrc_tv_button_pressed)
        self.lrc_window.add(self.lrc_tv)

        # mv window
        mv_win_wrap = Gtk.ScrolledWindow()
        self.append_page(mv_win_wrap, Gtk.Label.new('MV'))
        self.mv_window = Gtk.DrawingArea()
        self.mv_window.connect('draw', self.on_mv_window_redraw)
        mv_win_wrap.add(self.mv_window)

        self.update_background(self.lrc_default_background)

    def after_init(self):
        pass

    def first(self):
        pass

    def on_lrc_tv_button_pressed(self, widget, event):
        if event.button == 3:
            return True

    def set_lrc(self, lrc_txt):
        self.update_background(self.lrc_default_background)
        self.old_line_num = 1
        self.old_line_iter = None
        self.old_timestamp = -5
        if not lrc_txt:
            print('Failed to get lrc')
            self.lrc_buf.set_text(_('No lrc available'))
            self.lrc_obj = None
            return
        self.lrc_obj = lrc_parser(lrc_txt)
        self.lrc_content = [l[1] for l in self.lrc_obj]

        self.lrc_buf.remove_all_tags(
                self.lrc_buf.get_start_iter(),
                self.lrc_buf.get_end_iter())
        self.lrc_buf.set_text('\n'.join(self.lrc_content))
        #self.sync_lrc(0)
        self.lrc_window.get_vadjustment().set_value(0)

    def sync_lrc(self, timestamp):
        if not self.lrc_obj or len(self.lrc_obj) <= self.old_line_num + 1:
            return
        # current line, do nothing
        if (self.lrc_obj[self.old_line_num][0] < timestamp and
            timestamp < self.lrc_obj[self.old_line_num + 1][0]):
            return

        line_num = self.old_line_num + 1
        # remove old highlighted tags
        if self.old_line_num >= 0 and self.old_line_iter:
            self.lrc_buf.remove_tag(
                    self.highlighted_tag, *self.old_line_iter)

        # backward seeking
        if timestamp < self.old_timestamp:
            while timestamp < self.lrc_obj[line_num][0]:
                line_num -= 1
        else:
        # forward seeking
            while (len(self.lrc_obj) > line_num and
                   timestamp > self.lrc_obj[line_num][0]):
                line_num += 1
        line_num -= 1

        iter_start = self.lrc_buf.get_iter_at_line(line_num)
        iter_end = self.lrc_buf.get_iter_at_line(line_num+1)
        self.lrc_buf.apply_tag(self.highlighted_tag, iter_start, iter_end)
        self.lrc_tv.scroll_to_iter(iter_start, 0, True, 0, 0.5)
        self.old_line_iter = (iter_start, iter_end)
        self.old_line_num = line_num
        self.old_timestamp = timestamp

    def show_mv(self):
        self.set_current_page(MV_WINDOW)
        Gdk.Window.process_all_updates()
        self.mv_window.realize()
        self.xid = self.mv_window.get_property('window').get_xid()

    def show_music(self):
        self.set_current_page(LRC_WINDOW)

    # styles
    def update_background(self, filepath):
        if filepath is None or filepath == self.lrc_background:
            return
        if os.path.exists(filepath):
            self.lrc_background = filepath
        else:
            self.lrc_background = self.lrc_default_background
        css = '\n'.join([
            'GtkScrolledWindow.lrc_window {',
                "background-image: url('{0}');".format(self.lrc_background),
            '}',
            ])
        new_provider = self.app.apply_css(
                self.lrc_window, css, old_provider=self.old_provider)
        self.old_provider = new_provider

    def update_highlighted_tag(self):
        fore_rgba = Gdk.RGBA()
        fore_rgba.parse(self.app.conf['lrc-highlighted-text-color'])
        self.highlighted_tag.props.size_points = \
                self.app.conf['lrc-highlighted-text-size']
        self.highlighted_tag.props.foreground_rgba = fore_rgba

    def on_mv_window_redraw(self, *args):
        if self.app.player.get_fullscreen():
            self.app.player.playbin.expose_fullscreen()
        else:
            self.app.player.playbin.expose()
