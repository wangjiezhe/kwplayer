
import gettext
import json
import locale
import os

from gi.repository import GdkPixbuf

if __file__.startswith('/usr/'):
    PREF = '/usr/share'
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share')

LOCALEDIR = os.path.join(PREF, 'locale')
gettext.bindtextdomain('kuwo', LOCALEDIR)
gettext.textdomain('kuwo')
locale.bindtextdomain('kuwo', LOCALEDIR)
locale.textdomain('kuwo')
_ = gettext.gettext

APPNAME = _('KW Player')
VERSION = '2.3'
HOMEPAGE = 'https://github.com/LiuLang/kwplayer'
AUTHORS = ['LiuLang <gsushzhsosgsu@gmail.com>',]

_UI_FILES = ('menus.ui', )
UI_FILES = [os.path.join(PREF, 'kuwo', 'ui', ui) for ui in _UI_FILES]

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
THEME_MAIN_STYLE = os.path.join(THEME_DIR, 'main.css')
THEME_MAIN_STYLE_3_6 = os.path.join(THEME_DIR, 'main-3.6.css')

CONF_DIR = os.path.join(HOME_DIR, '.config', 'kuwo')
_conf_file = os.path.join(CONF_DIR, 'conf.json')
_default_conf = {
        'window-size': (840, 580),
        'song-dir': os.path.join(CACHE_DIR, 'song'),
        'mv-dir': os.path.join(CACHE_DIR, 'mv'),
        'volume': 0.08,
        'use-ape': False,
        'use-mkv': False,
        'lrc-img-back-color': 'rgba(0, 0, 0, 1)',
        'lrc-word-back-color': 'rgba(237, 221, 221, 0.28)',
        }

def check_first():
    if not os.path.exists(_conf_file):
        try:
            os.makedirs(os.path.dirname(_conf_file))
            os.makedirs(IMG_DIR)
            os.mkdir(IMG_LARGE_DIR)
            os.mkdir(_default_conf['song-dir'])
            os.mkdir(_default_conf['mv-dir'])
        except Exception as e:
            print('Error', e)

def load_conf():
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            return json.loads(fh.read())
    dump_conf(_default_conf)
    return _default_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        fh.write(json.dumps(conf))

def load_theme():
    theme_file = os.path.join(THEME_DIR, 'images.json')
    try:
        with open(theme_file) as fh:
            theme = json.loads(fh.read())
    except Exception as e:
        print(e)
        return None

    theme_pix = {}
    for key in theme:
        filename = os.path.join(THEME_DIR, theme[key])
        if os.path.exists(filename):
            theme_pix[key] = GdkPixbuf.Pixbuf.new_from_file(filename)
        else:
            print('Failed to open theme icon', filename)
            return None
    return theme_pix
