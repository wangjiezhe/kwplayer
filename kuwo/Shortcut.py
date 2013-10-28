
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GLib

try:
    from keybinder.keybinder_gtk import KeybinderGtk
    keybinder_imported = True
except ImportError as e:
    keybinder_imported = False
    print('Warning: no python3-keybinder module found, global keyboard shortcut will be disabled!')


from kuwo import Config
ShortcutMode = Config.ShortcutMode

class Shortcut:
    def __init__(self, player):
        self.player = player

        self.callbacks = {
                'VolumeUp': self.volume_up,
                'VolumeDown': self.volume_down,
                'Mute':
                    lambda *args: player.toggle_mute_cb(),
                'Previous': lambda *args: player.load_prev_cb(),
                'Next': lambda *args: player.load_next_cb(),
                'Pause': lambda *args: player.play_pause_cb(),
                'Play': lambda *args: player.play_pause_cb(),
                'Stop': lambda *args: player.stop_player_cb(),
                'Launch': self.present_window,
                }

        if keybinder_imported:
            self.keybinder = KeybinderGtk()
            self.bind_keys()
            self.keybinder.start()
            
    def volume_up(self, *args):
        volume = self.player.volume.get_value() + 0.15
        if volume > 1:
            volume = 1
        self.player.set_volume_cb(volume)

    def volume_down(self, *args):
        volume = self.player.volume.get_value() - 0.15
        if volume < 0:
            volume = 0
        self.player.set_volume_cb(volume)

    def present_window(self, *args):
        GLib.idle_add(self.player.app.window.present)

    def bind_keys(self):
        if not keybinder_imported:
            return
        curr_mode = self.player.app.conf['shortcut-mode']
        if curr_mode == ShortcutMode.NONE:
            return
        if curr_mode == ShortcutMode.DEFAULT:
            shortcut_keys = self.player.app.conf['default-shortcut']
        elif curr_mode == ShortcutMode.CUSTOM:
            shortcut_keys = self.player.app.conf['custom-shortcut']
        for name, key in shortcut_keys.items():
            self.keybinder.register(key, self.callbacks[name])

    def rebind_keys(self):
        self.bind_keys()

    def quit(self):
        print('Shortcut.quit')
        if keybinder_imported:
            self.keybinder.stop()
