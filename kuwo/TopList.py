
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class TopList(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

    def first(self):
        if self.first_show:
            return
        self.first_show = True
        app = self.app

        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)
        button_home = Gtk.Button(_('TopList'))
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, int, int,
                int)
        control_box = Widgets.ControlBox(self.liststore_songs, app)
        self.buttonbox.pack_end(control_box, False, False, 0)

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
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        self.scrolled_songs.add(treeview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_songs.hide()

        nid = 2
        page = 0
        nodes, total_pages = Net.get_nodes(nid, page)
        if total_pages == 0:
            return
        i = 0
        for node in nodes:
            self.liststore_nodes.append([
                self.app.theme['anonymous'],
                Widgets.unescape_html(node['name']),
                int(node['sourceid']),
                Widgets.unescape_html(node['info']),
                Widgets.set_tooltip_with_song_tips(node['name'],
                    node['tips']),
                ])
            Net.update_toplist_node_logo(self.liststore_nodes, i, 0, 
                    node['pic'])
            i += 1

    def on_button_home_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

    def on_iconview_nodes_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.buttonbox.show_all()
        self.label.set_label(model[path][1])
        self.app.playlist.advise_new_playlist_name(model[path][1])
        self.show_toplist_songs(model[path][2])

    def show_toplist_songs(self, nid):
        self.scrolled_nodes.hide()
        self.scrolled_songs.show_all()

        songs = Net.get_toplist_songs(nid)
        if songs is None:
            print('Error, failed to get toplist songs')
            return
        self.liststore_songs.clear()
        for song in songs:
            self.liststore_songs.append([True,
                song['name'], 
                song['artist'],
                song['album'],
                int(song['id']), 
                int(song['artistid']),
                int(song['albumid']), ])
