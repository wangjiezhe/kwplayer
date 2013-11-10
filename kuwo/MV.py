
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class MV(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

    def first(self):
        if self.first_show:
            return
        self.first_show = True
        app = self.app
        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)
        button_home = Gtk.Button(_('MV'))
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # pic, name, artist, album, rid, artistid, albumid, tooltip
        self.liststore_songs = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, str, str, int, int, int, str)
        self.mv_control_box = Widgets.MVControlBox(self.liststore_songs,
                self.app)
        self.buttonbox.pack_end(self.mv_control_box, False, False, 0)

        self.scrolled_nodes = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_nodes, True, True, 0)
        # logo, name, nid, info, tooltip
        self.liststore_nodes = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int, str, str)
        iconview_nodes = Widgets.IconView(self.liststore_nodes, tooltip=4)
        iconview_nodes.connect('item_activated', 
                self.on_iconview_nodes_item_activated)
        self.scrolled_nodes.add(iconview_nodes)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)
        iconview_songs = Widgets.IconView(self.liststore_songs,
                info_pos=2, tooltip=7)
        iconview_songs.connect('item_activated', 
                self.on_iconview_songs_item_activated)
        self.scrolled_songs.add(iconview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_songs.hide()

        nid = 3
        nodes_wrap = Net.get_index_nodes(nid)
        if not nodes_wrap:
            return
        nodes = nodes_wrap['child']
        self.liststore_nodes.clear()
        i = 0
        for node in nodes:
            self.liststore_nodes.append([
                self.app.theme['anonymous'],
                Widgets.unescape_html(node['disname']),
                int(node['sourceid']),
                Widgets.unescape_html(node['info']),
                Widgets.set_tooltip(node['disname'], node['info']),
                ])
            Net.update_liststore_image(self.liststore_nodes, i, 0,
                    node['pic'])
            i += 1

    def on_iconview_nodes_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.buttonbox.show_all()
        self.label.set_label(model[path][1])
        self.scrolled_nodes.hide()
        self.scrolled_songs.show_all()
        self.curr_node_id = model[path][2]
        self.append_songs(init=True)

    def append_songs(self, init=False):
        def _append_songs(songs_args, error=None):
            songs, self.songs_total = songs_args
            if self.songs_total == 0:
                return
            i = len(self.liststore_songs)
            for song in songs:
                self.liststore_songs.append([
                    self.app.theme['anonymous'],
                    song['name'],
                    song['artist'],
                    song['album'],
                    int(song['id']),
                    int(song['artistid']), 
                    int(song['albumid']),
                    Widgets.set_tooltip(song['name'], song['artist']),
                    ])
                Net.update_mv_image(self.liststore_songs, i, 0,
                        song['mvpic'])
                i += 1
            self.songs_page += 1
            if self.songs_page < self.songs_total - 1:
                self.append_songs()

        if init:
            self.app.playlist.advise_new_playlist_name(
                    self.label.get_text())
            self.songs_page = 0
            self.liststore_songs.clear()
        Net.async_call(Net.get_mv_songs, _append_songs, 
                self.curr_node_id, self.songs_page)

    def on_iconview_songs_item_activated(self, iconview, path):
        model = iconview.get_model()
        song = Widgets.song_row_to_dict(model[path])
        self.app.popup_page(self.app.lrc.app_page)
        self.app.playlist.play_song(song, use_mv=True)

    def on_button_home_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()
