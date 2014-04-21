
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import os
import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._


class InfoLabel(Gtk.Label):
    def __init__(self, grid, pref, left, top):
        super().__init__()
        self.props.xalign = 0
        self.props.use_markup = True
        grid.attach(self, left, top, 1, 1)
        self.pref = pref

    def set(self, info, key):
        if info and key in info:
            self.set_label('<b>{0} :</b> {1}'.format(self.pref, info[key]))
        else:
            self.set_label('<b>{0} :</b>'.format(self.pref))


class ArtistButton(Gtk.RadioButton):
    def __init__(self, parent, label, group, tab_index):
        super().__init__(label=label)
        self.props.draw_indicator = False
        if group:
            self.join_group(group)
        self.tab = tab_index
        self.parent = parent
        parent.artist_buttons.pack_start(self, False, False, 0)
        self.connect('toggled', self.on_toggled)

    def on_toggled(self, btn):
        state = self.get_active()
        if not state:
            return
        self.parent.artist_notebook.set_current_page(self.tab)
        methods = [
                self.parent.show_artist_songs,
                self.parent.show_artist_albums,
                self.parent.show_artist_mv,
                self.parent.show_artist_similar,
                self.parent.show_artist_info,
                ]
        methods[self.tab]()


class Artists(Gtk.Box):
    '''Artists tab in notebook.'''

    title = _('Artists')
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

    def first(self):
        if not self.first_run:
            return
        self.first_run = False

        app = self.app

        home_button = Gtk.Button(_('Artists'))
        home_button.connect('clicked', self.on_home_button_clicked)
        self.buttonbox.pack_start(home_button, False, False, 0)
        self.artist_button = Gtk.Button('')
        self.artist_button.connect('clicked', self.on_artist_button_clicked)
        self.buttonbox.pack_start(self.artist_button, False, False, 0)
        # to show artist name or album name
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        # control_box for artist's songs
        # checked, name, artist, album, rid, artistid, albumid
        self.artist_songs_liststore = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.artist_control_box = Widgets.ControlBox(
                self.artist_songs_liststore, app)
        self.buttonbox.pack_end(self.artist_control_box, False, False, 0)

        # control box for artist's mv
        # pic, name, artist, album, rid, artistid, albumid, tooltip
        self.artist_mv_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, str, str, int, int, int, str)
        self.artist_mv_control_box = Widgets.MVControlBox(
                self.artist_mv_liststore, app)
        self.buttonbox.pack_end(self.artist_mv_control_box, False, False, 0)

        # control box for artist's albums
        # checked, name, artist, album, rid, artistid, albumid
        self.album_songs_liststore = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.album_control_box = Widgets.ControlBox(
                self.album_songs_liststore, app)
        self.buttonbox.pack_end(self.album_control_box, False, False, 0)

        # main notebook
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        # Artists tab (tab 0)
        self.artists_tab = Gtk.Box()
        self.notebook.append_page(self.artists_tab, Gtk.Label(_('Artists')))
        #self.pack_start(self.box_artists, True, True, 0)

        # left panel of artists tab
        artists_left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.artists_tab.pack_start(artists_left_box, False, False, 0)
        # artists categories
        # name, id
        self.cate_liststore = Gtk.ListStore(str, int)
        self.cate_treeview = Gtk.TreeView(model=self.cate_liststore)
        self.cate_treeview.props.headers_visible = False
        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=0)
        self.cate_treeview.append_column(col_name)
        artists_left_box.pack_start(self.cate_treeview, False, False, 0)

        # artists prefix
        # disname, prefix
        self.pref_liststore = Gtk.ListStore(str, str)
        self.pref_combo = Gtk.ComboBox(model=self.pref_liststore)
        cell_name = Gtk.CellRendererText()
        self.pref_combo.pack_start(cell_name, True)
        self.pref_combo.add_attribute(cell_name, 'text', 0)
        self.pref_combo.props.margin_top = 15
        artists_left_box.pack_start(self.pref_combo, False, False, 0)

        # favirote artists
        self.fav_yes_img = Gtk.Image.new_from_pixbuf(app.theme['favorite'])
        self.fav_no_img = Gtk.Image.new_from_pixbuf(app.theme['no-favorite'])
        fav_artists_btn = Gtk.Button(_('Favorite'))
        fav_artists_btn.props.margin_top = 20
        fav_artists_btn.props.image = Gtk.Image.new_from_pixbuf(
                app.theme['favorite'])
        if not Config.GTK_LE_36:
            fav_artists_btn.props.always_show_image = True
        fav_artists_btn.connect('clicked', self.on_fav_artists_btn_clicked)
        artists_left_box.pack_start(fav_artists_btn, False, False, 0)

        # main window of artists
        self.artists_win = Gtk.ScrolledWindow()
        self.artists_win.get_vadjustment().connect(
                'value-changed', self.on_artists_win_scrolled)
        self.artists_tab.pack_start(self.artists_win, True, True, 0)
        # icon, artist name, artist id, num of songs, tooltip
        self.artists_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        artists_iconview = Widgets.IconView(
                self.artists_liststore, tooltip=4)
        artists_iconview.connect(
                'item_activated', self.on_artists_iconview_item_activated)
        self.artists_win.add(artists_iconview)

        # Artist tab (tab 1)
        self.artist_tab = Gtk.Box()
        self.notebook.append_page(self.artist_tab, Gtk.Label(_('Artist')))

        # left panel of artist
        self.artist_buttons = Gtk.Box(
                spacing=5, orientation=Gtk.Orientation.VERTICAL)
        self.artist_buttons.props.margin_top = 15
        self.artist_tab.pack_start(self.artist_buttons, False, False, 0)

        self.artist_songs_button = ArtistButton(
                self, _('Songs'), None, 0)
        self.artist_albums_button = ArtistButton(
                self, _('Albums'), self.artist_songs_button, 1)
        self.artist_mv_button = ArtistButton(
                self, _('MV'), self.artist_songs_button, 2)
        self.artist_similar_button = ArtistButton(
                self, _('Similar'), self.artist_songs_button, 3)
        self.artist_info_button = ArtistButton(
                self, _('Info'), self.artist_songs_button, 4)

        # Add fav_btn to artist_tab
        fav_curr_artist_btn = Gtk.Button()
        fav_curr_artist_btn.props.margin_top = 15
        fav_curr_artist_btn.props.halign = Gtk.Align.CENTER
        fav_curr_artist_btn.props.image = self.fav_no_img
        if not Config.GTK_LE_36:
            fav_curr_artist_btn.props.always_show_image = True
        fav_curr_artist_btn.set_tooltip_text(
                _('Add to favorite artists list'))
        fav_curr_artist_btn.connect(
                'clicked', self.on_fav_curr_artist_btn_clicked)
        self.artist_buttons.pack_start(fav_curr_artist_btn, False, False, 0)
        self.fav_curr_artist_btn = fav_curr_artist_btn

        # main window of artist tab
        self.artist_notebook = Gtk.Notebook()
        self.artist_notebook.set_show_tabs(False)
        self.artist_tab.pack_start(self.artist_notebook, True, True, 0)

        # songs tab for artist (tab 0)
        self.artist_songs_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_songs_tab, Gtk.Label(_('Songs')))
        artist_songs_treeview = Widgets.TreeViewSongs(
                self.artist_songs_liststore, app)
        self.artist_songs_tab.add(artist_songs_treeview)


        # albums tab for artist (tab 1)
        self.artist_albums_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_albums_tab, Gtk.Label(_('Albums')))
        # pic, album, albumid, artist, artistid, info/tooltip
        self.artist_albums_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, int, str)
        artist_albums_iconview = Widgets.IconView(
                self.artist_albums_liststore, tooltip=5)
        artist_albums_iconview.connect(
                'item_activated',
                self.on_artist_albums_iconview_item_activated)
        self.artist_albums_tab.add(artist_albums_iconview)

        # MVs tab for artist (tab 2)
        self.artist_mv_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_mv_tab, Gtk.Label(_('MV')))
        artist_mv_iconview = Widgets.IconView(
                self.artist_mv_liststore, info_pos=2, tooltip=7)
        artist_mv_iconview.connect(
                'item_activated', self.on_artist_mv_iconview_item_activated)
        self.artist_mv_tab.add(artist_mv_iconview)

        # Similar tab for artist (tab 3)
        self.artist_similar_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_similar_tab, Gtk.Label(_('Similar')))
        # pic, artist name, artist id, num of songs, tooltip
        self.artist_similar_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        artist_similar_iconview = Widgets.IconView(
                self.artist_similar_liststore, tooltip=4)
        artist_similar_iconview.connect(
                'item_activated',
                self.on_artist_similar_iconview_item_activated)
        self.artist_similar_tab.add(artist_similar_iconview)

        # Info tab for artist (tab 4)
        artist_info_tab = Gtk.ScrolledWindow()
        artist_info_tab_vp = Gtk.Viewport()
        artist_info_tab.add(artist_info_tab_vp)
        artist_info_tab.props.margin_left = 20
        artist_info_tab.props.margin_top = 5
        self.artist_notebook.append_page(
                artist_info_tab, Gtk.Label(_('Info')))
        artist_info_box = Gtk.Box(
                spacing=10, orientation=Gtk.Orientation.VERTICAL)
        artist_info_box.props.margin_right = 10
        artist_info_box.props.margin_bottom = 10
        artist_info_tab_vp.add(artist_info_box)

        artist_info_hbox = Gtk.Box(spacing=20)
        artist_info_box.pack_start(artist_info_hbox, False, False, 0)

        self.artist_info_pic = Gtk.Image()
        self.artist_info_pic.set_from_pixbuf(app.theme['anonymous'])
        self.artist_info_pic.props.xalign = 0
        self.artist_info_pic.props.yalign = 0
        artist_info_hbox.pack_start(self.artist_info_pic, False, False, 0)
        artist_info_grid = Gtk.Grid()
        artist_info_grid.props.row_spacing = 10
        artist_info_grid.props.column_spacing = 30
        self.artist_info_name = InfoLabel(
                artist_info_grid, _('Name'), 0, 0)
        self.artist_info_birthday = InfoLabel(
                artist_info_grid, _('Birthday'), 0, 1)
        self.artist_info_birthplace = InfoLabel(
                artist_info_grid, _('Birthplace'), 1, 1)
        self.artist_info_height = InfoLabel(
                artist_info_grid, _('Height'), 0, 2)
        self.artist_info_weight = InfoLabel(
                artist_info_grid, _('Weight'), 1, 2)
        self.artist_info_country = InfoLabel(
                artist_info_grid, _('Country'), 0, 3)
        self.artist_info_language = InfoLabel(
                artist_info_grid, _('Language'), 1, 3)
        self.artist_info_gender = InfoLabel(
                artist_info_grid, _('Gender'), 0, 4)
        self.artist_info_constellation = InfoLabel(
                artist_info_grid, _('Constellation'), 1, 4)
        artist_info_hbox.pack_start(artist_info_grid, False, False, 0)

        artist_info_textview = Gtk.TextView()
        self.artist_info_textbuffer = Gtk.TextBuffer()
        artist_info_textview.props.editable = False
        artist_info_textview.props.cursor_visible = False
        artist_info_textview.props.wrap_mode = Gtk.WrapMode.CHAR
        artist_info_textview.set_buffer(self.artist_info_textbuffer)
        artist_info_box.pack_start(artist_info_textview, True, True, 0)

        # Album tab (tab 2)
        album_songs_tab = Gtk.ScrolledWindow()
        self.notebook.append_page(album_songs_tab, Gtk.Label(_('Album')))
        album_songs_treeview = Widgets.TreeViewSongs(
                self.album_songs_liststore, app)
        album_songs_tab.add(album_songs_treeview)

        # Favorite artists tab (tab 3)
        fav_artists_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notebook.append_page(fav_artists_tab, Gtk.Label(_('Favorite')))
        fav_buttons = Gtk.Box(spacing=5)
        fav_artists_tab.pack_start(fav_buttons, False, False, 0)
        fav_main_btn = Gtk.Button(_('Artists'))
        fav_main_btn.connect('clicked', self.on_fav_main_btn_clicked)
        fav_buttons.pack_start(fav_main_btn, False, False, 0)
        fav_label = Gtk.Label(_('Favorite Artists'))
        fav_buttons.pack_start(fav_label, False, False, 0)
        fav_win = Gtk.ScrolledWindow()
        fav_artists_tab.pack_start(fav_win, True, True, 0)
        # icon, artist name, artist id, tooltip
        self.fav_artists_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str)
        fav_artists_iconview = Widgets.IconView(
                self.fav_artists_liststore, info_pos=None, tooltip=3)
        fav_artists_iconview.connect('item_activated',
                self.on_fav_artists_iconview_item_activated)
        fav_win.add(fav_artists_iconview)

        prefs = ((_('All'), ''),
                ('A', 'a'), ('B', 'b'), ('C', 'c'), ('D', 'd'),
                ('E', 'e'), ('F', 'f'), ('G', 'g'), ('H', 'h'), ('I', 'i'),
                ('J', 'j'), ('K', 'k'), ('L', 'l'), ('M', 'm'), ('N', 'n'),
                ('O', 'o'), ('P', 'p'), ('Q', 'q'), ('R', 'r'), ('S', 's'),
                ('T', 't'), ('U', 'u'), ('V', 'v'), ('W', 'w'), ('X', 'x'),
                ('Y', 'y'), ('Z', 'z'), ('#', '%26'),
                )
        for pref in prefs:
            self.pref_liststore.append(pref)
        self.pref_combo.set_active(0)
        self.pref_combo.connect('changed', self.on_cate_changed)

        cates = (
                (_('Hot Artists'), 0),
                (_('Chinese Male'), 1),
                (_('Chinese Female'), 2),
                (_('Chinese Band'), 3),
                (_('Japanese Male'), 4),
                (_('Japanese Female'), 5),
                (_('Japanese Band'), 6),
                (_('European Male'), 7),
                (_('European Female'), 8),
                (_('European Band'), 9),
                (_('Others'), 10),
                )
        for cate in cates:
            self.cate_liststore.append(cate)
        selection = self.cate_treeview.get_selection()
        self.cate_treeview.connect('row_activated', self.on_cate_changed)
        selection.connect('changed', self.on_cate_changed)
        selection.select_path(0)

        # load current favorite artists list
        self.load_fav_artists()
        self.show_all()
        self.buttonbox.hide()

    def after_init(self):
        pass

    def do_destroy(self):
        if not self.first_run:
            self.dump_fav_artists()

    def on_cate_changed(self, *args):
        self.append_artists(init=True)

    def append_artists(self, init=False):
        def on_append_artists(info, error=None):
            artists, self.artists_total = info
            if error or not self.artists_total or not artists:
                return
            urls = []
            tree_iters = []
            for artist in artists:
                _info = ' '.join([artist['music_num'], _(' songs'), ])
                tree_iter = self.artists_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(artist['name']),
                    int(artist['id']),
                    _info,
                    Widgets.set_tooltip(artist['name'], _info),
                    ])
                urls.append(artist['pic'])
                tree_iters.append(tree_iter)
            Net.update_artist_logos(
                    self.artists_liststore, 0, tree_iters, urls)

        if init:
            self.artists_liststore.clear()
            self.artists_page = 0
            self.artists_win.get_vadjustment().set_value(0)
        if init or not hasattr(self.artists_liststore, 'timestamp'):
            self.artists_liststore.timestamp = time.time()
        selection = self.cate_treeview.get_selection()
        selected = selection.get_selected()
        if not selected:
            return
        model, _iter = selected
        pref_index = self.pref_combo.get_active()
        catid = model[_iter][1]
        prefix = self.pref_liststore[pref_index][1]
        Net.async_call(
                Net.get_artists, on_append_artists, catid,
                self.artists_page, prefix)

    def on_artists_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist_name = model[path][1]
        artist_id = model[path][2]
        self.show_artist(artist_name, artist_id)

    # Song window
    def on_home_button_clicked(self, btn):
        self.buttonbox.hide()
        self.notebook.set_current_page(0)

    # scrolled windows
    def on_artists_win_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and 
            self.artists_page < self.artists_total - 1):
            self.artists_page += 1
            self.append_artists()

    # open API
    def show_artist(self, artist, artistid):
        '''Show artist tab'''
        self.first()
        self.curr_artist_name = artist
        self.curr_artist_id = artistid
        self.notebook.set_current_page(1)
        self.artist_songs_inited = False
        self.artist_albums_inited = False
        self.artist_mv_inited = False
        self.artist_similar_inited = False
        self.artist_info_inited = False

        self.buttonbox.show_all()
        self.artist_button.hide()
        self.artist_mv_control_box.hide()
        self.album_control_box.hide()
        self.artist_control_box.select_all()
        self.label.set_label(artist)
        self.app.playlist.advise_new_playlist_name(artist)

        if self.check_artist_favorited(artistid):
            self.fav_curr_artist_btn.props.image = self.fav_yes_img
        else:
            self.fav_curr_artist_btn.props.image = self.fav_no_img

        # switch to `songs` tab
        if self.artist_songs_button.get_active():
            self.show_artist_songs()
        else:
            self.artist_songs_button.set_active(True)

    def show_artist_songs(self):
        '''Show all songs of this artist'''
        self.album_control_box.hide()
        self.artist_mv_control_box.hide()
        self.artist_control_box.show_all()
        if self.artist_songs_inited:
            return
        self.artist_songs_inited = True
        self.append_artist_songs(init=True)

    def append_artist_songs(self, init=False):
        def _append_artist_songs(songs_args, error=None):
            songs, self.artist_songs_total = songs_args
            if error or self.artist_songs_total == 0:
                return
            for song in songs:
                self.artist_songs_liststore.append([
                    True,
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(song['album']),
                    int(song['musicrid']),
                    int(song['artistid']), 
                    int(song['albumid']),
                    ]) 
            # automatically load more songs
            self.artist_songs_page += 1
            if self.artist_songs_page < self.artist_songs_total - 1:
                self.append_artist_songs()

        if init:
            self.artist_songs_liststore.clear()
            self.artist_songs_page = 0
        Net.async_call(
                Net.get_artist_songs_by_id, _append_artist_songs, 
                self.curr_artist_id, self.artist_songs_page)

    def show_artist_albums(self):
        self.artist_control_box.hide()
        self.album_control_box.hide()
        self.artist_mv_control_box.hide()
        if self.artist_albums_inited:
            return
        self.artist_albums_inited = True
        self.append_artist_albums(init=True)

    def append_artist_albums(self, init=False):
        def _append_artist_albums(albums_args, error=None):
            albums, self.artist_albums_total = albums_args
            if error or self.artist_albums_total == 0:
                return
            urls = []
            tree_iters = []
            for album in albums:
                tree_iter = self.artist_albums_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(album['name']),
                    int(album['albumid']),
                    Widgets.unescape(album['artist']),
                    int(album['artistid']),
                    Widgets.set_tooltip(album['name'], album['info']),
                    ])
                urls.append(album['pic'])
                tree_iters.append(tree_iter)
            Net.update_album_covers(
                    self.artist_albums_liststore, 0, tree_iters, urls)
            self.artist_albums_page += 1
            if self.artist_albums_page < self.artist_albums_total - 1:
                self.append_artist_albums()

        if init:
            self.artist_albums_liststore.clear()
            self.artist_albums_page = 0
        if init or not hasattr(self.artist_albums, 'timestamp'):
            self.artist_albums_liststore.timestamp = time.time()
        Net.async_call(
                Net.get_artist_albums, _append_artist_albums,
                self.curr_artist_id, self.artist_albums_page)

    def show_artist_mv(self):
        self.artist_control_box.hide()
        self.album_control_box.hide()
        self.artist_mv_control_box.show_all()
        if self.artist_mv_inited:
            return
        self.artist_mv_inited = True
        self.append_artist_mv(init=True)

    def append_artist_mv(self, init=False):
        def _append_artist_mv(mv_args, error=None):
            mvs, self.artist_mv_total = mv_args
            if error or self.artist_mv_total == 0:
                return
            urls = []
            tree_iters = []
            for mv in mvs:
                tree_iter = self.artist_mv_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(mv['name']),
                    Widgets.unescape(mv['artist']),
                    '',
                    int(mv['musicid']),
                    int(mv['artistid']),
                    0,
                    Widgets.set_tooltip(mv['name'], mv['artist']),
                    ])
                tree_iters.append(tree_iter)
                urls.append(mv['pic'])
            Net.update_mv_images(
                    self.artist_mv_liststore, 0, tree_iters, urls)
            self.artist_mv_page += 1
            if self.artist_mv_page < self.artist_mv_total - 1:
                self.append_artist_mv()

        if init:
            self.artist_mv_liststore.clear()
            self.artist_mv_page = 0
        if init or not hasattr(self.artist_mv_liststore, 'timestamp'):
            self.artist_mv_liststore.timestamp = time.time()
        Net.async_call(
                Net.get_artist_mv, _append_artist_mv,
                self.curr_artist_id, self.artist_mv_page)

    def show_artist_similar(self):
        self.artist_control_box.hide()
        self.artist_mv_control_box.hide()
        self.album_control_box.hide()
        if self.artist_similar_inited:
            return
        self.artist_similar_inited = True
        self.append_artist_similar(init=True)

    def append_artist_similar(self, init=False):
        self.first()
        def _append_artist_similar(similar_args, error=None):
            artists, self.artist_similar_total = similar_args
            if error or not self.artist_similar_total:
                return
            urls = []
            tree_iters = []
            for artist in artists:
                _info = ''.join([artist['songnum'], _(' songs'), ])
                tree_iter = self.artist_similar_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(artist['name']),
                    int(artist['id']),
                    _info,
                    Widgets.set_tooltip(artist['name'], _info),
                    ])
                urls.append(artist['pic'])
                tree_iters.append(tree_iter)
            Net.update_artist_logos(
                    self.artist_similar_liststore, 0, tree_iters, urls)
            self.artist_similar_page += 1
            if self.artist_similar_page < self.artist_similar_total - 1:
                self.append_artist_similar()

        if init:
            self.artist_similar_liststore.clear()
            self.artist_similar_page = 0
        if init or not hasattr(self.artist_similar_liststore, 'timestamp'):
            self.artist_similar_liststore.timestamp = time.time()
        Net.async_call(
                Net.get_artist_similar, _append_artist_similar,
                self.curr_artist_id, self.artist_similar_page)

    def show_artist_info(self):
        self.artist_control_box.hide()
        self.artist_mv_control_box.hide()
        self.album_control_box.hide()
        if self.artist_info_inited:
            return
        self.artist_info_inited = True
        self.append_artist_info()

    def append_artist_info(self):
        def _append_artist_info(info, error=None):
            if error or not info:
                return
            if info.get('pic', None):
                self.artist_info_pic.set_from_file(info['pic'])
            self.artist_info_name.set(info, 'name')
            self.artist_info_birthday.set(info, 'birthday')
            self.artist_info_birthplace.set(info, 'birthplace')
            self.artist_info_height.set(info, 'tall')
            self.artist_info_weight.set(info, 'weight',)
            self.artist_info_country.set(info, 'country')
            self.artist_info_language.set(info, 'language')
            self.artist_info_gender.set(info, 'gender',)
            self.artist_info_constellation.set(info, 'constellation')
            if info and 'info' in info:
                self.artist_info_textbuffer.set_text(
                        Widgets.escape(info['info']))
            else:
                self.artist_info_textbuffer.set_text('')

        Net.async_call(
                Net.get_artist_info, _append_artist_info,
                self.curr_artist_id)


    def on_artist_albums_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        album = model[path][1]
        albumid = model[path][2]
        artist = model[path][3]
        artistid = model[path][4]
        self.show_album(album, albumid, artist, artistid)

    def on_artist_mv_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        song = Widgets.song_row_to_dict(model[path])
        self.app.popup_page(self.app.lrc.app_page)
        self.app.playlist.play_song(song, use_mv=True)

    def on_artist_similar_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist = model[path][1]
        artistid = model[path][2]
        self.show_artist(artist, artistid)

    # open API
    def show_album(self, album, albumid, artist, artistid):
        '''Show album information, including songs'''
        self.first()
        self.curr_album_name = album
        self.curr_album_id = albumid
        self.curr_artist_name = artist
        self.curr_artist_id = artistid
        self.artist_button.set_label(artist)
        self.label.set_label(album)
        self.app.playlist.advise_new_playlist_name(album)
        self.buttonbox.show_all()
        self.artist_control_box.hide()
        self.artist_mv_control_box.hide()
        self.notebook.set_current_page(2)
        self.append_album_songs()
    
    def append_album_songs(self):
        def _append_album_songs(songs, error=None):
            if error or not songs:
                return
            for song in songs:
                self.album_songs_liststore.append([
                    True,
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(self.curr_album_name),
                    int(song['id']),
                    int(song['artistid']),
                    int(self.curr_album_id), ])
        self.album_songs_liststore.clear()
        Net.async_call(
                Net.get_album, _append_album_songs,
                self.curr_album_id)

    def on_artist_button_clicked(self, button):
        self.show_artist(self.curr_artist_name, self.curr_artist_id)

    # Signal handlers for favorite artists tab
    def add_to_fav_artists(self, artist_id, init=False):
        def _append_fav_artist(info, error=None):
            if error or not info:
                return
            if info.get('pic', None):
                pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        info['pic'], 100, 100)
            else:
                pix = self.app.theme['anonymous']
            tip = Widgets.escape(info.get('info', ''))
            self.fav_artists_liststore.append(
                    [pix, info['name'], artist_id, tip])

        if init is False and self.check_artist_favorited(artist_id):
            return
        Net.async_call(Net.get_artist_info, _append_fav_artist, artist_id)

    def remove_from_fav_artists(self, artist_id):
        '''Remove an artist from fav_artists_liststore.'''
        for row in self.fav_artists_liststore:
            if artist_id == row[2]:
                self.fav_artists_liststore.remove(row.iter)
                return

    def check_artist_favorited(self, artist_id):
        '''Check whether this artist is in favorite list.'''
        for row in self.fav_artists_liststore:
            if artist_id == row[2]:
                return True
        return False

    def load_fav_artists(self):
        '''Load fav_artists from json.'''
        if not os.path.exists(Config.FAV_ARTISTS_JSON):
            return
        with open(Config.FAV_ARTISTS_JSON) as fh:
            fav_artists = json.loads(fh.read())
        for artist_id in fav_artists:
            self.add_to_fav_artists(artist_id)

    def dump_fav_artists(self):
        '''Dump fav_artists to a json file'''
        fav_artists = [row[2] for row in self.fav_artists_liststore]
        if not fav_artists:
            return
        with open(Config.FAV_ARTISTS_JSON, 'w') as fh:
            fh.write(json.dumps(fav_artists))

    def on_fav_artists_btn_clicked(self, btn):
        self.notebook.set_current_page(3)

    def on_fav_main_btn_clicked(self, btn):
        self.notebook.set_current_page(0)

    def on_fav_artists_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist_name = model[path][1]
        artist_id = model[path][2]
        self.show_artist(artist_name, artist_id)

    def on_fav_curr_artist_btn_clicked(self, btn):
        if btn.props.image == self.fav_yes_img:
            btn.props.image = self.fav_no_img
            self.remove_from_fav_artists(self.curr_artist_id)
        else:
            btn.props.image = self.fav_yes_img
            self.add_to_fav_artists(self.curr_artist_id)
