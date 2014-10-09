
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import os
import random
import shutil
import threading
import time
import traceback

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

from kuwo import Config
_ = Config._
from kuwo import Net
from kuwo import Utils
from kuwo import Widgets
from kuwo.log import logger

DRAG_TARGETS = [
    ('text/plain', Gtk.TargetFlags.SAME_APP, 0),
    ('TEXT', Gtk.TargetFlags.SAME_APP, 1),
    ('STRING', Gtk.TargetFlags.SAME_APP, 2),
]
DRAG_ACTIONS = Gdk.DragAction.MOVE

def get_song_paths(artist, name, conf):
    song_name = (artist + '-' + name).replace('/', '+')
    return (
        os.path.join(conf['song-dir'], song_name) + '.mp3',
        os.path.join(conf['song-dir'], song_name) + '.flac',
        os.path.join(conf['mv-dir'], song_name) + '.mp4',
    )


class TreeViewColumnText(Widgets.TreeViewColumnText):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.props.clickable = True
        self.props.reorderable = True
        self.props.sort_indicator = True
        self.props.sort_column_id = kwds['text']


class NormalSongTab(Gtk.ScrolledWindow):

    NAME, ARTIST, ALBUM, RID, ARTISTID, ALBUMID, FORMATS = list(range(7))
    COL_NAME, COL_ARTIST, COL_ALBUM, COL_DELETE = list(range(4))

    def __init__(self, app, list_name):
        super().__init__()
        self.app = app
        self.list_name = list_name

        # name, artist, album, rid, artistid, albumid, formats
        self.liststore = Gtk.ListStore(str, str, str, int, int, int, str)

        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        self.treeview.set_search_column(self.COL_NAME)
        self.treeview.props.headers_clickable = True
        self.treeview.props.headers_visible = True
        self.treeview.props.reorderable = True
        self.treeview.props.rules_hint = True
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                               DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview.connect('drag-data-get', self.on_drag_data_get)
        self.treeview.enable_model_drag_dest(DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview.connect('drag-data-received', self.on_drag_data_received)
        self.treeview.connect('row_activated', self.on_treeview_row_activated)
        self.add(self.treeview)

        song_cell = Gtk.CellRendererText()
        song_col = TreeViewColumnText(_('Title'), song_cell,
                                      text=self.COL_NAME)
        self.treeview.append_column(song_col)

        artist_cell = Gtk.CellRendererText()
        artist_col = TreeViewColumnText(_('Aritst'), artist_cell,
                                        text=self.COL_ARTIST)
        self.treeview.append_column(artist_col)

        album_cell = Gtk.CellRendererText()
        album_col = TreeViewColumnText(_('Album'), album_cell,
                                       text=self.COL_ALBUM)
        self.treeview.append_column(album_col)

        delete_cell = Gtk.CellRendererPixbuf(icon_name='user-trash-symbolic')
        self.delete_col = Widgets.TreeViewColumnIcon(_('Delete'), delete_cell)
        self.treeview.append_column(self.delete_col)
        self.treeview.connect('key-press-event', self.on_treeview_key_pressed)
        self.treeview.connect('button-press-event',
                              self.on_treeview_button_pressed)
        self.treeview.connect('button-release-event',
                              self.on_treeview_button_released)

        self.popup_menu = Gtk.Menu()
        save_as_menu = Gtk.MenuItem(_('Save As..'))
        save_as_menu.connect('activate', self.on_save_as_menu_activated)
        self.popup_menu.append(save_as_menu)
        sep = Gtk.SeparatorMenuItem()
        self.popup_menu.append(sep)
        delete_song_menu = Gtk.MenuItem(_('Delete from Playlist'))
        delete_song_menu.connect('activate',
                                 self.on_delete_song_menu_activated)
        self.popup_menu.append(delete_song_menu)
        delete_cache_menu = Gtk.MenuItem(_('Delete Local Cache'))
        delete_cache_menu.connect('activate',
                                  self.on_delete_cache_menu_activated)
        self.popup_menu.append(delete_cache_menu)
        
    def on_treeview_key_pressed(self, treeview, event):
        if event.keyval == Gdk.KEY_Delete:
            model, paths = self.selection.get_selected_rows()
            # paths needs to be reversed, or else an IndexError throwed.
            for path in reversed(paths):
                model.remove(model[path].iter)

    def on_treeview_button_pressed(self, treeview, event):
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return False
        path = treeview.get_path_at_pos(event.x, event.y)
        selection = treeview.get_selection()
        if path is None:
            selection.unselect_all()
            return True

        if event.button == Gdk.BUTTON_PRIMARY:
            return False
        elif event.button == Gdk.BUTTON_SECONDARY:
            liststore, selected_paths = selection.get_selected_rows()
            self.popup_menu.show_all()
            self.popup_menu.popup(None, None, None, None, event.button,
                                  event.time)
            return True
        return False

    def on_treeview_button_released(self, treeview, event):
        path_info = treeview.get_path_at_pos(event.x, event.y)
        if not path_info:
            return
        path, column, cell_x, cell_y = path_info
        if column != self.delete_col:
            return
        self.liststore.remove(self.liststore.get_iter(path))

    def on_treeview_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = Widgets.song_row_to_dict(model[path], start=0)
        if index == self.COL_NAME:
            self.app.playlist.play_song(song, list_name=self.list_name)
        elif index == self.COL_ARTIST:
            self.app.search.search_artist(song['artist'])
        elif index == self.COL_ALBUM:
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
            tree_iter = model.get_iter(path)
            self.drag_data_old_iters.append(tree_iter)
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
        for tree_iter in self.drag_data_old_iters:
            model.remove(tree_iter)

    def on_save_as_menu_activated(self, menu_item):
        export_dialog = ExportDialog(self, self.treeview, export_all=False)
        export_dialog.run()
        export_dialog.destroy()

    def on_delete_song_menu_activated(self, menu_item):
        selection = self.treeview.get_selection()
        liststore, paths = selection.get_selected_rows()
        for path in paths:
            liststore.remove(liststore.get_iter(path))

    def on_delete_cache_menu_activated(self, menu_item):
        selection = self.treeview.get_selection()
        liststore, paths = selection.get_selected_rows()
        for path in paths:
            filepaths = get_song_paths(self.liststore[path][1],
                                       self.liststore[path][0], self.app.conf)
            for filepath in filepaths:
                if os.path.exists(filepath):
                    os.remove(filepath)


class ExportDialog(Gtk.Dialog):

    export_worker = None

    def __init__(self, parent, treeview, export_all=True):
        super().__init__(_('Export Songs'), parent.app.window,
                         Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK,))
        self.parent = parent
        self.treeview = treeview
        self.export_all = export_all
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

        self.including_lrc = Gtk.CheckButton(_('Including lyrics'))
        self.including_lrc.set_tooltip_text(
                _('Export lyrics to the same folder'))
        self.including_lrc.props.margin_top = 20
        box.pack_start(self.including_lrc, False, False, 0)

        export_box = Gtk.Box(spacing=5)
        export_box.props.margin_top = 20
        box.pack_start(export_box, False, True, 0)

        self.export_prog = Gtk.ProgressBar()
        self.export_prog.props.show_text = True
        self.export_prog.props.text = ''
        export_box.pack_start(self.export_prog, True, True, 0)

        self.export_btn = Gtk.Button(_('Export'))
        self.export_btn.connect('clicked', self.do_export)
        export_box.pack_start(self.export_btn, False, False, 0)

        infobar = Gtk.InfoBar()
        infobar.props.margin_top = 20
        box.pack_start(infobar, False, True, 0)
        info_content = infobar.get_content_area()
        info_label = Gtk.Label(_('Only cached songs will be exported'))
        info_content.pack_start(info_label, False, False, 0)
        box.show_all()

    def do_export(self, button):
        def on_song_copied(worker, name, percent):
            GLib.idle_add(do_on_song_copied, name, percent)

        def do_on_song_copied(name, percent):
            self.export_prog.set_fraction(percent)
            self.export_prog.set_text(name)

        def on_worker_finished(worker, file_nums):
            GLib.idle_add(do_on_worker_finished)

        def do_on_worker_finished():
            self.export_worker = None
            self.destroy()

        self.export_btn.set_sensitive(False)
        self.export_worker = ExportWorker(self.app.conf, self.treeview,
                                          self.folder_chooser.get_filename(),
                                          self.including_lrc.get_active(),
                                          self.export_all)

        self.export_worker.connect('copied', on_song_copied)
        self.export_worker.connect('finished', on_worker_finished)
        self.export_worker.start()

    def do_destroy(self):
        if self.export_worker:
            self.export_worker.destroy()


