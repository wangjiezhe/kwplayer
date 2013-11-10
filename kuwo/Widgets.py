
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
import html
from html.parser import HTMLParser
import os

from kuwo import Config

_ = Config._

_html_parser = HTMLParser()
# Need to unescape twice
unescape_html = lambda entity: _html_parser.unescape(_html_parser.unescape(entity))

def short_str(_str, length=10):
    if len(_str) > length:
        return _str[:length-2] + '..'
    return _str

def reach_scrolled_bottom(adj):
    return adj.get_upper() - adj.get_page_size() - adj.get_value() < 80

# deprecated
def tooltip(_str):
    return html.escape(_str.replace('<br>', '\n'))

def short_tooltip(tooltip, length=10):
    return short_str(html.escape(tooltip.replace('<br>', '\n')), length)

def set_tooltip(head, body):
    return '<b>{0}</b>\n\n{1}'.format(tooltip(head), tooltip(body))

def set_tooltip_with_song_tips(head, tip):
    songs = tip.split(';')
    results = []
    fmt = '{0}   <small>by <i>{1}</i></small>'
    for song in songs:
        if len(song) < 5:
            continue
        item = song.split('@')
        try:
            results.append(fmt.format(tooltip(item[1]), tooltip(item[3])))
        except IndexError as e:
            print(e, item)
            continue
    return '<b>{0}</b>\n\n{1}'.format(tooltip(head), '\n'.join(results))

def song_row_to_dict(song_row, start=1):
    song = {
            'name': song_row[start],
            'artist': song_row[start+1],
            'album': song_row[start+2],
            'rid': song_row[start+3],
            'artistid': song_row[start+4],
            'albumid': song_row[start+5],
            }
    return song

def song_dict_to_row(song):
    # with filepath
    song_row = [song['name'], song['artist'], song['album'], 
            int(song['rid']), int(song['artistid']), int(song['albumid']),]
    return song_row

class ListRadioButton(Gtk.RadioButton):
    def __init__(self, label, last_button=None):
        super().__init__(label)
        self.props.draw_indicator = False
        if last_button:
            self.join_group(last_button)
        # it might need a class name.

class BoldLabel(Gtk.Label):
    def __init__(self, label):
        super().__init__('<b>{0}</b>'.format(label))
        self.set_use_markup(True)
        self.props.halign = Gtk.Align.START
        self.props.xalign = 0
        #self.props.margin_bottom = 10

class FolderChooser(Gtk.Box):
    def __init__(self, parent):
        super().__init__(spacing=5)
        self.parent = parent
        self.filepath = os.environ['HOME']

        self.entry = Gtk.Entry()
        self.entry.set_text(self.filepath)
        self.entry.props.editable = False
        self.entry.props.width_chars = 30
        self.pack_start(self.entry, True, True, 0)

        choose_button = Gtk.Button('...')
        choose_button.connect('clicked', self.on_choose_button_clicked)
        self.pack_start(choose_button, False, False, 0)

    def set_filename(self, filepath):
        self.filepath = filepath
        self.entry.set_text(filepath)

    def get_filename(self):
        return self.filepath
    
    def on_choose_button_clicked(self, button):
        def on_dialog_file_activated(dialog):
            self.filepath = dialog.get_filename()
            self.entry.set_text(self.filepath)
            dialog.destroy()

        dialog = Gtk.FileChooserDialog(_('Choose a Folder'), self.parent,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK, Gtk.ResponseType.OK))

        dialog.connect('file-activated', on_dialog_file_activated)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            on_dialog_file_activated(dialog)
            return
        dialog.destroy()

class TreeViewColumnText(Gtk.TreeViewColumn):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        # This is the best option, but Gtk raises some Exceptions like:
        # (kuwo.py:14225): Gtk-CRITICAL **: _gtk_tree_view_column_autosize: assertion `GTK_IS_TREE_VIEW (tree_view)' failed
        # I don't know why that happens and how to fix it.  
        #self.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        self.props.sizing = Gtk.TreeViewColumnSizing.GROW_ONLY
        self.props.expand = True
        self.props.max_width = 280


class TreeViewColumnIcon(Gtk.TreeViewColumn):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        self.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self.props.fixed_width = 20


class ControlBox(Gtk.Box):
    def __init__(self, liststore, app, select_all=True):
        super().__init__(spacing=5)
        self.liststore = liststore
        self.app = app

        button_selectall = Gtk.ToggleButton(_('Select All'))
        button_selectall.set_active(select_all)
        button_selectall.connect('toggled', 
                self.on_button_selectall_toggled)
        self.pack_start(button_selectall, False, False, 0)

        button_play = Gtk.Button(_('Play'))
        button_play.connect('clicked', self.on_button_play_clicked)
        self.pack_start(button_play, False, False, 0)

        #button_add = Gtk.MenuButton(_('Add to Playlist'))
        #button_add.set_menu_model(self.app.playlist.playlist_menu_model)
        button_add = Gtk.Button(_('Add to Playlist'))
        button_add.connect('clicked', self.on_button_add_clicked)
        self.pack_start(button_add, False, False, 0)

        button_cache = Gtk.Button(_('Cache'))
        button_cache.connect('clicked', self.on_button_cache_clicked)
        self.pack_start(button_cache, False, False, 0)

    def on_button_selectall_toggled(self, btn):
        toggled = btn.get_active()
        for song in self.liststore:
            song[0] = toggled

    def on_button_play_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore if s[0]]
        self.app.playlist.play_songs(songs)

    def on_button_add_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore if s[0]]
        self.app.playlist.popup_playlist_menu(btn, songs)

    def on_button_cache_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore if s[0]]
        self.app.playlist.cache_songs(songs)

