
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import dbus
import dbus.service


BUS_NAME = 'org.mpris.MediaPlayer2.kwplayer'
MPRIS_PATH = '/org/mpris/MediaPlayer2'
ROOT_IFACE = 'org.mpris.MediaPlayer2'
PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
PLAYLIST_IFACE = 'org.mpris.MediaPlayer2.Playlists'

class PlayerDBus:
    '''Implements MPRIS DBus Interface v2.2'''

    def __init__(self, player):
        self.player = player
        self.app = player.app
        session_bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(BUS_NAME, bus=session_bus)
        mpris_path = dbus.service.ObjectPath(MPRIS_PATH)
        super().__init__(bus_name=bus_name, object_path=mpris_path)

    # root iface methods
    @dbus.service.method(ROOT_IFACE)
    def Quit(self):
        self.app.quit()

    @dbus.service.method(ROOT_IFACE)
    def Raise(self):
        self.app.window.present()

    # player iface methods
    @dbus.service.method(PLAYER_IFACE)
    def Next(self):
        self.player.load_next()

    @dbus.service.method(PLAYER_IFACE)
    def Previous(self):
        self.player.load_prev()

    @dbus.service.method(PLAYER_IFACE)
    def Pause(self):
        self.player.pause_player()

    @dbus.service.method(PLAYER_IFACE)
    def PlayPause(self):
        self.player.play_pause()

    @dbus.service.method(PLAYER_IFACE)
    def Stop(self):
        self.player.stop_player()

    @dbus.service.method(PLAYER_IFACE)
    def Play(self):
        self.player.start_player()

    @dbus.service.method(PLAYER_IFACE, in_signature='x')
    def Seek(self, offset):
        # Note: offset unit is microsecond, but player.seek() requires
        # nanoseconds as time unit
        self.player.seek(offset*1000)

    @dbus.service.method(PLAYER_IFACE, in_signature='s')
    def OpenUri(self, uri):
        pass
    
    # player iface signals
    @dbus.service.signal(PLAYER_IFACE, in_signature='x')
    def Seeked(self, offset):
        print('PlayerDBus.Seeked signal emited')