class ExportWorker(threading.Thread, GObject.GObject):

    stop_flag = False

    __gsignals__ = {
        'copied': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                   (str, GObject.TYPE_INT64)),  # song_name, number
        'finished': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                     (GObject.TYPE_INT64, )),  # number of songs
    }

    def __init__(self, conf, treeview, export_dir, including_lrc, export_all):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self.daemon = True

        self.conf = conf
        self.treeview = treeview
        self.export_dir = export_dir
        self.including_lrc = including_lrc
        self.export_all = export_all

    def run(self):
        selection = self.treeview.get_selection()
        liststore, selected_paths = selection.get_selected_rows()
        if self.export_all:
            file_nums = len(liststore)
            song_rows = liststore
        else:
            file_nums = len(selected_paths)
            song_rows = (liststore[path] for path in selected_paths)

        for i, item in enumerate(song_rows):
            if self.stop_flag:
                return
            song = Widgets.song_row_to_dict(item, start=0)
            cached, song_link, song_path = Net.get_song_link(song, self.conf)
            if not cached:
                continue
            shutil.copy(song_path, self.export_dir)
            if self.including_lrc:
                lrc_path, lrc_cached = Net.get_lrc_path(song)
                if lrc_cached:
                    shutil.copy(lrc_path, self.export_dir)
            self.emit('copied', song['name'], i /file_nums)
        self.emit('finished', file_nums)

    def destroy(self):
        self.stop_flag = True


