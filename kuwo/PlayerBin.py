
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstVideo


# Or init threads in another place.
GObject.threads_init()
# init Gst so that play works ok.
Gst.init(None)
GST_LOWER_THAN_1 = (Gst.version()[0] < 1)


class PlayerBin(GObject.GObject):
    
    __gsignals__ = {
            'eos': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (bool, )),
            'error': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (str, )),
            }
    xid = None
    bus_sync_sid = 0

    def __init__(self):
        super().__init__()
        self.playbin = Gst.ElementFactory.make('playbin', None)
        if self.playbin is None:
            print('Gst Error: playbin failed to inited, abort!')
            sys.exit(1)
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

    # Open APIs
    def load_audio(self, uri):
        self.set_uri(uri)
        self.disable_bus_sync()
        self.play()

    def load_video(self, uri, xid):
        self.set_uri(uri)
        self.set_xid(xid)
        self.enable_bus_sync()
        self.play()

    def destroy(self):
        self.quit()

    def quit(self):
        self.stop()

    def play(self):
        self.playbin.set_state(Gst.State.PLAYING)

    def pause(self):
        self.playbin.set_state(Gst.State.PAUSED)

    def stop(self):
        self.playbin.set_state(Gst.State.NULL)

    def get_status(self):
        return self.playbin.get_state(5)[1]

    def is_playing(self):
        return self.get_status() == Gst.State.PLAYING

    def set_uri(self, uri):
        self.playbin.set_property('uri', uri)

    def get_uri(self):
        return self.playbin.get_property('uri')

    def get_position(self):
        if GST_LOWER_THAN_1:
            status, _type, pos = self.playbin.query_position(
                Gst.Format.TIME)
        else:
            status, pos = self.playbin.query_position(Gst.Format.TIME)
        return (status, pos)

    def set_position(self, pos):
        self.seek(pos)

    def seek(self, pos):
        self.playbin.seek_simple(Gst.Format.TIME, 
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, pos)

    def get_duration(self):
        if GST_LOWER_THAN_1:
            status, _type, upper = self.playbin.query_duration(
                Gst.Format.TIME)
        else:
            status, upper = self.playbin.query_duration(Gst.Format.TIME)
        return (status, upper)

    def set_xid(self, xid):
        self.xid = xid

    def get_xid(self):
        return self.xid

    def set_volume(self, vol):
        self.playbin.set_property('volume', vol)

    def get_volume(self):
        return self.playbin.get_property('volume')

    # private functions
    def enable_bus_sync(self):
        self.bus.enable_sync_message_emission()
        # this signal never emited in gtk3 and gstreamer0.10, it is a bug
        # found in 2010 and not fixed.
        self.bus_sync_sid = self.bus.connect('sync-message::element', 
                self.on_sync_message)

    def disable_bus_sync(self):
        if self.bus_sync_sid > 0:
            self.bus.disconnect(self.bus_sync_sid)
            self.bus.disable_sync_message_emission()
            self.bus_sync_sid = 0

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)

    def on_eos(self, bus, msg):
        self.emit('eos', True)

    def on_error(self, bus, msg):
        error_msg = msg.parse_error()
        print('on_error():', error_msg)
        self.emit('error', error_msg)

GObject.type_register(PlayerBin)
