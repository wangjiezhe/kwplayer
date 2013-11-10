
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class Themes(Gtk.Box):
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

        self.button_main = Gtk.Button(_('Themes'))
        self.button_main.connect('clicked', self.on_button_main_clicked)
        self.buttonbox.pack_start(self.button_main, False, False, 0)

        self.button_sub = Gtk.Button('')
        self.button_sub.connect('clicked', self.on_button_sub_clicked)
        self.buttonbox.pack_start(self.button_sub, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, 
                int, int, int)
        self.control_box = Widgets.ControlBox(self.liststore_songs, app)
        self.buttonbox.pack_end(self.control_box, False, False, 0)

        self.scrolled_main = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_main, True, True, 0)
        # pic, name, id, info(num of lists), tooltip
        self.liststore_main = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int, str, str)
        iconview_main = Widgets.IconView(self.liststore_main, tooltip=4)
        iconview_main.connect('item_activated', 
                self.on_iconview_main_item_activated)
        self.scrolled_main.add(iconview_main)

        self.scrolled_sub = Gtk.ScrolledWindow()
        self.scrolled_sub.get_vadjustment().connect('value-changed',
                self.on_scrolled_sub_scrolled)
        self.pack_start(self.scrolled_sub, True, True, 0)
        # pic, name, sourceid, info(num of lists), tooltip
        self.liststore_sub = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int, str, str)
        iconview_sub = Widgets.IconView(self.liststore_sub, tooltip=4)
        iconview_sub.connect('item_activated', 
                self.on_iconview_sub_item_activated)
        self.scrolled_sub.add(iconview_sub)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.scrolled_songs.get_vadjustment().connect('value-changed',
                self.on_scrolled_songs_scrolled)
        self.pack_start(self.scrolled_songs, True, True, 0)
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        self.scrolled_songs.add(treeview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_sub.hide()
        self.scrolled_songs.hide()

        nodes = Net.get_themes_main()
        if nodes is None:
            print('Failed to get nodes, do something!')
            return
        i = 0
        for node in nodes:
            self.liststore_main.append([
                self.app.theme['anonymous'],
                Widgets.unescape_html(node['name']),
                int(node['nid']),
                Widgets.unescape_html(node['info']),
                Widgets.set_tooltip(node['name'], node['info']),
                ])
            Net.update_liststore_image(self.liststore_main, i, 0, 
                    node['pic'])
            i += 1

    def on_iconview_main_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_sub_name = model[path][1]
        self.curr_sub_id = model[path][2]
        self.label.set_label(self.curr_sub_name)
        self.show_sub(init=True)

    def show_sub(self, init=False):
        if init:
            self.scrolled_main.hide()
            self.scrolled_songs.hide()
            self.buttonbox.show_all()
            self.button_sub.hide()
            self.control_box.hide()
            self.scrolled_sub.get_vadjustment().set_value(0)
            self.scrolled_sub.show_all()
            self.nodes_page = 0
            self.liststore_sub.clear()
        nodes, self.nodes_total = Net.get_nodes(self.curr_sub_id,
                self.nodes_page)
        if nodes is None:
            return
        i = len(self.liststore_sub)
        for node in nodes:
            self.liststore_sub.append([
                self.app.theme['anonymous'],
                Widgets.unescape_html(node['name']),
                int(node['sourceid']),
                Widgets.unescape_html(node['info']),
                Widgets.set_tooltip_with_song_tips(node['name'],
                    node['tips']),
                ])
            Net.update_liststore_image(self.liststore_sub, i, 0, 
                    node['pic'])
            i += 1

    def on_iconview_sub_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_list_name = model[path][1]
        self.curr_list_id = model[path][2]
        self.label.set_label(self.curr_list_name)
        self.button_sub.set_label(self.curr_sub_name)
        self.show_songs(init=True)
    
    def show_songs(self, init=False):
        if init:
            self.app.playlist.advise_new_playlist_name(
                    self.label.get_text())
            self.liststore_songs.clear()
            self.songs_page = 0
            self.scrolled_sub.hide()
            self.button_sub.show_all()
            self.control_box.show_all()
            self.scrolled_songs.get_vadjustment().set_value(0.0)
            self.scrolled_songs.show_all()

        songs, self.songs_total = Net.get_themes_songs(
                self.curr_list_id, self.songs_page)
        if songs is None:
            return
        for song in songs:
            self.liststore_songs.append([True,
                song['name'],
                song['artist'],
                song['album'],
                int(song['id']),
                int(song['artistid']), 
                int(song['albumid']), ])
    
    # buttonbox buttons
    def on_button_main_clicked(self, btn):
        self.buttonbox.hide()
        self.scrolled_sub.hide()
        self.scrolled_songs.hide()
        self.control_box.hide()
        self.scrolled_main.show_all()

    def on_button_sub_clicked(self, btn):
        self.scrolled_songs.hide()
        self.label.set_label(self.curr_sub_name)
        self.buttonbox.show_all()
        self.button_sub.hide()
        self.control_box.hide()
        self.scrolled_sub.show_all()

    def on_scrolled_sub_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.nodes_page < self.nodes_total - 1:
            self.nodes_page += 1
            self.show_sub()

    def on_scrolled_songs_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.songs_page < self.songs_total - 1:
            self.songs_page += 1
            self.show_songs()
