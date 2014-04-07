
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import os
import random
import shutil
import time
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

from kuwo import Config
from kuwo import Net
from kuwo import Utils
from kuwo import Widgets

_ = Config._

DRAG_TARGETS = [
        ('text/plain', Gtk.TargetFlags.SAME_APP, 0),
        ('TEXT', Gtk.TargetFlags.SAME_APP, 1),
        ('STRING', Gtk.TargetFlags.SAME_APP, 2),
        ]
DRAG_ACTIONS = Gdk.DragAction.MOVE

class TreeViewColumnText(Widgets.TreeViewColumnText):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.props.clickable = True
        self.props.reorderable = True
        self.props.sort_indicator = True
        self.props.sort_column_id = kwds['text']

class NormalSongTab(Gtk.ScrolledWindow):
    def __init__(self, app, list_name):
        super().__init__()
        self.app = app
        self.list_name = list_name

        # name, artist, album, rid, artistid, albumid
        self.liststore = Gtk.ListStore(str, str, str, int, int, int)

        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        self.treeview.set_search_column(0)
        self.treeview.props.headers_clickable = True
        self.treeview.props.headers_visible = True
        self.treeview.props.reorderable = True
        self.treeview.props.rules_hint = True
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.enable_model_drag_source(
                Gdk.ModifierType.BUTTON1_MASK,
                DRAG_TARGETS,
                DRAG_ACTIONS)
        self.treeview.connect('drag-data-get', self.on_drag_data_get)
        self.treeview.enable_model_drag_dest(
                DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview.connect(
                'drag-data-received', self.on_drag_data_received)
        self.treeview.connect(
                'row_activated', self.on_treeview_row_activated)
        self.add(self.treeview)

        song_cell = Gtk.CellRendererText()
        song_col = TreeViewColumnText(_('Title'), song_cell, text=0)
        self.treeview.append_column(song_col)

        artist_cell = Gtk.CellRendererText()
        artist_col = TreeViewColumnText(_('Aritst'), artist_cell, text=1)
        self.treeview.append_column(artist_col)

        album_cell = Gtk.CellRendererText()
        album_col = TreeViewColumnText(_('Album'), album_cell, text=2)
        self.treeview.append_column(album_col)

        delete_cell = Gtk.CellRendererPixbuf(
                icon_name='user-trash-symbolic')
        self.delete_col = Widgets.TreeViewColumnIcon(
                _('Delete'), delete_cell)
        self.treeview.append_column(self.delete_col)
        self.treeview.connect(
                'key-press-event', self.on_treeview_key_pressed)
        self.treeview.connect(
                'button-press-event', self.on_treeview_button_pressed)
        
    def on_treeview_key_pressed(self, treeview, event):
        if event.keyval == Gdk.KEY_Delete:
            model, paths = self.selection.get_selected_rows()
            # paths needs to be reversed, or else an IndexError throwed.
            for path in reversed(paths):
                model.remove(model[path].iter)

    def on_treeview_button_pressed(self, treeview, event):
        path_info = treeview.get_path_at_pos(event.x, event.y)
        if not path_info:
            return
        path, column, cell_x, cell_y = path_info
        if column != self.delete_col:
            return
        self.liststore.remove(self.liststore[path].iter)

    def on_treeview_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = Widgets.song_row_to_dict(model[path], start=0)
        if index == 0:
            self.app.playlist.play_song(song, list_name=self.list_name)
        elif index == 1:
            self.app.search.search_artist(song['artist'])
        elif index == 2:
            self.app.search.search_album(song['album'])

    def on_drag_data_get(self, treeview, drag_context, sel_data, info, 
                         time):
        selection = treeview.get_selection()
        model, paths = selection.get_selected_rows()
        self.drag_data_old_iters = []
        songs = []
        for path in paths:
            song = [i for i in model[path]]
            songs.append(song)
            _iter = model.get_iter(path)
            self.drag_data_old_iters.append(_iter)
        sel_data.set_text(json.dumps(songs), -1)

    def on_drag_data_received(self, treeview, drag_context, x, y, sel_data,
                              info, event_time):
        model = treeview.get_model()
        data = sel_data.get_text()
        if not data:
            return
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if not drop_info:
            return
        path = drop_info[0]
        pos = int(str(path))
        songs = json.loads(data)
        for song in songs:
            model.insert(pos, song)
        for _iter in self.drag_data_old_iters:
            model.remove(_iter)


class ExportDialog(Gtk.Dialog):

    def __init__(self, parent, liststore):
        super().__init__(
                _('Export Songs'), parent.app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK,))
        self.parent = parent
        self.liststore = liststore
        self.app = parent.app

        self.set_border_width(15)

        box = self.get_content_area()
        box.set_size_request(540, 260)
        box.set_spacing = 5

        folder_label = Widgets.BoldLabel(_('Choose export folder:'))
        box.pack_start(folder_label, False, True, 2)

        self.folder_chooser = Widgets.FolderChooser(self.app.window)
        self.folder_chooser.props.margin_left = 20
        box.pack_start(self.folder_chooser, False, True, 0)

        self.with_lrc = Gtk.CheckButton(_('With lyrics'))
        self.with_lrc.set_tooltip_text(_('Export lyrics to the same folder'))
        self.with_lrc.props.margin_top = 20
        box.pack_start(self.with_lrc, False, False, 0)

        export_box = Gtk.Box(spacing=5)
        export_box.props.margin_top = 20
        box.pack_start(export_box, False, True, 0)

        self.export_prog = Gtk.ProgressBar()
        self.export_prog.props.show_text = True
        self.export_prog.props.text = ''
        export_box.pack_start(self.export_prog, True, True, 0)

        export_btn = Gtk.Button(_('Export'))
        export_btn.connect('clicked', self.do_export)
        export_box.pack_start(export_btn, False, False, 0)

        infobar = Gtk.InfoBar()
        infobar.props.margin_top = 20
        box.pack_start(infobar, False, True, 0)
        info_content = infobar.get_content_area()
        info_label = Gtk.Label(_('Only cached songs will be exported'))
        info_content.pack_start(info_label, False, False, 0)
        box.show_all()

    def do_export(self, button):
        num_songs = len(self.liststore)
        export_dir = self.folder_chooser.get_filename()
        export_lrc = self.with_lrc.get_active()
        for i, item in enumerate(self.liststore):
            song = Widgets.song_row_to_dict(item, start=0)
            cached, song_link, song_path = Net.get_song_link(
                    song, self.app.conf)
            if not cached:
                continue
            self.export_prog.set_fraction(i / num_songs)
            self.export_prog.set_text(song['name'])
            shutil.copy(song_path, export_dir)

            if export_lrc:
                lrc_path, lrc_cached = Net.get_lrc_path(song)
                if lrc_cached:
                    shutil.copy(lrc_path, export_dir)
            Gdk.Window.process_all_updates()
        self.destroy()


