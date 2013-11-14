
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


from gi.repository import GLib
from gi.repository import Notify

from kuwo import Config
from kuwo import Widgets

Notify.init('kwplayer')
_ = Config._

class PlayerNotify:
    def __init__(self, player):
        self.player = player
        self.notify = Notify.Notification.new('', '', 'kwplayer')

    def refresh(self):
        if not self.player.app.conf['use-notify']:
            return

        notify = self.notify
        song = self.player.curr_song

        notify.clear_hints()
        #notify.set_timeout(4000)

        if len(song['artist']) > 0:
            artist = Widgets.short_tooltip(song['artist'], 20)
        else:
            artist = _('Unknown')
        if len(song['album']) > 0:
            album = Widgets.short_tooltip(song['album'], 30)
        else:
            album = _('Unknown')
        notify.update(
                song['name'],
                'by <i>{0}</i> from <i>{1}</i>'.format(artist, album),
                self.player.meta_artUrl
                )
        notify.set_hint('image-path', GLib.Variant.new_string(
            self.player.meta_artUrl))
        #notify.set_hint('icon-name', GLib.Variant.new_string(
        #    self.player.meta_artUrl))
        #notify.set_image_from_pixbuf(
        #        self.player.artist_pic.get_pixbuf())

        notify.clear_actions()

        try:
            notify.add_action(
                    'media-skip-backward',
                    _('Previous'),
                    self.on_prev_action_activated,
                    None)
            if self.player.is_playing():
                notify.add_action(
                        'media-playback-pause',
                        _('Pause'),
                        self.on_playpause_action_activated,
                        None)
            else:
                notify.add_action(
                        'media-playback-start',
                        _('Play'),
                        self.on_playpause_action_activated,
                        None)
            notify.add_action(
                    'media-skip-forward',
                    _('Next'),
                    self.on_next_action_activated,
                    None)
        except Exception:
            notify.add_action(
                    'media-skip-backward',
                    _('Previous'),
                    self.on_prev_action_activated,
                    None,
                    None)
            if self.player.is_playing():
                notify.add_action(
                        'media-playback-pause',
                        _('Pause'),
                        self.on_playpause_action_activated,
                        None,
                        None)
            else:
                notify.add_action(
                        'media-playback-start',
                        _('Play'),
                        self.on_playpause_action_activated,
                        None,
                        None)
            notify.add_action(
                    'media-skip-forward',
                    _('Next'),
                    self.on_next_action_activated,
                    None,
                    None)

        notify.set_hint('action-icons',
                GLib.Variant.new_boolean(True))

        # gnome shell screenlocker will get `x-gnome.music` notification
        # and the whole notification content will be presented
        # from rhythmbox/plugins/rb-notification-plugin.c
        notify.set_category('x-gnome.music')
        #notify.set_hint('desktop-entry',
        #        GLib.Variant.new_string('kwplayer'))

        # show on lock screen
        hint = 'resident'
        # show on desktop
        #hint = 'transient'
        notify.set_hint(hint, GLib.Variant.new_boolean(True))

        notify.show()

    def on_prev_action_activated(self, *args):
        print('on prev_action activated')
        self.player.load_prev_cb()

    def on_playpause_action_activated(self, *args):
        print('on playpause activated', args)
        self.player.play_pause_cb()

    def on_next_action_activated(self, *args):
        print('on next action activated')
        self.player.load_next_cb()
