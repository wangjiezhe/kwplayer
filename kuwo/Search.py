
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import html
import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
_ = Config._
from kuwo import Widgets
from kuwo import Net
from kuwo.log import logger


class Search(Gtk.Box):
    '''Search tab in notebook.'''

    title = _('Search')

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.app = app

        self.search_count = 0
        self.keyword = ''

        #Initialize page counter
        self.songs_page = 0
        self.songs_total = 0
        self.artists_page = 0
        self.artists_total = 0
        self.albums_page = 0
        self.albums_total = 0

        box_top = Gtk.Box(spacing=5)
        self.pack_start(box_top, False, False, 0)

        if Config.GTK_LE_36:
            self.search_entry = Gtk.Entry()
        else:
            self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_('Search Songs, Artists..'))
        self.search_entry.props.width_chars = 30
        self.search_entry.connect('activate', self.on_search_entry_activate)
        box_top.pack_start(self.search_entry, False, False, 20)

        self.songs_button = Widgets.ListRadioButton(_('Songs'))
        self.songs_button.connect('toggled', self.switch_notebook_page, 0)
        self.songs_button.search_count = 0
        box_top.pack_start(self.songs_button, False, False, 0)

        self.artists_button = Widgets.ListRadioButton(_('Artists'),
                                                      self.songs_button)
        self.artists_button.connect('toggled', self.switch_notebook_page, 1)
        self.artists_button.search_count = 0
        box_top.pack_start(self.artists_button, False, False, 0)

        self.albums_button = Widgets.ListRadioButton(_('Albums'),
                                                     self.songs_button)
        self.albums_button.connect('toggled', self.switch_notebook_page, 2)
        self.albums_button.search_count = 0
        box_top.pack_start(self.albums_button, False, False, 0)

        treeview_songs = Widgets.TreeViewSongs(app)
        self.liststore_songs = treeview_songs.liststore
        self.control_box = Widgets.ControlBox(self.liststore_songs, app,
                                              select_all=False)
        box_top.pack_end(self.control_box, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        songs_tab = Gtk.ScrolledWindow()
        songs_tab.get_vadjustment().connect('value-changed',
                                            self.on_songs_tab_scrolled)
        self.notebook.append_page(songs_tab, Gtk.Label(_('Songs')))
        songs_tab.add(treeview_songs)

        artists_tab = Gtk.ScrolledWindow()
        artists_tab.get_vadjustment().connect('value-changed',
                                              self.on_artists_tab_scrolled)
        self.notebook.append_page(artists_tab, Gtk.Label(_('Artists')))

        # pic, artist, artistid, country
        self.liststore_artists = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int, str)
        iconview_artists = Widgets.IconView(self.liststore_artists)
        iconview_artists.connect('item_activated',
                                 self.on_iconview_artists_item_activated)
        artists_tab.add(iconview_artists)

        albums_tab = Gtk.ScrolledWindow()
        albums_tab.get_vadjustment().connect('value-changed',
                                             self.on_albums_tab_scrolled)
        self.notebook.append_page(albums_tab, Gtk.Label(_('Albums')))
        albums_tab.search_count = 0

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
        if page == 0:
            self.control_box.show_all()
        elif page == 1:
            self.control_box.hide()
        elif page == 2:
            self.control_box.hide()
        if self.keyword and radiobtn.search_count != self.search_count:
            radiobtn.search_count = self.search_count
            self.reload_current_page()

    def on_search_entry_activate(self, search_entry):
        '''Start a new search action'''
        keyword = self.search_entry.get_text()
        if not keyword:
            return
        self.search_count += 1
        self.keyword = keyword
        self.reset_search_status()
        self.reload_current_page()

    def reload_current_page(self):
        page = self.notebook.get_current_page()
        if page == 0:
            self.show_songs()
        elif page == 1:
            self.show_artists()
        elif page == 2:
            self.show_albums()

    def show_songs(self):
        def _append_songs(songs_args, error=None):
            songs, hit, self.songs_total = songs_args
            if not error and songs and hit:
                for song in songs:
                    self.liststore_songs.append([
                        False,
                        Widgets.unescape(song['SONGNAME']),
                        Widgets.unescape(song['ARTIST']),
                        Widgets.unescape(song['ALBUM']),
                        int(song['MUSICRID'][6:]),
                        int(song['ARTISTID']),
                        int(song['ALBUMID']),
                        song['FORMATS'],
                    ])
            self.songs_button.set_label('{0} ({1})'.format(_('Songs'),
                                        len(self.liststore_songs)))

        self.app.playlist.advise_new_playlist_name(self.keyword)
        Net.async_call(Net.search_songs, self.keyword, self.songs_page,
                       callback=_append_songs)

    def show_artists(self):
        def _append_artists(artists_args, error=None):
            artists, hit, self.artists_total = artists_args
            if not error and artists and hit:
                urls, tree_iters = [], []
                for artist in artists:
                    tree_iter = self.liststore_artists.append([
                        self.app.theme['anonymous'],
                        Widgets.unescape(artist['ARTIST']),
                        int(artist['ARTISTID']),
                        Widgets.unescape(artist['COUNTRY']),
                    ])
                    tree_iters.append(tree_iter)
                    urls.append(artist['PICPATH'])
                Net.update_artist_logos(self.liststore_artists, 0,
                                        tree_iters, urls)
            else:
                logger.error('show_artists(): %s, %s' %
                             (self.artists_total, error))

            self.artists_button.set_label('{0} ({1})'.format(_('Artists'),
                                          len(self.liststore_artists)))

        # timestamp is used to mark Liststore ID
        if self.artists_page == 0:
            self.liststore_artists.timestamp = time.time()
        Net.async_call(Net.search_artists, self.keyword, self.artists_page,
                       callback=_append_artists)

    def show_albums(self):
        def _append_albums(albums_args, error=None):
            albums, hit, self.albums_total = albums_args
            if not error and albums and hit:
                urls,tree_iters = [], []
                for album in albums:
                    tooltip = Widgets.escape(album.get('info',
                                             album['name']))
                    tree_iter = self.liststore_albums.append([
                        self.app.theme['anonymous'],
                        Widgets.unescape(album['name']),
                        int(album['albumid']),
                        Widgets.unescape(album['artist']),
                        int(album['artistid']),
                        tooltip,
                    ])
                    tree_iters.append(tree_iter)
                    urls.append(album['pic'])
                Net.update_album_covers(self.liststore_albums, 0,
                                        tree_iters, urls)
            else:
                logger.error('show_albums: %s, %s' % (self.albums_total, error))

            self.albums_button.set_label('{0} ({1})'.format(_('Albums'),
                                         len(self.liststore_albums)))

        if self.albums_page == 0:
            self.liststore_albums.timestamp = time.time()
        Net.async_call(Net.search_albums, self.keyword, self.albums_page,
                       callback=_append_albums)

    def reset_search_status(self):
        self.songs_button.set_label(_('Songs'))
        self.artists_button.set_label(_('Artists'))
        self.albums_button.set_label(_('Albums'))

        self.liststore_songs.clear()
        self.liststore_artists.clear()
        self.liststore_albums.clear()
        for page in range(0, self.notebook.get_n_pages()):
            scrolled_window = self.notebook.get_nth_page(page)
            adj = scrolled_window.get_vadjustment()
            adj.set_value(0)
            adj.set_lower(0)
            adj.set_upper(0)

        self.songs_page = 0
        self.songs_total = 0
        self.artists_page = 0
        self.artists_total = 0
        self.albums_page = 0
        self.albums_total = 0

    def on_songs_tab_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and
                self.songs_page < self.songs_total - 1):
            self.songs_page += 1
            self.show_songs()

    def on_artists_tab_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and 
                self.artists_page < self.artists_total - 1):
            self.artists_page += 1
            self.show_artists()

    def on_albums_tab_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and
                self.albums_page < self.albums_total - 1):
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

    # Open APIs
    def search_artist(self, artist):
        self.app.popup_page(self.app_page)
        if not artist:
            return
        self.search_entry.set_text(artist)
        self.search_count += 1
        self.keyword = artist
        self.reset_search_status()
        self.artists_button.set_active(True)
        self.artists_button.toggled()

    def search_album(self, album):
        self.app.popup_page(self.app_page)
        if not album:
            return
        self.search_entry.set_text(album)
        self.search_count += 1
        self.keyword = album
        self.reset_search_status()
        self.albums_button.set_active(True)
        self.albums_button.toggled()
