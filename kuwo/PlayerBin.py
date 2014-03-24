
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import sys
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstVideo
from gi.repository import Gtk

# init Gst so that play works ok.
Gst.init(None)
GST_LOWER_THAN_1 = (Gst.version()[0] < 1)


class PlayerBin(GObject.GObject):
    '''Gstreamer wrapper.

    PlayerBin uses playbin as GstPipeline.
    '''
    
    __gsignals__ = {
            'eos': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (bool, )),
            'error': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (str, )),
            'mute-changed': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (bool, )),
            'volume-changed': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (float, )),
            }
    xid = None
    bus_sync_sid = 0
    audio_stream = 0

    def __init__(self):
        super().__init__()
        self.playbin = Gst.ElementFactory.make('playbin', None)
        screen = Gdk.Screen.get_default()
        self.fullscreen_rect = (0, 0, screen.width(), screen.height())
        
        if not self.playbin:
            print('Gst Error: playbin failed to be inited, abort!')
            sys.exit(1)
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)
        self.volume_sid = self.playbin.connect(
                'notify::volume', self.on_volume_changed)
        self.mute_sid = self.playbin.connect(
                'notify::mute', self.on_mute_changed)

    # Open APIs
    def load_audio(self, uri):
        self.set_uri(uri)
        self.disable_bus_sync()
        self.play()

    def load_video(self, uri, xid, audio_stream):
        print('load_video:', audio_stream)
        self.set_uri(uri)
        self.set_xid(xid)
        self.enable_bus_sync()
        self.play()
        GLib.timeout_add(2000, self.set_current_audio, audio_stream)

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
            status, _type, offset = self.playbin.query_position(
                Gst.Format.TIME)
        else:
            status, offset = self.playbin.query_position(Gst.Format.TIME)
        return (status, offset)

    def set_position(self, offset):
        self.seek(offset)
        #self.set_current_audio(self.audio_stream)

    def seek(self, offset):
        self.playbin.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                offset)

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
        self.playbin.handler_block(self.volume_sid)
        self.playbin.handler_block(self.mute_sid)
        self.playbin.set_property('volume', vol)
        self.playbin.handler_unblock(self.volume_sid)
        self.playbin.handler_unblock(self.mute_sid)

    def get_volume(self):
        return self.playbin.get_property('volume')

    def set_mute(self, mute):
        self.playbin.handler_block(self.mute_sid)
        self.playbin.set_property('mute', mute)
        self.playbin.handler_unblock(self.mute_sid)

    def get_mute(self):
        return self.playbin.get_property('mute')

    def set_current_audio(self, audio_stream):
        print('set_current_audio:', audio_stream)
        if self.get_audios() <= audio_stream:
            return
        self.playbin.props.current_audio = audio_stream

    def get_current_audio(self):
        return self.playbin.props.current_audio

    def get_audios(self):
        return self.playbin.props.n_audio

    # private functions
    def enable_bus_sync(self):
        self.bus.enable_sync_message_emission()
        self.bus_sync_sid = self.bus.connect(
                'sync-message::element', self.on_sync_message)

    def disable_bus_sync(self):
        if self.bus_sync_sid > 0:
            self.bus.disconnect(self.bus_sync_sid)
            self.bus.disable_sync_message_emission()
            self.bus_sync_sid = 0

    def on_sync_message(self, bus, msg):
        if not msg.get_structure():
            return
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)
            msg.src.handle_events(False)
            msg.src.set_property('force-aspect-ratio', True)

    def expose(self, rect=None):
        '''Redraw video frame.

        This should be used when video overlay is resized.
        '''
        if self.bus_sync_sid == 0:
            return
        videosink = self.playbin.props.video_sink
        if not videosink:
            return
        if not rect:
            # reset to default size, used in window mode
            videosink.set_render_rectangle(0, 0, -1, -1)
        else:
            videosink.set_render_rectangle(*rect)
        videosink.expose()

    def expose_fullscreen(self):
        '''Redraw when in fullscreen mode'''
        self.expose(self.fullscreen_rect)

    def on_eos(self, bus, msg):
        self.emit('eos', True)

    def on_error(self, bus, msg):
        error_msg = msg.parse_error()
        self.emit('error', error_msg)

    def on_volume_changed(self, playbin, volume_name):
        self.emit('volume-changed', self.get_volume())

    def on_mute_changed(self, playbin, mute_name):
        self.emit('mute-changed', self.get_mute())

GObject.type_register(PlayerBin)
