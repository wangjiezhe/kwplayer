
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import dbus
import dbus.service
import dbus.mainloop.glib
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
import json

GObject.threads_init()
dbus.mainloop.glib.threads_init()

BUS_NAME = 'org.mpris.MediaPlayer2.kwplayer'
MPRIS_PATH = '/org/mpris/MediaPlayer2'
ROOT_IFACE = 'org.mpris.MediaPlayer2'
PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'

# TODO:
URI_SCHEMES = ['file', 'http', 'smb']
MIME_TYPES = ['application/ogg', ]


class PlayerDBus(dbus.service.Object):
    '''Implements MPRIS DBus Interface v2.2'''

    properties = None

    def __init__(self, player):
        self.player = player
        self.app = player.app
        loop = DBusGMainLoop(set_as_default=True)
        session_bus = dbus.SessionBus(loop)
        bus_name = dbus.service.BusName(BUS_NAME, bus=session_bus)
        mpris_path = dbus.service.ObjectPath(MPRIS_PATH)
        super().__init__(bus_name=bus_name, object_path=mpris_path)

        self.properties = {
                ROOT_IFACE: self._get_root_iface_properties(),
                PLAYER_IFACE: self._get_player_iface_properties(),
                }

    def _get_root_iface_properties(self):
        return {
            'CanQuit': (True, None),
            'Fullscreen': (False, None),
            'CanSetFullscreen': (False, None),
            'CanRaise': (True, None),
            'HasTrackList': (False, None),
            'Identity': ('KW Player', None),
            'DesktopEntry': ('kwplayer', None),
            'SupportedUriSchemes': 
                (dbus.Array(URI_SCHEMES, signature='s'), None),
            #'SupportedMimeTypes': (dbus.Array([], signature='s'), None),
            'SupportedMimeTypes':
                (dbus.Array(MIME_TYPES, signature='s'), None),
        }

    def _get_player_iface_properties(self):
        return {
            'PlaybackStatus': (self.get_PlaybackStatus, None),
            'LoopStatus': ('None', self.set_LoopStatus),
            'Rate': (1.0, self.set_Rate),
            'Shuffle': (self.get_Shuffle, self.set_Shuffle),
            'Metadata': (self.get_Metadata, None),
            'Volume': (self.get_Volume, self.set_Volume),
            'Position': (self.get_Position, None),
            'MinimumRate': (1.0, None),
            'MaximumRate': (1.0, None),
            'CanGoNext': (True, None),
            'CanGoPrevious': (self.get_CanGoPrevious, None),
            'CanPlay': (self.get_CanPlay, None),
            'CanPause': (True, None),
            'CanSeek': (False, None),
            'CanControl': (True, None),
        }

    # interface properties
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss',
            out_signature='v')
    def Get(self, interface, prop):
        (getter, _) = self.properties[interface][prop]
        if callable(getter):
            return getter()
        else:
            return getter

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s',
            out_signature='a{sv}')
    def GetAll(self, interface):
        getters = {}
        for key, (getter, _) in self.properties[interface].items():
            getters[key] = getter() if callable(getter) else getter
        return getters

    @dbus.service.method(dbus.PROPERTIES_IFACE,
            in_signature='ssv', out_signature='')
    def Set(self, interface, prop, value):
        _, setter = self.properties[interface][prop]
        if setter is not None:
            setter(value)
            self.PropertiesChanged(interface,
                    {prop: self.Get(interface, prop)}, [])

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties,
            invalidated_properties):
        pass

    # root iface methods
    @dbus.service.method(ROOT_IFACE)
    def Quit(self):
        self.app.quit()

    @dbus.service.method(ROOT_IFACE)
    def Raise(self):
        self.app.window.present()

    # player iface methods
    @dbus.service.method(PLAYER_IFACE)
    def Previous(self):
        self.player.load_prev_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Next(self):
        self.player.load_next_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Pause(self):
        self.player.pause_player_cb()

    @dbus.service.method(PLAYER_IFACE)
    def PlayPause(self):
        self.player.play_pause_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Stop(self):
        self.player.stop_player_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Play(self):
        self.player.start_player_cb()

    @dbus.service.method(PLAYER_IFACE, in_signature='x')
    def Seek(self, offset):
        # Note: offset unit is microsecond, but player.seek() requires
        # nanoseconds as time unit
        self.player.seek_cb(offset*1000)

    @dbus.service.method(PLAYER_IFACE, in_signature='s')
    def OpenUri(self, uri):
        pass
    
    # player iface signals
    @dbus.service.signal(PLAYER_IFACE, signature='x')
    def Seeked(self, offset):
        pass

    @dbus.service.method(PLAYER_IFACE)
    def SetPosition(self, track_id, offset):
        self.Seek()

    # does not have playlists or tracklist

    # player properties
    def get_PlaybackStatus(self):
        if self.player.is_playing():
            return 'Playing'
        return 'Paused'

    def set_LoopStatus(self, value):
        pass

    def set_Rate(self, rate):
        pass

    def get_Shuffle(self):
        return self.player.shuffle_btn.get_active()

    def set_Shuffle(self):
        self.player.shuffle_btn.set_active(True)

    def get_Metadata(self):
        song = self.player.curr_song
        if song is None:
            return {'mpris:trackid': ''}

        artUrl = self.player.meta_artUrl

        meta_obj = {
                'xesam:genre': ['', ],
                'xesam:userCount': 1,
                'xesam:trackNumber': 1,
                #'xesam:comment': ['by kwplayer'],
                #'xesam:contentCreated': '2008-01-01T00:00:00Z',
                'xesam:userRating': 0.0,
                #'xesam:lastUsed': '2013-01-01T00:00:00Z',
                'mpris:trackid': '',

                'xesam:title': song['name'],
                'xesam:artist': 
                    dbus.Array(song['artist'].split('&'), signature='s'),
                'xesam:album': song['album'],
                'xesam:url': self.player.meta_url,
                'mpris:length': self.get_Length(),
                'mpris:artUrl': 'file://' + artUrl if artUrl != '' else ''
                }
        return dbus.Dictionary(meta_obj, signature='sv')


    def get_Volume(self):
        return self.player.get_volume()

    def set_Volume(self, volume):
        self.player.set_volume_cb(volume)

    def get_Position(self):
        pos = self.player.playbin.get_position()[1] // 1000
        return pos

    def get_CanGoPrevious(self):
        return self.player.can_go_previous()

    def get_CanPlay(self):
        return True
        state = self.player.playbin.get_status()
        if state in (Gst.State.PLAYING, Gst.State.PAUSED):
            return True
        return False

    def get_CanSeek(self):
        if self.player.scale.get_sensitive():
            return True
        return False

    def update_pos(self, pos):
        self.Seeked(pos)

    def set_Playing(self):
        self.PropertiesChanged(PLAYER_IFACE,
                {'PlaybackStatus': 'Playing'}, [])
        self.update_meta()

    def set_Pause(self):
        self.PropertiesChanged(PLAYER_IFACE,
                {'PlaybackStatus': 'Paused'}, [])

    def get_Length(self):
        length = self.player.adjustment.get_upper()
        mod_len = int(divmod(length, 10**9)[0])
        return mod_len*10**6

    def update_meta(self):
        meta = self.get_Metadata()
        self.PropertiesChanged(PLAYER_IFACE,
                {'Metadata': meta}, [])

    def enable_seek(self):
        self.PropertiesChanged(PLAYER_IFACE, {'CanSeek': True}, [])

    def disable_seek(self):
        self.PropertiesChanged(PLAYER_IFACE, {'CanSeek': False}, [])
