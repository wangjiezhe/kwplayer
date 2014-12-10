# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import gettext
import json
import os
import shutil
import sys
import traceback

from gi.repository import GdkPixbuf
from gi.repository import Gtk

import kuwo
from kuwo.log import logger

if __file__.startswith('/usr/local/'):
    PREF = '/usr/local/share'
elif __file__.startswith('/usr/'):
    PREF = '/usr/share'
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share')

NAME = 'kwplayer'
LOCALEDIR = os.path.join(PREF, 'locale')
gettext.bindtextdomain(NAME, LOCALEDIR)
gettext.textdomain(NAME)
_ = gettext.gettext

# Check Gtk version <= 3.6
GTK_LE_36 = (Gtk.MAJOR_VERSION == 3) and (Gtk.MINOR_VERSION <= 6)
GTK_GE_312 = Gtk.MINOR_VERSION >= 12

APPNAME = _('KW Player')
VERSION = kuwo.__version__
HOMEPAGE = 'https://github.com/LiuLang/kwplayer'
AUTHORS = ['LiuLang <gsushzhsosgsu@gmail.com>', ]
COPYRIGHT = 'Copyright (c) 2013-2014 LiuLang'
DESCRIPTION = _('Music player for linux users')

ICON_PATH = os.path.join(PREF, NAME, 'icons')
LRC_BACKGROUND_IMG = os.path.join(ICON_PATH, 'lrc-background.jpg')
ANONYMOUS_IMG = os.path.join(ICON_PATH, 'anonymous.png')
ANONYMOUS_PIXBUF = GdkPixbuf.Pixbuf.new_from_file(ANONYMOUS_IMG)

HOME_DIR = os.path.expanduser('~')
CACHE_DIR = os.path.join(HOME_DIR, '.cache', 'kuwo')
# used for small logos(100x100)
IMG_DIR = os.path.join(CACHE_DIR, 'images')
# used by today_recommand images
IMG_LARGE_DIR = os.path.join(CACHE_DIR, 'images_large')
# lyrics are putted here
LRC_DIR = os.path.join(CACHE_DIR, 'lrc')
# url requests are stored here.
CACHE_DB = os.path.join(CACHE_DIR, 'cache.db')
# store playlists, `cached` not included.
PLS_JSON = os.path.join(CACHE_DIR, 'pls.json')
# store radio playlist.
RADIO_JSON = os.path.join(CACHE_DIR, 'radio.json')
# favorite artists list.
FAV_ARTISTS_JSON = os.path.join(CACHE_DIR, 'fav_artists.json')


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
    'version': VERSION,
    'window-size': (960, 680),
    'song-dir': os.path.join(CACHE_DIR, 'song'),
    'mv-dir': os.path.join(CACHE_DIR, 'mv'),
    'volume': 0.08,
    'audio': 2,  # 320k mp3
    'video': 1,  # mp4 high
    'use-status-icon': True,
    'use-notify': False,
    'use-dark-theme': False,
    'lrc-text-color': 'rgba(46, 52, 54, 0.999)',
    'lrc-back-color': 'rgba(237, 221, 221, 0.28)',
    'lrc-text-size': 22,
    'lrc-highlighted-text-color': 'rgba(0, 0, 0, 0.999)',
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

    'osd-x': 200,
    'osd-y': 200,
    'osd-show': False,
    'osd-three': False,  # 三行显示
    'osd-locked': False,
    'osd-style': 'default',
    'osd-background-color': 'rgba(123, 123, 123, 0)',
    'osd-inactivated-color': 'rgba(196, 160, 0, 0.999)',
    'osd-inactivated-size': 30,
    'osd-inactivated-shadow-x': 1,
    'osd-inactivated-shadow-y': 1,
    'osd-inactivated-shadow-radius': 6,
    'osd-inactivated-shadow-color': 'rgba(174, 167, 107, 0.565)',
    'osd-activated-color': 'rgba(42, 119, 231, 0.999)',
    'osd-activated-size': 40,
    'osd-activated-shadow-x': 1,
    'osd-activated-shadow-y': 1,
    'osd-activated-shadow-radius': 7,
    'osd-activated-shadow-color': 'rgba(52, 101, 164, 0.99)',
}

def check_first():
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR)
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        os.mkdir(IMG_DIR)
        os.mkdir(IMG_LARGE_DIR)
        os.mkdir(_default_conf['song-dir'])
        os.mkdir(_default_conf['mv-dir'])
        os.mkdir(LRC_DIR)

def load_conf():
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            conf = json.loads(fh.read())
        for key in _default_conf:
            if key not in conf:
                conf[key] = _default_conf[key]
        return conf
    dump_conf(_default_conf)
    return _default_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        fh.write(json.dumps(conf, indent=2))
