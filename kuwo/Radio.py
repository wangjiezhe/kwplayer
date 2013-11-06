
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
import json
import os

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class RadioItem(Gtk.EventBox):
    def __init__(self, radio_info, app):
        super().__init__()
        self.app = app
        self.playlists = app.radio.playlists
        self.connect('button-press-event', self.on_button_pressed)
        # radio_info contains:
        # pic, name, radio_id, offset
        self.radio_info = radio_info
        self.expanded = False

        self.box = Gtk.Box()
        self.box.props.margin_top = 5
        self.box.props.margin_bottom = 5
        self.add(self.box)

        self.img = Gtk.Image()
        self.img_path = Net.get_image(radio_info['pic'])
        self.small_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                self.img_path, 50, 50)
        self.big_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                self.img_path, 75, 75)
        self.img.set_from_pixbuf(self.small_pix)
        self.box.pack_start(self.img, False, False, 0)

        box_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(box_right, True, True, 0)

        radio_name = Gtk.Label(Widgets.short_str(radio_info['name'], 8))
        box_right.pack_start(radio_name, True, True, 0)

        self.label = Gtk.Label(_('song name'))
        self.label.get_style_context().add_class('info-label')
        box_right.pack_start(self.label, False, False, 0)

        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        self.toolbar.set_show_arrow(False)
        self.toolbar.set_icon_size(1)
        box_right.pack_start(self.toolbar, False, False, 0)

        button_play = Gtk.ToolButton()
        button_play.set_label(_('Play'))
        button_play.set_icon_name('media-playback-start-symbolic')
        button_play.connect('clicked', self.on_button_play_clicked)
        self.toolbar.insert(button_play, 0)

#        button_next = Gtk.ToolButton()
#        button_next.set_label(_('Next'))
#        button_next.set_icon_name('media-skip-forward-symbolic')
#        button_next.connect('clicked', self.on_button_next_clicked)
#        self.toolbar.insert(button_next, 1)
#
        button_favorite = Gtk.ToolButton()
        button_favorite.set_label(_('Favorite'))
        button_favorite.set_icon_name('emblem-favorite-symbolic')
        button_favorite.connect('clicked', self.on_button_favorite_clicked)
        self.toolbar.insert(button_favorite, 1)

        button_delete = Gtk.ToolButton()
        button_delete.set_label(_('Delete'))
        button_delete.set_icon_name('user-trash-symbolic')
        button_delete.connect('clicked', self.on_button_delete_clicked)
        self.toolbar.insert(button_delete, 2)

        self.show_all()
        self.label.hide()
        self.toolbar.hide()

        self.init_songs()
    
    def init_songs(self):
        def _update_songs(songs, error=None):
            if songs is None:
                return
            index = self.get_index()
            self.playlists[index]['songs'] = songs
            self.playlists[index]['curr_song'] = 0
            self.update_label()
        index = self.get_index()
        if len(self.playlists[index]['songs']) == 0:
            Net.async_call(Net.get_radio_songs, _update_songs, 
                    self.radio_info['radio_id'], self.radio_info['offset'])
    
    def load_more_songs(self):
        def _on_more_songs_loaded(songs, error=None):
            if songs:
                # merge next list of songs to current list
                index = self.get_index()
                self.playlists[index]['songs'] += songs
        index = self.get_index()
        offset = self.playlists[index]['offset'] + 1
        self.playlists[index]['offset'] = offset
        Net.async_call(Net.get_radio_songs, _on_more_songs_loaded, 
                self.radio_info['radio_id'], offset)

    def expand(self):
        if self.expanded:
            return
        self.expanded = True
        self.img.set_from_pixbuf(self.big_pix)
        self.label.show_all()
        self.toolbar.show_all()
        self.update_label()

    def collapse(self):
        if not self.expanded:
            return
        self.expanded = False
        self.img.set_from_pixbuf(self.small_pix)
        self.label.hide()
        self.toolbar.hide()

    def update_label(self):
        index = self.get_index()
        radio = self.playlists[index]
        if radio['curr_song'] > 19:
            self.label.set_label('Song Name')
            return
        song = radio['songs'][radio['curr_song']]
        self.label.set_label(Widgets.short_str(song['name'], length=12))
        Gdk.Window.process_all_updates()
        self.label.realize()

    def get_index(self):
        i = 0
        for radio in self.playlists:
            if radio['radio_id'] == self.radio_info['radio_id']:
                break
            i += 1
        return i

    def play_song(self):
        index = self.get_index()
        radio = self.playlists[index]
        if radio['curr_song'] > 19:
            radio['curr_song'] = 0
            radio['songs'] = radio['songs'][20:]
        song = radio['songs'][radio['curr_song']]
        self.update_label()
        self.app.player.load_radio(song, self)

    def play_next_song(self):
        index = self.get_index()
        self.playlists[index]['curr_song'] += 1
        self.play_song()

    def get_next_song(self):
        index = self.get_index()
        radio = self.playlists[index]
        if radio['curr_song'] == 10:
            self.load_more_songs()
        if radio['curr_song'] > 19:
            radio['curr_song'] = 0
            radio['songs'] = radio['songs'][20:]
        return radio['songs'][radio['curr_song'] + 1]

    def on_button_pressed(self, widget, event):
        parent = self.get_parent()
        children = parent.get_children()
        for child in children:
            child.collapse()
        self.expand()

    # toolbar
    def on_button_play_clicked(self, btn):
        self.play_song()

    def on_button_favorite_clicked(self, btn):
        # TODO: change button image
        index = self.get_index()
        radio = self.playlists[index]
        song = radio['songs'][radio['curr_song']]
        self.app.playlist.add_song_to_favorite(song)

    def on_button_delete_clicked(self, btn):
        self.playlists.pop(self.get_index())
        self.destroy()


