
# Copyright (C) 2013 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import gettext
from gi.repository import GdkPixbuf
import json
import locale
import os

if __file__.startswith('/usr/local/'):
    PREF = '/usr/local/share'
elif __file__.startswith('/usr/'):
    PREF = '/usr/share'
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share')

LOCALEDIR = os.path.join(PREF, 'locale')
gettext.bindtextdomain('kwplayer', LOCALEDIR)
gettext.textdomain('kwplayer')
locale.bindtextdomain('kwplayer', LOCALEDIR)
locale.textdomain('kwplayer')
_ = gettext.gettext

APPNAME = _('KW Player')
VERSION = '3.2.2'
HOMEPAGE = 'https://github.com/LiuLang/kwplayer'
AUTHORS = ['LiuLang <gsushzhsosgsu@gmail.com>',]
DESCRIPTION = _('A simple music player on Linux desktop.')

HOME_DIR = os.path.expanduser('~')
CACHE_DIR = os.path.join(HOME_DIR, '.cache', 'kuwo')
# used for small logos(100x100)
IMG_DIR = os.path.join(CACHE_DIR, 'images')
# used by today_recommand images
IMG_LARGE_DIR = os.path.join(CACHE_DIR, 'images_large')
# lyrics are putted here
LRC_DIR = os.path.join(CACHE_DIR, 'lrc')
# song index
SONG_DB = os.path.join(CACHE_DIR, 'music.sqlite')
# url requests are stored here.
CACHE_DB = os.path.join(CACHE_DIR, 'cache.db')
# store playlists, `cached` not included.
PLS_JSON = os.path.join(CACHE_DIR, 'pls.json')
# store radio playlist.
RADIO_JSON = os.path.join(CACHE_DIR, 'radio.json')

THEME_DIR = os.path.join(PREF, 'kuwo', 'themes', 'default')

class ShortcutMode:
    NONE = 0
    DEFAULT = 1
    CUSTOM = 2

CONF_DIR = os.path.join(HOME_DIR, '.config', 'kuwo')
_conf_file = os.path.join(CONF_DIR, 'conf.json')
SHORT_CUT_I18N = {
        'VolumeUp': _('VolumeUp'),
        'VolumeDown': _('VolumeDown'),
        'Mute': _('Mute'),
        'Previous': _('Previous'),
        'Next': _('Next'),
        'Pause': _('Pause'),
        'Play': _('Play'),
        'Stop': _('Stop'),
        'Launch': _('Launch'),
        }
_default_conf = {
        'window-size': (960, 680),
        'song-dir': os.path.join(CACHE_DIR, 'song'),
        'mv-dir': os.path.join(CACHE_DIR, 'mv'),
        'volume': 0.08,
        'use-ape': False,
        'use-mkv': False,
        'use-status-icon': True,
        'use-notify': False,
        'lrc-text-color': 'rgba(46, 52, 54, 0.999)',
        'lrc-back-color': 'rgba(237, 221, 221, 0.28)',
        'lrc-text-size': 22,
        'lrc-highlighted-text-color': 'rgba(52, 101, 164, 0.999)',
        'lrc-highlighted-text-size': 26,
        'shortcut-mode': ShortcutMode.DEFAULT,
        'custom-shortcut': {
            'VolumeUp': '<Ctrl><Shift>U',
            'VolumeDown': '<Ctrl><Shift>D',
            'Mute': '<Ctrl><Shift>M',
            'Previous': '<Ctrl><Shift>Left',
            'Next': '<Ctrl><Shift>Right',
            'Pause': '<Ctrl><Shift>Down',
            'Play': '<Ctrl><Shift>Down',
            'Stop': '<Ctrl><Shift>Up',
            'Launch': '<Ctrl><Shift>L',
            },
        'default-shortcut': {
            'VolumeUp': 'XF86AudioRaiseVolume',
            'VolumeDown': 'XF86AudioLowerVolume',
            'Mute': 'XF86AudioMute',
            'Previous': 'XF86AudioPrev',
            'Next': 'XF86AudioNext',
            'Pause': 'XF86AudioPause',
            'Play': 'XF86AudioPlay',
            'Stop': 'XF86AudioStop',
            'Launch': 'XF86AudioMedia',
            },
        }

def check_first():
    if not os.path.exists(CONF_DIR):
        try:
            os.makedirs(CONF_DIR)
        except Exception as e:
            print(e)
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
            os.mkdir(IMG_DIR)
            os.mkdir(IMG_LARGE_DIR)
            os.mkdir(_default_conf['song-dir'])
            os.mkdir(_default_conf['mv-dir'])
        except Exception as e:
            print(e)
    if not os.path.exists(LRC_DIR):
        try:
            os.mkdir(LRC_DIR)
        except Exception as e:
            print(e)

def load_conf():
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            conf = json.loads(fh.read())
        for key in _default_conf:
            if key not in conf:
                conf[key] = _default_conf[key]
        # 3.1.5 -> 3.1.6
        if 'Launch' not in conf['custom-shortcut']:
            conf['custom-shortcut']['Launch'] = _default_conf['custom-shortcut']['Launch']
        if 'Launch' not in conf['default-shortcut']:
            conf['default-shortcut']['Launch'] = _default_conf['default-shortcut']['Launch']
        return conf
    dump_conf(_default_conf)
    return _default_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        fh.write(json.dumps(conf, indent=2))

def load_theme():
    theme_file = os.path.join(THEME_DIR, 'images.json')
    try:
        with open(theme_file) as fh:
            theme = json.loads(fh.read())
    except Exception as e:
        print(e)
        return None

    theme_pix = {}
    theme_path = {}
    for key in theme:
        filename = os.path.join(THEME_DIR, theme[key])
        if os.path.exists(filename):
            theme_pix[key] = GdkPixbuf.Pixbuf.new_from_file(filename)
            theme_path[key] = filename
        else:
            print('Failed to open theme icon', filename)
            return None
    return (theme_pix, theme_path)