class PlayList(Gtk.Box):
    '''Playlist tab in notebook.'''

    title = _('PlayList')

    def __init__(self, app):
        super().__init__()

        self.app = app
        self.tabs = {}
        # self.lists_name contains playlists name
        self.lists_name = []
        # use curr_playing to locate song in treeview
        self.curr_playing = [None, None]

        # control cache job
        self.cache_enabled = False
        self.cache_job = None

        self.playlist_menu = Gtk.Menu()
        self.playlist_advice_disname = ''

        box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(box_left, False, False, 0)

        win_left = Gtk.ScrolledWindow()
        box_left.pack_start(win_left, True, True, 0)

        # disname, name/uuid, deletable/editable, tooltip(escaped disname)
        self.liststore_left = Gtk.ListStore(str, str, bool, str)
        self.treeview_left = Gtk.TreeView(model=self.liststore_left)
        self.treeview_left.set_headers_visible(False)
        self.treeview_left.set_tooltip_column(3)
        list_disname = Gtk.CellRendererText()
        list_disname.connect('edited', self.on_list_disname_edited)
        col_name = Gtk.TreeViewColumn(
                'List Name', list_disname, text=0, editable=2)
        self.treeview_left.append_column(col_name)
        #col_name.props.max_width = 75
        #col_name.props.fixed_width = 75
        #col_name.props.min_width = 70
        col_name.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        tree_sel = self.treeview_left.get_selection()
        tree_sel.connect('changed', self.on_tree_selection_left_changed)
        self.treeview_left.enable_model_drag_dest(
                DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview_left.connect(
                'drag-data-received',
                self.on_treeview_left_drag_data_received)
        win_left.add(self.treeview_left)

        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class(
                Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        toolbar.props.show_arrow = False
        toolbar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        toolbar.props.icon_size = 1
        add_btn = Gtk.ToolButton()
        add_btn.set_name('Add')
        add_btn.set_tooltip_text(_('Add a new playlist'))
        add_btn.set_icon_name('list-add-symbolic')
        add_btn.connect('clicked', self.on_add_playlist_button_clicked)
        toolbar.insert(add_btn, 0)
        remove_btn = Gtk.ToolButton()
        remove_btn.set_name('Remove')
        remove_btn.set_tooltip_text(_('Remove selected playlist'))
        remove_btn.set_icon_name('list-remove-symbolic')
        remove_btn.connect(
                'clicked', self.on_remove_playlist_button_clicked)
        toolbar.insert(remove_btn, 1)
        export_btn = Gtk.ToolButton()
        export_btn.set_name('Export')
        export_btn.set_tooltip_text(_('Export songs in selected playlist'))
        export_btn.set_icon_name('media-eject-symbolic')
        export_btn.connect(
                'clicked', self.on_export_playlist_button_clicked)
        toolbar.insert(export_btn, 2)
        box_left.pack_start(toolbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        self.pack_start(self.notebook, True, True, 0)

        # Use this trick to accelerate startup speed of app.
        GLib.timeout_add(1000, self.init_ui)

    def do_destroy(self):
        self.dump_playlists()
        if self.cache_job:
            self.cache_job.destroy()

    def first(self):
        selection = self.treeview_left.get_selection()
        selection.select_path(Gtk.TreePath(1))

    def init_ui(self):
        self.load_playlists()
        # dump playlists to dist every 5 minites
        GLib.timeout_add(300000, self.dump_playlists)
        if self.app.conf['show-pls']:
            self.app.popup_page(self.app_page)
        return False

    def dump_playlists(self):
        filepath = Config.PLS_JSON
        names = [list(p[:-1]) for p in self.liststore_left]
        # There must be at least 3 playlists.
        if len(names) < 3:
            return True
        playlists = {'_names_': names}
        for name in names:
            list_name = name[1]
            liststore = self.tabs[list_name].liststore
            playlists[list_name] = [list(p) for p in liststore]
        with open(filepath, 'w') as fh:
            fh.write(json.dumps(playlists))
        return True

    def load_playlists(self):
        filepath = Config.PLS_JSON
        _default = {
                '_names_': [
                    [_('Caching'), 'Caching', False],
                    [_('Default'), 'Default', False],
                    [_('Favorite'), 'Favorite', False],
                    ],
                'Caching': [],
                'Default': [],
                'Favorite': [],
                }
        if os.path.exists(filepath):
            with open(filepath) as fh:
                playlists = json.loads(fh.read())
        else:
            playlists = _default

        for playlist in playlists['_names_']:
            disname, list_name, editable = playlist
            tooltip = Widgets.escape(disname)
            self.liststore_left.append(
                    [disname, list_name, editable, tooltip])
            songs = playlists[list_name]
            self.init_tab(list_name, songs)

    def init_tab(self, list_name, songs):
        scrolled_win = NormalSongTab(self.app, list_name)
        for song in songs:
            scrolled_win.liststore.append(song)
        if list_name == 'Caching':
            box_caching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            buttonbox = Gtk.Box(spacing=5)
            box_caching.pack_start(buttonbox, False, False, 0)
            button_start = Gtk.Button(_('Start Cache Service'))
            button_start.connect('clicked', self.switch_caching_daemon)
            self.button_start = button_start
            buttonbox.pack_start(button_start, False, False, 0)
            button_open = Gtk.Button(_('Open Cache Folder'))
            button_open.connect('clicked', self.open_cache_folder)
            buttonbox.pack_start(button_open, False, False, 0)

            box_caching.pack_start(scrolled_win, True, True, 0)
            self.notebook.append_page(box_caching, Gtk.Label(_('Caching')))
            box_caching.show_all()
        else:
            self.notebook.append_page(scrolled_win, Gtk.Label(list_name))
            scrolled_win.show_all()
        self.tabs[list_name] = scrolled_win

    # Side Panel
    def on_tree_selection_left_changed(self, tree_sel):
        model, tree_iter = tree_sel.get_selected()
        path = model.get_path(tree_iter)
        if path is None:
            return
        index = path.get_indices()[0]
        self.notebook.set_current_page(index)

    def on_treeview_left_drag_data_received(self, treeview, drag_context,
                                            x, y, sel_data, info,
                                            event_time):
        model = treeview.get_model()
        data = sel_data.get_text()
        if not data:
            return
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if not drop_info:
            return
        path = drop_info[0]
        songs = json.loads(data)
        list_name = model[path][1]
        liststore = self.tabs[list_name].liststore
        for song in songs:
            liststore.append(song)

    # Open API for others to call.
    def play_song(self, song, list_name='Default', use_mv=False):
        if not song:
            return
        if not list_name:
            list_name = 'Default'
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path > -1:
            # curr_playing contains: listname, path
            self.curr_playing = [list_name, path]
            song = Widgets.song_row_to_dict(liststore[path], start=0)
        else:
            liststore.append(Widgets.song_dict_to_row(song))
            self.curr_playing = [list_name, len(liststore)-1, ]
            self.locate_curr_song(popup_page=False)
        if use_mv is True:
            self.app.player.load_mv(song)
        else:
            self.app.player.load(song)

    def play_songs(self, songs):
        if not songs or songs:
            return
        self.add_songs_to_playlist(songs, list_name='Default')
        self.play_song(songs[0])

    def add_song_to_playlist(self, song, list_name='Default'):
        liststore = self.tabs[list_name].liststore
        if self.check_song_in_playlist(song, list_name):
            return
        liststore.append(Widgets.song_dict_to_row(song))

    def remove_song_from_playlist(self, song, list_name):
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path == -1:
            return
        liststore.remove(liststore[path].iter)

    def check_song_in_playlist(self, song, list_name):
        '''Check whether this song is in this playlist'''
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path > -1:
            return True
        else:
            return False

    def add_songs_to_playlist(self, songs, list_name='Default'):
        def start():
            tree.freeze_child_notify()
            for song in songs:
                rid = song['rid']
                path = self.get_song_path_in_liststore(liststore, rid)
                if path > -1:
                    continue
                liststore.append(Widgets.song_dict_to_row(song))

        def stop(*args):
            tree.thaw_child_notify()
            Gdk.Window.process_all_updates()

        liststore = self.tabs[list_name].liststore
        tree = self.tabs[list_name].treeview
        Net.async_call(start, stop)

    # Open API
    def cache_song(self, song):
        rid = song['rid']
        liststore = self.tabs['Caching'].liststore
        liststore.append(Widgets.song_dict_to_row(song))
        if not self.cache_enabled:
            self.switch_caching_daemon()

    # Open API
    def cache_songs(self, songs):
        for song in songs:
            self.cache_song(song)

    def open_cache_folder(self, btn):
        Utils.open_folder(self.app.conf['song-dir'])

    # song cache daemon
    def switch_caching_daemon(self, *args):
        if not self.cache_enabled:
            self.cache_enabled = True
            self.button_start.set_label(_('Stop Cache Service'))
            self.do_cache_song_pool()
        else:
            self.cache_enabled = False
            self.button_start.set_label(_('Start Cache Service'))

    def do_cache_song_pool(self):
        def _move_song():
            try:
                liststore.remove(liststore[path].iter)
            except IndexError:
                pass
            Gdk.Window.process_all_updates()

        def _on_disk_error(widget, song_path, eror=None):
            self.cache_enabled = False
            GLib.idle_add(
                    Widgets.filesystem_error,
                    self.app.window,
                    song_path)

        def _on_network_error(widget, song_link, error=None):
            self.cache_enabled = False
            GLib.idle_add(
                    Widgets.network_error,
                    self.app.window,
                    _('Failed to cache song'))

        def _on_downloaded(widget, song_path, error=None):
            if song_path:
                GLib.idle_add(_move_song)
            if self.cache_enabled:
                GLib.idle_add(self.do_cache_song_pool)

        if not self.cache_enabled:
            return

        list_name = 'Caching'
        liststore = self.tabs[list_name].liststore
        path = 0
        if len(liststore) == 0:
            print('Caching playlist is empty, please add some songs')
            self.switch_caching_daemon()
            Notify.init('kwplayer-cache')
            notify = Notify.Notification.new(
                    'Kwplayer',
                    _('All songs in caching list have been downloaded.'),
                    'kwplayer')
            notify.show()
            return
        song = Widgets.song_row_to_dict(liststore[path], start=0)
        print('will download:', song)
        self.cache_job = Net.AsyncSong(self.app)
        self.cache_job.connect('downloaded', _on_downloaded)
        self.cache_job.connect('disk-error', _on_disk_error)
        self.cache_job.connect('network-error', _on_network_error)
        self.cache_job.get_song(song)

    # Others
    def on_song_downloaded(self, play=False):
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song = Widgets.song_row_to_dict(liststore[path], start=0)
        Gdk.Window.process_all_updates()

    def get_prev_song(self, repeat):
        list_name = self.curr_playing[0]
        if not list_name:
            return None
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song_nums = len(liststore)
        if song_nums == 0:
            return None
        if path == 0:
            if repeat:
                path = song_nums - 1
            else:
                path = 0
        else:
            path = path - 1
        self.prev_playing = path
        return Widgets.song_row_to_dict(liststore[path], start=0)

    def get_next_song(self, repeat, shuffle):
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song_nums = len(liststore)
        if song_nums == 0:
            return None
        if shuffle:
            path = random.randint(0, song_nums-1)
        elif path == song_nums - 1:
            if not repeat:
                return None
            path = 0
        else:
            path = path + 1

        self.next_playing = path
        return Widgets.song_row_to_dict(liststore[path], start=0)

    def play_prev_song(self, repeat, use_mv=False):
        prev_song = self.get_prev_song(repeat)
        if not prev_song:
            return
        self.curr_playing[1] = self.prev_playing
        self.locate_curr_song(popup_page=False)
        if use_mv:
            self.app.player.load_mv(prev_song)
        else:
            self.app.player.load(prev_song)

    def play_next_song(self, repeat, shuffle, use_mv=False):
        next_song = self.get_next_song(repeat, shuffle)
        if not next_song:
            return
        self.curr_playing[1] = self.next_playing
        self.locate_curr_song(popup_page=False)
        if use_mv:
            self.app.player.load_mv(next_song)
        else:
            self.app.player.load(next_song)

    def locate_curr_song(self, popup_page=True):
        '''switch current playlist and select curr_song.'''
        list_name = self.curr_playing[0]
        if not list_name:
            return
        treeview = self.tabs[list_name].treeview
        liststore = treeview.get_model()
        path = self.curr_playing[1]
        treeview.set_cursor(path)

        for left_path, item in enumerate(self.liststore_left):
            if list_name == self.liststore_left[left_path][1]:
                selection_left = self.treeview_left.get_selection()
                selection_left.select_path(left_path)
                break
        if popup_page:
            self.app.popup_page(self.app_page)

    def get_song_path_in_liststore(self, liststore, rid, pos=3):
        for i, row in enumerate(liststore):
            if row[pos] == rid:
                return i
        return -1


    # left panel
    def on_list_disname_edited(self, cell, path, new_name):
        if not new_name:
            return
        old_name = self.liststore_left[path][0]
        self.liststore_left[path][0] = new_name

    def on_add_playlist_button_clicked(self, button):
        list_name = str(time.time())
        disname = _('Playlist')
        editable = True
        tooltip = Widgets.escape(disname)
        _iter = self.liststore_left.append(
                [disname, list_name, editable, tooltip])
        selection = self.treeview_left.get_selection()
        selection.select_iter(_iter)
        self.init_tab(list_name, [])

    def on_remove_playlist_button_clicked(self, button):
        selection = self.treeview_left.get_selection()
        model, _iter = selection.get_selected()
        if not _iter:
            return
        path = model.get_path(_iter)
        index = path.get_indices()[0]
        disname, list_name, editable, tooltip = model[path]
        if not editable:
            return
        self.notebook.remove_page(index)
        model.remove(_iter)

    def on_export_playlist_button_clicked(self, button):
        selection = self.treeview_left.get_selection()
        model, _iter = selection.get_selected()
        if not _iter:
            return
        path = model.get_path(_iter)
        index = path.get_indices()[0]
        disname, list_name, editable, tooltip = model[path]
        liststore = self.tabs[list_name].liststore

        export_dialog = ExportDialog(self, liststore)
        export_dialog.run()
        export_dialog.destroy()

    def advise_new_playlist_name(self, disname):
        self.playlist_advice_disname = disname

    def on_advice_menu_item_activated(self, advice_item):
        list_name = str(time.time())
        tooltip = Widgets.escape(self.playlist_advice_disname)
        self.liststore_left.append(
                [self.playlist_advice_disname, list_name, True, tooltip])
        self.init_tab(list_name, [])
        advice_item.list_name = list_name
        self.on_menu_item_activated(advice_item)

    def on_menu_item_activated(self, menu_item):
        list_name = menu_item.list_name
        songs = menu_item.get_parent().songs
        self.add_songs_to_playlist(songs, list_name)

    def popup_playlist_menu(self, button, songs):
        menu = self.playlist_menu
        while menu.get_children():
            menu.remove(menu.get_children()[0])

        for item in self.liststore_left:
            if item[1] in ('Caching', ):
                continue
            menu_item = Gtk.MenuItem(item[0])
            menu_item.list_name = item[1]
            menu_item.connect('activate', self.on_menu_item_activated)
            menu.append(menu_item)

        if self.playlist_advice_disname:
            sep_item = Gtk.SeparatorMenuItem()
            menu.append(sep_item)
            advice_item = Gtk.MenuItem('+ ' + self.playlist_advice_disname)
            advice_item.connect(
                    'activate', self.on_advice_menu_item_activated)
            advice_item.set_tooltip_text(
                    _('Create this playlist and add songs into it'))
            menu.append(advice_item)

        menu.songs = songs
        menu.show_all()
        menu.popup(None, None, None, None, 1, Gtk.get_current_event_time())