class Radio(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.first_show = False
        self.playlists = None
        self.load_playlists()

    def first(self):
        if self.first_show:
            return
        self.first_show = True
        app = self.app

        # left side panel
        scrolled_myradio = Gtk.ScrolledWindow()
        scrolled_myradio.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        self.pack_start(scrolled_myradio, False, False, 0)

        # radios selected by user.
        self.box_myradio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_myradio.props.margin_left = 10
        scrolled_myradio.add(self.box_myradio)

        self.scrolled_radios = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_radios, True, True, 0)

        # pic, name, id, num of listeners, pic_url, tooltip
        self.liststore_radios = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int, str, str, str)
        iconview_radios = Widgets.IconView(self.liststore_radios, tooltip=5)
        iconview_radios.connect('item_activated',
                self.on_iconview_radios_item_activated)
        self.scrolled_radios.add(iconview_radios)

        self.show_all()

        nid = 8
        page = 0
        radios, total_page = Net.get_nodes(nid, page)
        if total_page == 0:
            return
        i = 0
        for radio in radios:
            self.liststore_radios.append([
                self.app.theme['anonymous'],
                Widgets.unescape_html(radio['disname']), 
                int(radio['sourceid'].split(',')[0]),
                Widgets.unescape_html(radio['info']),
                radio['pic'],
                Widgets.set_tooltip(radio['disname'], radio['info']),
                ])
            Net.update_liststore_image(self.liststore_radios, i, 0,
                    radio['pic']),
            i += 1
        for radio in self.playlists:
            radio_item = RadioItem(radio, self.app)
            self.box_myradio.pack_start(radio_item, False, False, 0)

        GLib.timeout_add(300000, self.dump_playlists)

    def load_playlists(self):
        filepath = Config.RADIO_JSON
        _default = []
        if os.path.exists(filepath):
            with open(filepath) as fh:
                playlists = json.loads(fh.read())
        else:
            playlists = _default
        self.playlists = playlists

    def dump_playlists(self):
        filepath = Config.RADIO_JSON
        if self.playlists is not None:
            with open(filepath, 'w') as fh:
                fh.write(json.dumps(self.playlists))
        return True

    def do_destroy(self):
        self.dump_playlists()

    def on_iconview_radios_item_activated(self, iconview, path):
        model = iconview.get_model()
        radio_info = {
                'name': model[path][1],
                'radio_id': model[path][2],
                'pic': model[path][4],
                'offset': 0,
                'curr_song': 0,
                'songs': [],
                }
        self.append_radio(radio_info)

    def append_radio(self, radio_info):
        for radio in self.playlists:
            # check if this radio already exists
            if radio['radio_id'] == radio_info['radio_id']:
                return
        self.playlists.append(radio_info)
        radio_item = RadioItem(radio_info, self.app)
        self.box_myradio.pack_start(radio_item, False, False, 0)