class PlayList(Gtk.Box):
    '''Playlist tab in notebook.'''

    title = _('PlayList')

    def __init__(self, app):
        super().__init__()

        self.app = app
        self.tabs = {}
        # self.lists_name contains playlists name
        self.lists_name = []
        # use curr_playing to locate song in treeview, [model, iter]
        self.curr_playing = [None, None]

        # control cache job
        self.cache_enabled = False
        self.cache_job = None
        self.cache_global_count = 0
        self.cache_local_count = 0

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
        col_name = Gtk.TreeViewColumn('List Name', list_disname, text=0,
                                      editable=2)
        self.treeview_left.append_column(col_name)
        #col_name.props.max_width = 75
        #col_name.props.fixed_width = 75
        #col_name.props.min_width = 70
        col_name.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        tree_sel = self.treeview_left.get_selection()
        tree_sel.connect('changed', self.on_tree_selection_left_changed)
        self.treeview_left.enable_model_drag_dest(DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview_left.connect('drag-data-received',
                                   self.on_treeview_left_drag_data_received)
        win_left.add(self.treeview_left)

        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
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
        remove_btn.connect('clicked', self.on_remove_playlist_button_clicked)
        toolbar.insert(remove_btn, 1)
        export_btn = Gtk.ToolButton()
        export_btn.set_name('Export')
        export_btn.set_tooltip_text(_('Export songs in selected playlist'))
        export_btn.set_icon_name('media-eject-symbolic')
        export_btn.connect('clicked', self.on_export_playlist_button_clicked)
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
            self.liststore_left.append([disname, list_name, editable, tooltip])
            songs = playlists[list_name]
            self.init_tab(list_name, songs)

    def init_tab(self, list_name, songs):
        scrolled_win = NormalSongTab(self.app, list_name)
        for song in songs:
            # TODO: be compatible with v3.4.7, remove it in v3.6.1
            if len(song) == 6:
                song.append('')
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

            self.cache_speed_label = Gtk.Label()
            buttonbox.pack_start(self.cache_speed_label, False, False, 5)

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
        if not tree_iter:
            return
        path = model.get_path(tree_iter)
        index = path.get_indices()[0]
        self.notebook.set_current_page(index)

    def on_treeview_left_drag_data_received(self, treeview, drag_context, x,
                                            y, sel_data, info, event_time):
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
            self.curr_playing = [list_name, liststore.get_iter(path)]
            song = Widgets.song_row_to_dict(liststore[path], start=0)
        else:
            liststore.append(Widgets.song_dict_to_row(song))
            self.curr_playing = [
                    list_name, liststore.get_iter(len(liststore) - 1)]
            #self.locate_curr_song(popup_page=False)
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
        return path > -1

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
        Net.async_call(start, callback=stop)

    # Open API
    def cache_song(self, song):
        '''Add song to cache playlist'''
        rid = song['rid']
        liststore = self.tabs['Caching'].liststore
        liststore.append(Widgets.song_dict_to_row(song))
        self.start_caching_daemon()

    # Open API
    def cache_songs(self, songs):
        for song in songs:
            self.cache_song(song)

    def open_cache_folder(self, btn):
        Utils.open_folder(self.app.conf['song-dir'])

    # song cache daemon
    def switch_caching_daemon(self, button):
        if self.cache_enabled:
            self.stop_caching_daemon()
        else:
            self.start_caching_daemon()

    def check_caching_daemon(self):
        '''Caching daemon monitor'''
        if not self.cache_enabled:
            return False
        if self.cache_local_count > self.cache_global_count:
            self.cache_global_count = self.cache_local_count
            return True
        else:
            # restart caching daemon in 5 seconds
            self.stop_caching_daemon()
            GLib.timeout_add(5000, self.start_caching_daemon)
            return False

    def start_caching_daemon(self):
        if not self.cache_enabled:
            self.cache_speed_label.show()
            self.cache_enabled = True
            self.cache_global_count = 0
            self.cache_local_count = 0
            self.button_start.set_label(_('Stop Cache Service'))
            GLib.timeout_add(30000, self.check_caching_daemon)
            self.do_cache_song_pool()

    def stop_caching_daemon(self):
        self.cache_enabled = False
        self.cache_global_count = 0
        self.cache_local_count = 0
        self.cache_speed_label.hide()
        self.button_start.set_label(_('Start Cache Service'))
        if self.cache_job:
            self.cache_job.destroy()
            self.cache_job = None

    def do_cache_song_pool(self):
        def _remove_song():
            try:
                liststore.remove(liststore[path].iter)
            except IndexError:
                logger.error(traceback.format_exc())
            Gdk.Window.process_all_updates()

        def _on_disk_error(widget, song_path, eror=None):
            self.stop_caching_daemon()
            GLib.idle_add(Widgets.filesystem_error, self.app.window, song_path)

        def _on_network_error(widget, song_link, error=None):
            self.stop_caching_daemon()
            GLib.idle_add(Widgets.network_error, self.app.window,
                          _('Failed to cache song'))

        def _on_chunk_received(widget, percent):
            GLib.idle_add(do_on_chunk_received, percent)

        def do_on_chunk_received(percent):
            self.cache_local_count += 1
            self.cache_speed_label.set_text('{0} %'.format(int(percent * 100)))

        def _on_downloaded(widget, song_path, error=None):
            if song_path:
                GLib.idle_add(_remove_song)
            if self.cache_enabled:
                GLib.idle_add(self.do_cache_song_pool)

        if not self.cache_enabled:
            return
        self.cache_local_count = 0
        self.cache_global_count = 0
        self.cache_speed_label.set_text('0 %')
        list_name = 'Caching'
        liststore = self.tabs[list_name].liststore
        path = 0
        if len(liststore) == 0:
            logger.info('Caching playlist is empty, please add some songs')
            self.stop_caching_daemon()
            Notify.init('kwplayer-cache')
            notify = Notify.Notification.new('Kwplayer',
                    _('All songs in caching list have been downloaded.'),
                    'kwplayer')
            notify.show()
            return
        song = Widgets.song_row_to_dict(liststore[path], start=0)
        logger.debug('will download: %s' % song)
        self.cache_job = Net.AsyncSong(self.app)
        self.cache_job.connect('chunk-received', _on_chunk_received)
        self.cache_job.connect('downloaded', _on_downloaded)
        self.cache_job.connect('disk-error', _on_disk_error)
        self.cache_job.connect('network-error', _on_network_error)
        self.cache_job.get_song(song)

    # Others
    def on_song_downloaded(self, play=False):
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        iter_ = self.curr_playing[1]
        path = liststore.get_path(iter_)
        song = Widgets.song_row_to_dict(liststore[path], start=0)
        Gdk.Window.process_all_updates()

    def get_prev_song(self, repeat):
        list_name = self.curr_playing[0]
        if not list_name:
            return None
        liststore = self.tabs[list_name].liststore
        song_nums = len(liststore)
        if song_nums == 0:
            return None

        iter_ = self.curr_playing[1]
        path = liststore.get_path(iter_)
        pos = int(str(path))
        if pos == 0:
            if repeat:
                pos = song_nums - 1
            else:
                pos = 0
        else:
            pos = pos - 1
        self.prev_playing = liststore.get_iter(Gtk.TreePath(pos))
        return Widgets.song_row_to_dict(liststore[pos], start=0)

    def get_next_song(self, repeat, shuffle):
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        song_nums = len(liststore)
        if song_nums == 0:
            return None

        iter_ = self.curr_playing[1]
        path = liststore.get_path(iter_)
        pos = int(str(path))
        if shuffle:
            pos = random.randint(0, song_nums-1)
        elif pos == song_nums - 1:
            if not repeat:
                return None
            pos = 0
        else:
            pos = pos + 1

        self.next_playing = liststore.get_iter(Gtk.TreePath(pos))
        return Widgets.song_row_to_dict(liststore[pos], start=0)

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
        if len(liststore) == 0:
            return None

        iter_ = self.curr_playing[1]
        path = liststore.get_path(iter_)
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
            if row and row[pos] == rid:
                return i
        return -1


    # left panel
    def on_list_disname_edited(self, cell, path, new_name):
        if not new_name:
            return
        self.liststore_left[path][0] = new_name

    def on_add_playlist_button_clicked(self, button):
        list_name = str(time.time())
        disname = _('Playlist')
        editable = True
        tooltip = Widgets.escape(disname)
        _iter = self.liststore_left.append([disname, list_name, editable,
                                            tooltip])
        selection = self.treeview_left.get_selection()
        selection.select_iter(_iter)
        self.init_tab(list_name, [])

    def on_remove_playlist_button_clicked(self, button):
        selection = self.treeview_left.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter:
            return
        path = model.get_path(tree_iter)
        index = path.get_indices()[0]
        disname, list_name, editable, tooltip = model[path]
        if not editable:
            return
        self.notebook.remove_page(index)
        model.remove(tree_iter)

    def on_export_playlist_button_clicked(self, button):
        selection = self.treeview_left.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter:
            return
        song_tab = self.notebook.get_nth_page(self.notebook.get_current_page())
        treeview = song_tab.treeview

        export_dialog = ExportDialog(self, treeview)
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
            advice_item.connect('activate', self.on_advice_menu_item_activated)
            advice_item.set_tooltip_text(
                    _('Create this playlist and add songs into it'))
            menu.append(advice_item)

        menu.songs = songs
        menu.show_all()
        menu.popup(None, None, None, None, 1, Gtk.get_current_event_time())