class MVControlBox(Gtk.Box):
    def __init__(self, liststore, app):
        super().__init__()
        self.liststore = liststore
        self.app = app

        button_add = Gtk.Button(_('Add to Playlist'))
        button_add.connect('clicked', self.on_button_add_clicked)
        self.pack_start(button_add, False, False, 0)

    def on_button_add_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore]
        self.app.playlist.popup_playlist_menu(btn, songs)


class IconView(Gtk.IconView):
    def __init__(self, liststore, info_pos=3, tooltip=None):
        super().__init__(model=liststore)

        # liststore:
        # 0 - logo
        # 1 - name
        # 2 - id
        # 3 - info
        # 4 - tooltip
        self.set_pixbuf_column(0)
        if tooltip is not None:
            self.set_tooltip_column(tooltip)
        self.props.item_width = 150

        cell_name = Gtk.CellRendererText()
        cell_name.set_alignment(0.5, 0.5)
        cell_name.props.max_width_chars = 15
        #cell_name.props.width_chars = 15
        self.pack_start(cell_name, True)
        self.add_attribute(cell_name, 'text', 1)

        cell_info = Gtk.CellRendererText()
        fore_color = Gdk.RGBA(red=136/256, green=139/256, blue=132/256)
        cell_info.props.foreground_rgba = fore_color
        cell_info.props.size_points = 9
        cell_info.props.max_width_chars = 18
        #cell_info.props.width_chars = 18
        cell_info.set_alignment(0.5, 0.5)
        self.pack_start(cell_info, True)
        self.add_attribute(cell_info, 'text', info_pos)


class TreeViewSongs(Gtk.TreeView):
    def __init__(self, liststore, app):
        super().__init__(model=liststore)
        self.set_headers_visible(False)
        self.liststore = liststore
        self.app = app

        checked = Gtk.CellRendererToggle()
        checked.connect('toggled', self.on_song_checked)
        column_check = Gtk.TreeViewColumn('Checked', checked, active=0)
        self.append_column(column_check)

        name = Gtk.CellRendererText()
        col_name = TreeViewColumnText('Name', name, text=1)
        self.append_column(col_name)

        artist = Gtk.CellRendererText()
        col_artist = TreeViewColumnText('Artist', artist, text=2)
        self.append_column(col_artist)

        album = Gtk.CellRendererText()
        col_album = TreeViewColumnText('Album', album, text=3)
        self.append_column(col_album)

        play = Gtk.CellRendererPixbuf(pixbuf=app.theme['play'])
        col_play = TreeViewColumnIcon('Play', play)
        self.append_column(col_play)

        add = Gtk.CellRendererPixbuf(pixbuf=app.theme['add'])
        col_add = TreeViewColumnIcon('Add', add)
        self.append_column(col_add)

        cache = Gtk.CellRendererPixbuf(pixbuf=app.theme['cache'])
        col_cache = TreeViewColumnIcon('Cache', cache)
        self.append_column(col_cache)

        self.connect('row_activated', self.on_row_activated)

    def on_song_checked(self, widget, path):
        self.liststore[path][0] = not self.liststore[path][0]

    def on_row_activated(self, treeview, path, column):
        print('on row activated')
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = song_row_to_dict(model[path])

        if index in (1, 4):
            self.app.playlist.play_song(song)
        elif index == 2:
            if len(song['artist']) == 0:
                print('artist is empty, no searching')
            self.app.search.search_artist(song['artist'])
        elif index == 3:
            if len(song['album']) == 0:
                print('album is empty, no searching')
                return
            self.app.search.search_album(song['album'])
        elif index == 5:
            self.app.playlist.add_song_to_playlist(song)
        elif index == 6:
            self.app.playlist.cache_song(song)

def network_error(parent, msg):
    dialog = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, msg)
    dialog.format_secondary_text(
            _('Please check network connection and try again'))
    dialog.run()
    dialog.destroy()

def filesystem_error(parent, path):
    msg = _('Failed to open file or direcotry')
    dialog = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, msg)
    dialog.format_secondary_text(
            _('Please check {0} exists').format(path))
    dialog.run()
    dialog.destroy()

def error(app, msg, msg2=None):
    dialog = Gtk.MessageDialog(app.window, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, msg)
    if msg2 is not None:
        dialog.format_secondary_text(msg2)
    dialog.run()
    dialog.destroy()
