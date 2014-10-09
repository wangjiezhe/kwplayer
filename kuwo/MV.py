
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
_ = Config._
from kuwo import Net
from kuwo import Widgets
from kuwo.log import logger

class MV(Gtk.Box):
    '''MV tab in notebook.'''

    title = _('MV')

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def first(self):
        app = self.app
        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)
        button_home = Gtk.Button(_('MV'))
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # pic, name, artist, album, rid, artistid, albumid, tooltip
        self.liststore_songs = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str,
                                             str, int, int, int, str)
        self.mv_control_box = Widgets.MVControlBox(self.liststore_songs,
                                                   self.app)
        self.buttonbox.pack_end(self.mv_control_box, False, False, 0)

        self.scrolled_nodes = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_nodes, True, True, 0)
        # logo, name, nid, info, tooltip
        self.liststore_nodes = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int,
                                             str, str)
        iconview_nodes = Widgets.IconView(self.liststore_nodes, tooltip=4)
        iconview_nodes.connect('item_activated',
                               self.on_iconview_nodes_item_activated)
        self.scrolled_nodes.add(iconview_nodes)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)
        iconview_songs = Widgets.IconView(self.liststore_songs, info_pos=2,
                                          tooltip=7)
        iconview_songs.connect('item_activated',
                               self.on_iconview_songs_item_activated)
        self.scrolled_songs.add(iconview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_songs.hide()

        def _on_get_index_nodes(nodes_wrap, error=None):
            if not nodes_wrap or error:
                logger.error('MV._on_get_inex_nodes(): %s, %s' %
                             (nodes_wrap, error))
                return
            nodes = nodes_wrap['child']
            self.liststore_nodes.clear()
            urls = []
            tree_iters = []
            for node in nodes:
                tree_iter = self.liststore_nodes.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(node['disname']),
                    int(node['sourceid']),
                    Widgets.unescape(node['info']),
                    Widgets.set_tooltip(node['disname'], node['info']),
                ])
                tree_iters.append(tree_iter)
                urls.append(node['pic'])
            self.liststore_nodes.timestamp = time.time()
            Net.async_call(Net.update_liststore_images, self.liststore_nodes, 0,
                           tree_iters, urls)
        nid = 3
        Net.async_call(Net.get_index_nodes, nid, callback=_on_get_index_nodes)

    def on_iconview_nodes_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.buttonbox.show_all()
        self.label.set_label(model[path][1])
        self.scrolled_nodes.hide()
        self.scrolled_songs.show_all()
        self.curr_node_id = model[path][2]
        self.append_songs(init=True)

    def append_songs(self, init=False):
        def _on_append_songs(info, error=None):
            if error or not info or not info[0] or not info[1]:
                logger.error('append_songs():  %s, %s' % (info, error))
                return
            songs, self.songs_total = info
            urls = []
            tree_iters = []
            for song in songs:
                tree_iter = self.liststore_songs.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(song['album']),
                    int(song['id']),
                    int(song['artistid']), 
                    int(song['albumid']),
                    Widgets.set_tooltip(song['name'], song['artist']),
                ])
                tree_iters.append(tree_iter)
                urls.append(song['mvpic'])
            Net.async_call(Net.update_mv_images, self.liststore_songs, 0,
                           tree_iters, urls)
            self.songs_page += 1
            if self.songs_page < self.songs_total - 1:
                self.append_songs()

        if init:
            # reset scrollbar
            self.scrolled_songs.get_vscrollbar().set_value(0)
            self.app.playlist.advise_new_playlist_name(self.label.get_text())
            self.songs_page = 0
            self.liststore_songs.clear()
        if init or not hasattr(self.liststore_songs, 'timestamp'):
            self.liststore_songs.timestamp = time.time()
        Net.async_call(Net.get_mv_songs, self.curr_node_id, self.songs_page,
                       callback=_on_append_songs)

    def on_iconview_songs_item_activated(self, iconview, path):
        model = iconview.get_model()
        song = Widgets.song_row_to_dict(model[path])
        self.app.popup_page(self.app.lrc.app_page)
        self.app.playlist.play_song(song, use_mv=True)

    def on_button_home_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()
