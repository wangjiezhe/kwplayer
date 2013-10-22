
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
import html

from kuwo import Config
from kuwo import Widgets
from kuwo import Net

_ = Config._

class Search(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.app = app

        self.songs_tab_inited = False
        self.artists_tab_inited = False
        self.albums_tab_inited = False

        box_top = Gtk.Box(spacing=5)
        self.pack_start(box_top, False, False, 0)

        if Gtk.MINOR_VERSION < 6:
            self.search_entry = Gtk.Entry()
        else:
            self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_('Search Songs, Artists..'))
        self.search_entry.props.width_chars = 30
        self.search_entry.connect('activate', self.on_search_entry_activate)
        box_top.pack_start(self.search_entry, False, False, 20)

        self.songs_button = Widgets.ListRadioButton(_('Songs'))
        self.songs_button.connect('toggled', self.switch_notebook_page, 0)
        box_top.pack_start(self.songs_button, False, False, 0)

        self.artists_button = Widgets.ListRadioButton(_('Artists'), 
                self.songs_button)
        self.artists_button.connect('toggled', self.switch_notebook_page, 1)
        box_top.pack_start(self.artists_button, False, False, 0)

        self.albums_button = Widgets.ListRadioButton(_('Albums'), 
                self.songs_button)
        self.albums_button.connect('toggled', self.switch_notebook_page, 2)
        box_top.pack_start(self.albums_button, False, False, 0)

        # TODO: add MV and lyrics search.

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, int, int,
                int)
        self.control_box = Widgets.ControlBox(self.liststore_songs,
                app, select_all=False)
        box_top.pack_end(self.control_box, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        songs_tab = Gtk.ScrolledWindow()
        songs_tab.get_vadjustment().connect('value-changed',
                self.on_songs_tab_scrolled)
        self.notebook.append_page(songs_tab, Gtk.Label(_('Songs')))
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        songs_tab.add(treeview_songs)

        artists_tab = Gtk.ScrolledWindow()
        artists_tab.get_vadjustment().connect('value-changed',
                self.on_artists_tab_scrolled)
        self.notebook.append_page(artists_tab, Gtk.Label(_('Artists')))

        # pic, artist, artistid, country
        self.liststore_artists = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int, str)
        iconview_artists = Widgets.IconView(self.liststore_artists)
        iconview_artists.connect('item_activated',
                self.on_iconview_artists_item_activated)
        artists_tab.add(iconview_artists)

        albums_tab = Gtk.ScrolledWindow()
        albums_tab.get_vadjustment().connect('value-changed',
                self.on_albums_tab_scrolled)
        self.notebook.append_page(albums_tab, Gtk.Label(_('Albums')))

        # logo, album, albumid, artist, artistid, info
        self.liststore_albums = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int,
                str, int, str)
        iconview_albums = Widgets.IconView(self.liststore_albums, tooltip=5)
        iconview_albums.connect('item_activated',
                self.on_iconview_albums_item_activated)
        albums_tab.add(iconview_albums)

    def after_init(self):
        self.control_box.hide()

    def first(self):
        pass

    def switch_notebook_page(self, radiobtn, page):
        state = radiobtn.get_active()
        if not state:
            return
        self.notebook.set_current_page(page)
        if page == 0 and self.songs_tab_inited:
            self.control_box.show_all()
        else:
            self.control_box.hide()

        if (page == 0 and not self.songs_tab_inited) or \
           (page == 1 and not self.artists_tab_inited) or \
           (page == 2 and not self.artists_tab_inited):
            self.on_search_entry_activate(None, False)

    def on_search_entry_activate(self, search_entry, reset_status=True):
        if len(self.search_entry.get_text()) == 0:
            return
        if reset_status:
            self.reset_search_status()
        page = self.notebook.get_current_page()
        if page == 0:
            self.control_box.show_all()
            self.songs_tab_inited = True
            self.show_songs(reset_status)
        elif page == 1:
            self.artists_tab_inited = True
            self.show_artists(reset_status)
        elif page == 2:
            self.albums_tab_inited = True
            self.show_albums(reset_status)

    def show_songs(self, reset_status=False):
        def _append_songs(songs_args, error=None):
            songs, hit, self.songs_total = songs_args
            if not songs or hit == 0:
                if reset_status:
                    self.songs_button.set_label(
                            '{0} (0)'.format(_('Songs')))
                return
            self.songs_button.set_label(
                    '{0} ({1})'.format(_('Songs'), hit))
            for song in songs:
                self.liststore_songs.append([False,
                    song['SONGNAME'],
                    song['ARTIST'], song['ALBUM'],
                    int(song['MUSICRID'][6:]),
                    int(song['ARTISTID']),
                    int(song['ALBUMID']), ])

        keyword = self.search_entry.get_text()
        self.app.playlist.advise_new_playlist_name(keyword)
        if len(keyword) == 0:
            return
        if reset_status:
            self.liststore_songs.clear()
        Net.async_call(Net.search_songs, _append_songs,
                keyword, self.songs_page)

    def show_artists(self, reset_status=False):
        def _append_artists(artists_args, error=None):
            artists, hit, self.artists_total = artists_args
            if hit == 0:
                if reset_status:
                    self.artists_button.set_label(
                            '{0} (0)'.format(_('Artists')))
                return
            self.artists_button.set_label(
                    '{0} ({1})'.format(_('Artists'), hit))
            i = len(self.liststore_artists)
            for artist in artists:
                self.liststore_artists.append([self.app.theme['anonymous'],
                    artist['ARTIST'],
                    int(artist['ARTISTID']), 
                    artist['COUNTRY'], ])
                Net.update_artist_logo(self.liststore_artists, i, 0,
                        artist['PICPATH'])
                i += 1

        keyword = self.search_entry.get_text()
        if len(keyword) == 0:
            return
        if reset_status:
            self.liststore_artists.clear()
        Net.async_call(Net.search_artists, _append_artists,
                keyword, self.artists_page)

    def show_albums(self, reset_status=False):
        def _append_albums(albums_args, error=None):
            albums, hit, self.albums_total = albums_args
            if hit == 0:
                if reset_status:
                    self.albums_button.set_label(
                            '{0} (0)'.format(_('Albums')))
                return
            self.albums_button.set_label(
                    '{0} ({1})'.format(_('Albums'), hit))
            i = len(self.liststore_albums)
            for album in albums:
                if len(album['info']) == 0:
                    tooltip = Widgets.tooltip(album['name'])
                else:
                    tooltip = '<b>{0}</b>\n{1}'.format(
                            Widgets.tooltip(album['name']),
                            Widgets.tooltip(album['info']))
                self.liststore_albums.append([self.app.theme['anonymous'],
                    album['name'],
                    int(album['albumid']), 
                    album['artist'],
                    int(album['artistid']),
                    tooltip, ])
                Net.update_album_covers(self.liststore_albums,
                        i, 0, album['pic'])
                i += 1

        keyword = self.search_entry.get_text()
        if len(keyword) == 0:
            return
        if reset_status:
            self.liststore_albums.clear()
        Net.async_call(Net.search_albums, _append_albums,
                keyword, self.albums_page)

    def reset_search_status(self):
        self.songs_tab_inited = False
        self.artists_tab_inited = False
        self.albums_tab_inited = False

        self.songs_button.set_label(_('Songs'))
        self.artists_button.set_label(_('Artists'))
        self.albums_button.set_label(_('Albums'))

        self.liststore_songs.clear()
        self.liststore_artists.clear()
        self.liststore_albums.clear()

        self.songs_page = 0
        self.artists_page = 0
        self.albums_page = 0

    def search_artist(self, artist):
        self.reset_search_status()
        self.app.popup_page(self.app_page)
        self.search_entry.set_text(artist)
        self.artists_button.set_active(True)

    def search_album(self, album):
        self.reset_search_status()
        self.app.popup_page(self.app_page)
        self.search_entry.set_text(album)
        self.albums_button.set_active(True)

    def on_songs_tab_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.songs_page < self.songs_total - 1:
            self.songs_page += 1
            self.show_songs()

    def on_artists_tab_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.artists_page < self.artists_total - 1:
            self.artists_page += 1
            self.show_artists()

    def on_albums_tab_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.albums_page < self.albums_total - 1:
            self.albums_page += 1
            self.show_albums()

    def on_iconview_artists_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist = model[path][1]
        artistid = model[path][2]
        self.app.popup_page(self.app.artists.app_page)
        self.app.artists.show_artist(artist, artistid)

    def on_iconview_albums_item_activated(self, iconview, path):
        model = iconview.get_model()
        album = model[path][1]
        albumid = model[path][2]
        artist = model[path][3]
        artistid = model[path][4]
        self.app.popup_page(self.app.artists.app_page)
        self.app.artists.show_album(album, albumid, artist, artistid)
