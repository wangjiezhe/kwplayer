
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import traceback
from urllib.error import URLError
from urllib import parse
from urllib import request

from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from kuwo import Config
from kuwo import DES
from kuwo import Utils
from kuwo.log import logger

IMG_CDN = 'http://img4.kwcdn.kuwo.cn/'
ARTIST_IMG_CDN = 'http://img1.kuwo.cn/'
ARTIST = 'http://artistlistinfo.kuwo.cn/mb.slist?'
QUKU = 'http://qukudata.kuwo.cn/q.k?'
QUKU_SONG = 'http://nplserver.kuwo.cn/pl.svc?'
SEARCH = 'http://search.kuwo.cn/r.s?'
SONG = 'http://antiserver.kuwo.cn/anti.s?'

CHUNK = 16384                # 2**14, 16k, chunk size for file downloading 
CHUNK_TO_PLAY = 2097152      # 2**21, 2M, min size to emit can-play signal
CHUNK_MV_TO_PLAY = 8388608   # 2**23, 8M
RETRIES = 3                 # time to retry http connections
TIMEOUT = 30                 # HTTP connection timeout
SONG_NUM = 100               # num of songs in each request
ICON_NUM = 50                # num of icons in each request
CACHE_TIMEOUT = 1209600      # 14 days in seconds

IMG_SIZE = 100               # image size, 100px

# Using weak reference to cache song list in TopList and Radio.
class Dict(dict):
    pass
req_cache = Dict()

try:
    # Debian: http://code.google.com/p/py-leveldb/
    from leveldb import LevelDB
    ldb_imported = True
except ImportError:
    logger.debug(traceback.format_exc())
    try:
        # Fedora: https://github.com/wbolster/plyvel
        from plyvel import DB as LevelDB
        ldb_imported = True
    except ImportError:
        logger.debug(traceback.format_exc())
        ldb_imported = False

ldb = None
if ldb_imported:
    try:
        ldb = LevelDB(Config.CACHE_DB, create_if_missing=True)
        # support plyvel 0.6
        if hasattr(ldb, 'put'):
            ldb_get = ldb.get
            ldb_put = ldb.put
        else:
            ldb_get = ldb.Get
            ldb_put = ldb.Put
    except Exception:
        logger.debug(traceback.format_exc())
        ldb_imported = False

def async_call(func, *args, callback=None):
    '''Call `func` in background thread, and then call `callback` in Gtk main thread.

    If error occurs in `func`, error will keep the traceback and passed to
    `callback` as second parameter. Always check `error` is not None.
    '''
    def do_call():
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e
        if callback:
            GLib.idle_add(callback, result, error)

    thread = threading.Thread(target=do_call)
    thread.daemon = True
    thread.start()

def hash_byte(_str):
    return hashlib.sha512(_str.encode()).digest()

def hash_str(_str):
    return hashlib.sha1(_str.encode()).hexdigest()

def urlopen(_url, use_cache=True, retries=RETRIES):
    # set host port from 81 to 80, to fix image problem
    url = _url.replace(':81', '')
    if use_cache and ldb_imported:
        key = hash_byte(url)
        try:
            content = ldb_get(key)
            if content and len(content) > 10:
                try:
                    timestamp = int(content[:10].decode())
                    if (time.time() - timestamp) < CACHE_TIMEOUT:
                        return content[10:]
                except (ValueError, UnicodeDecodeError):
                    logger.debug(traceback.format_exc())
        except KeyError:
            logger.debug(traceback.format_exc())
    for i in range(retries):
        try:
            req = request.urlopen(url, timeout=TIMEOUT)
            req_content = req.read()
            if use_cache and ldb_imported:
                ldb_put(key, str(int(time.time())).encode() + req_content)
            return req_content
        except URLError:
            logger.warn(traceback.format_exc())
            logger.warn('Net.urlopen, url: %s' % url)
    return None

def get_nodes(nid, page):
    # node list contains very few items
    url = ''.join([
        QUKU,
        'op=query&fmt=json&src=mbox&cont=ninfo&rn=',
        str(ICON_NUM),
        '&pn=',
        str(page),
        '&node=',
        str(nid),
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        nodes_wrap = json.loads(req_content.decode())
    except ValueError:
        logger.error(traceback.format_exc())
        return (None, 0)
    nodes = nodes_wrap['child']
    pages = math.ceil(int(nodes_wrap['total']) / ICON_NUM)
    return (nodes, pages)

def get_image(url, filepath=None):
    if not url or len(url) < 10:
        logger.error('Net.get_image: url is invalid, %s' % url)
        return None
    if not filepath:
        filename = os.path.split(url)[1]
        filepath = os.path.join(Config.IMG_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    image = urlopen(url, use_cache=False)
    if not image:
        logger.debug('Net.get_image: failed to get image, %s' % image)
        return None

    with open(filepath, 'wb') as fh:
        fh.write(image)
    # Now, check its mime type
    file_ = Gio.File.new_for_path(filepath)
    file_info = file_.query_info(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
                                 Gio.FileQueryInfoFlags.NONE)
    content_type = file_info.get_content_type()
    if 'image' in content_type:
        return filepath
    else:
        os.remove(filepath)
        return None

def get_album(albumid):
    url = '{0}stype=albuminfo&albumid={1}'.format(SEARCH, albumid)
    req_content = urlopen(url)
    if not req_content:
        return None
    songs_wrap = Utils.json_loads_single(req_content.decode())
    if not songs_wrap:
        return None
    songs = songs_wrap['musiclist']
    return songs

def update_liststore_images(liststore,  col, tree_iters, urls,
                            url_proxy=None, resize=IMG_SIZE):
    '''Update a banch of thumbnails consequently.

    liststore - the tree model, which has timestamp property
    col       - column index
    tree_iters - a list of tree_iters
    urls      - a list of image urls
    url_proxy - a function to reconstruct image url, this function run in 
                background thread. default is None, do nothing.
    resize    - will resize pixbuf to specific size, default is 100x100
    '''
    def update_image(filepath, tree_iter):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath, resize,
                                                         resize)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is not None:
                liststore[tree_path][col] = pix
        except Exception:
            logger.error(traceback.format_exc())

    timestamp = liststore.timestamp
    for tree_iter, url in zip(tree_iters, urls):
        # First, check timestamp matches
        if liststore.timestamp != timestamp:
            break
        if url_proxy:
            url = url_proxy(url)
        try:
            filepath = get_image(url)
        except Exception:
            logger.error(traceback.format_exc())
            continue
        if filepath:
            GLib.idle_add(update_image, filepath, tree_iter)


def update_album_covers(liststore, col, tree_iters, urls):
    def url_proxy(url):
        url = url.strip()
        if not url:
            return ''
        return '{0}star/albumcover/{1}'.format(IMG_CDN, url)
    update_liststore_images(liststore, col, tree_iters, urls, url_proxy)

def update_mv_images(liststore, col, tree_iters, urls):
    def url_proxy(url):
        url = url.strip()
        if not url:
            return ''
        return '{0}wmvpic/{1}'.format(IMG_CDN, url)
    update_liststore_images(liststore, col, tree_iters, urls,
                            url_proxy=url_proxy, resize=120)

def get_toplist_songs(nid):
    # no need to use pn, because toplist contains very few songs
    url = ''.join([
        'http://kbangserver.kuwo.cn/ksong.s?',
        'from=pc&fmt=json&type=bang&data=content&rn=',
        str(SONG_NUM),
        '&id=',
        str(nid),
    ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return None
        req_cache[url] = req_content
    try:
        songs_wrap = json.loads(req_cache[url].decode())
    except ValueError:
        logger.error(traceback.format_exc())
        return None
    return songs_wrap['musiclist']

def get_artists(catid, page, prefix):
    url = ''.join([
        ARTIST,
        'stype=artistlist&order=hot&rn=',
        str(ICON_NUM),
        '&category=',
        str(catid),
        '&pn=',
        str(page),
    ])
    if len(prefix) > 0:
        url = url + '&prefix=' + prefix
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    artists_wrap = Utils.json_loads_single(req_content.decode())
    if not artists_wrap:
        return (None, 0)
    pages = int(artists_wrap['total'])
    artists = artists_wrap['artistlist']
    return (artists, pages)

def get_artist_pic_url(pic_path):
    if len(pic_path) < 5:
        return None
    if pic_path[:2] in ('55', '90',):
        pic_path = '/100' + pic_path[2:]
    url = '{0}star/starheads{1}'.format(ARTIST_IMG_CDN, pic_path)
    return url

def update_artist_logos(liststore, col, tree_iters, urls):
    update_liststore_images(liststore, col, tree_iters, urls,
                            url_proxy=get_artist_pic_url)

def get_artist_info(artistid, artist=None):
    '''Get artist info, if cached, just return it.

    Artist pic is also retrieved and saved to info['pic']
    '''
    if artistid == 0:
        url = ''.join([
            SEARCH,
            'stype=artistinfo&artist=', 
            Utils.encode_uri(artist),
        ])
    else:
        url = ''.join([
            SEARCH,
            'stype=artistinfo&artistid=', 
            str(artistid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return None
    info = Utils.json_loads_single(req_content.decode())
    if not info:
        return None
    # set logo size to 100x100
    pic_path = info['pic']
    url = get_artist_pic_url(pic_path)
    if url:
        info['pic'] = get_image(url)
    else:
        info['pic'] = None
    return info

def get_artist_songs(artist, page):
    url = ''.join([
        SEARCH,
        'ft=music&itemset=newkw&newsearch=1&cluster=0&rn=',
        str(SONG_NUM),
        '&pn=',
        str(page),
        '&primitive=0&rformat=json&encoding=UTF8&artist=',
        artist,
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    songs_wrap = Utils.json_loads_single(req_content.decode())
    if not songs_wrap:
        return (None, 0)
    songs = songs_wrap['abslist']
    pages = math.ceil(int(songs_wrap['TOTAL']) / SONG_NUM)
    return (songs, pages)

def get_artist_songs_by_id(artistid, page):
    url = ''.join([
        SEARCH,
        'stype=artist2music&artistid=',
        str(artistid),
        '&rn=',
        str(SONG_NUM),
        '&pn=',
        str(page),
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    songs_wrap = Utils.json_loads_single(req_content.decode())
    if not songs_wrap:
        return (None, 0)
    songs = songs_wrap['musiclist']
    pages = math.ceil(int(songs_wrap['total']) / SONG_NUM)
    return (songs, pages)

def get_artist_albums(artistid, page):
    url = ''.join([
        SEARCH,
        'stype=albumlist&sortby=1&rn=',
        str(ICON_NUM),
        '&artistid=',
        str(artistid),
        '&pn=',
        str(page),
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    albums_wrap = Utils.json_loads_single(req_content.decode())
    if not albums_wrap:
        return (None, 0)
    albums = albums_wrap['albumlist']
    pages = math.ceil(int(albums_wrap['total']) / ICON_NUM)
    return (albums, pages)

def get_artist_mv(artistid, page):
    url = ''.join([
        SEARCH,
        'stype=mvlist&sortby=0&rn=',
        str(ICON_NUM),
        '&artistid=',
        str(artistid),
        '&pn=',
        str(page),
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    mvs_wrap = Utils.json_loads_single(req_content.decode())
    if not mvs_wrap:
        return (None, 0)
    mvs = mvs_wrap['mvlist']
    pages = math.ceil(int(mvs_wrap['total']) / ICON_NUM)
    return (mvs, pages)

def get_artist_similar(artistid, page):
    '''Only has 10 items'''
    url = ''.join([
        SEARCH,
        'stype=similarartist&sortby=0&rn=',
        str(ICON_NUM),
        '&pn=',
        str(page),
        '&artistid=',
        str(artistid),
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    artists_wrap = Utils.json_loads_single(req_content.decode())
    if not artists_wrap:
        return (None, 0)
    artists = artists_wrap['artistlist']
    pages = math.ceil(int(artists_wrap['total']) / ICON_NUM)
    return (artists, pages)

def get_lrc_path(song):
    rid = str(song['rid'])
    oldname = rid + '.lrc'
    oldpath = os.path.join(Config.LRC_DIR, oldname)
    newname = '{0}-{1}.lrc'.format(song['artist'], song['name'])
    newpath = os.path.join(Config.LRC_DIR, newname)
    if os.path.exists(oldpath):
        os.rename(oldpath, newpath)
    if os.path.exists(newpath):
        return (newpath, True)
    return (newpath, False)

def get_lrc(song):
    def _parse_lrc():
        url = ('http://newlyric.kuwo.cn/newlyric.lrc?' + 
                Utils.encode_lrc_url(rid))
        req_content = urlopen(url, use_cache=False, retries=8)
        if not req_content:
            return None
        try:
            lrc = Utils.decode_lrc_content(req_content)
            return lrc
        except Exception:
            logger.error(traceback.format_exc())
            return None

    rid = str(song['rid'])
    (lrc_path, lrc_cached) = get_lrc_path(song)
    if lrc_cached:
        with open(lrc_path) as fh:
            return fh.read()

    lrc = _parse_lrc()
    if lrc:
        with open(lrc_path, 'w') as fh:
            fh.write(lrc)
    return lrc

def get_recommend_lists(artist):
    url = ''.join([
        'http://artistpicserver.kuwo.cn/pic.web?',
        'type=big_artist_pic&pictype=url&content=list&&id=0&from=pc',
        '&name=',
        Utils.encode_uri(artist),
    ])
    req_content = urlopen(url)
    if not req_content:
        return None
    return req_content.decode()

def get_recommend_image(_url):
    '''Get big cover image about this artist, normally 1024x768'''
    url = _url.strip()
    ext = os.path.splitext(url)[1]
    filename = hash_str(url) + ext
    filepath = os.path.join(Config.IMG_LARGE_DIR, filename)
    return get_image(url, filepath)

def search_songs(keyword, page):
    url = ''.join([
        SEARCH,
        'ft=music&rn=',
        str(SONG_NUM),
        '&newsearch=1&primitive=0&cluster=0',
        '&itemset=newkm&rformat=json&encoding=utf8&all=',
        parse.quote(keyword),
        '&pn=',
        str(page),
    ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0, 0)
        req_cache[url] = req_content
    songs_wrap = Utils.json_loads_single(req_cache[url].decode())
    if not songs_wrap:
        return (None, 0, 0)
    hit = int(songs_wrap['TOTAL'])
    pages = math.ceil(hit / SONG_NUM)
    songs = songs_wrap['abslist']
    return (songs, hit, pages)

def search_artists(keyword, page):
    url = ''.join([
        SEARCH,
        'ft=artist&pn=',
        str(page),
        '&rn=',
        str(ICON_NUM),
        '&newsearch=1&primitive=0&cluster=0',
        '&itemset=newkm&rformat=json&encoding=utf8&all=',
        parse.quote(keyword),
    ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0, 0)
        req_cache[url] = req_content
    artists_wrap = Utils.json_loads_single(req_cache[url].decode())
    if not artists_wrap:
        return (None, 0, 0)
    hit = int(artists_wrap['TOTAL'])
    pages = math.ceil(hit / SONG_NUM)
    artists = artists_wrap['abslist']
    return (artists, hit, pages)

def search_albums(keyword, page):
    url = ''.join([
        SEARCH,
        'ft=album&pn=',
        str(page),
        '&rn=',
        str(ICON_NUM),
        '&newsearch=1&primitive=0&cluster=0',
        '&itemset=newkm&rformat=json&encoding=utf8&all=',
        parse.quote(keyword),
    ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0, 0)
        req_cache[url] = req_content
    albums_wrap = Utils.json_loads_single(req_cache[url].decode())
    if not albums_wrap:
        return (None, 0, 0)
    hit = int(albums_wrap['total'])
    pages = math.ceil(hit / ICON_NUM)
    albums = albums_wrap['albumlist']
    return (albums, hit, pages)

def get_index_nodes(nid):
    '''Get content of nodes from nid=2 to nid=15'''
    url = ''.join([
        QUKU,
        'op=query&fmt=json&src=mbox&cont=ninfo&pn=0&rn=',
        str(ICON_NUM),
        '&node=',
        str(nid),
    ])
    req_content = urlopen(url)
    if not req_content:
        return None
    try:
        nodes_wrap = json.loads(req_content.decode())
    except ValueError:
        logger.error(traceback.format_exc())
        return None
    return nodes_wrap

def get_themes_main():
    def append_to_nodes(nid, use_child=True):
        nodes_wrap = get_index_nodes(nid)
        if not nodes_wrap:
            return None
        if use_child:
            # node is limited to 10, no more are needed.
            for node in nodes_wrap['child'][:10]:
                nodes.append({
                    'name': node['disname'],
                    'nid': int(node['id']),
                    'info': node['info'],
                    'pic': node['pic'],
                })
        else:
            # Because of different image style, we use child picture instaed
            node = nodes_wrap['ninfo']
            pic = nodes_wrap['child'][0]['pic']
            nodes.append({
                'name': node['disname'],
                'nid': int(node['id']),
                'info': node['info'],
                'pic': pic,
            })

    nodes = []
    # Languages 10(+)
    append_to_nodes(10)
    # People 11
    append_to_nodes(11, False)
    # Festivals 12
    append_to_nodes(12, False)
    # Feelings 13(+)
    append_to_nodes(13)
    # Thmes 14
    append_to_nodes(14, False)
    # Tyles 15(+)
    append_to_nodes(15)
    # Time 72325
    append_to_nodes(72325, False)
    # Environment 72326
    append_to_nodes(72326, False)
    if len(nodes) > 0:
        return nodes
    else:
        return None

def get_themes_songs(nid, page):
    url = ''.join([
        QUKU_SONG,
        'op=getlistinfo&encode=utf-8&identity=kuwo&keyset=pl2012&rn=',
        str(SONG_NUM),
        '&pid=',
        str(nid),
        '&pn=',
        str(page),
    ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0)
        req_cache[url] = req_content
    try:
        songs_wrap = json.loads(req_cache[url].decode())
    except ValueError:
        logger.error(traceback.format_exc())
        return (None, 0)
    pages = math.ceil(int(songs_wrap['total']) / SONG_NUM)
    return (songs_wrap['musiclist'], pages)

def get_mv_songs(pid, page):
    url = ''.join([
        QUKU_SONG,
        'op=getlistinfo&pn=',
        str(page),
        '&rn=',
        str(ICON_NUM),
        '&encode=utf-8&keyset=mvpl&pid=',
        str(pid),
    ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        songs_wrap = json.loads(req_content.decode())
    except ValueError:
        logger.error(traceback.format_exc())
        return (None, 0)
    songs = songs_wrap['musiclist']
    pages = math.ceil(int(songs_wrap['total']) / ICON_NUM)
    return (songs, pages)

def get_radios_nodes():
    nid = 8
    return get_nodes(nid)

def get_radio_songs(nid, offset):
    url = ''.join([
        'http://gxh2.kuwo.cn/newradio.nr?',
        'type=4&uid=0&login=0&size=20&fid=',
        str(nid),
        '&offset=',
        str(offset),
    ])
    req_content = urlopen(url)
    if not req_content:
        return None
    songs = Utils.parse_radio_songs(req_content.decode('gbk'))
    return songs

def get_song_link(song, conf, use_mv=False):
    '''song is song_info dict.

    conf['song-dir'] and song['mv-dir'].
    use_mv, default is False, which will get mp3 link.
    Return:
     @cached : if is True, local song exists
               if is False, no available song_link
     @song_link: music source link; if local song exists or failed to get
              music source link, returns ''
     @song_path: target abs-path this song will be cached.
    '''
    audio_brs = ['128kmp3', '192kmp3', '320kmp3', '2000kflac']
    audio_formats = ['MP3128', 'MP3192', 'MP3H', 'AL']
    video_formats = ['MP4L', 'MP4']
    if use_mv:
        if video_formats[1] in song.get('formats', '') and conf['video'] == 1:
            br = video_formats[1]
        else:
            br = video_formats[0]
        ext = 'mp4'
        url = ''.join([
            'user=359307055300426&prod=kwplayer_ar_6.4.8.0',
            '&corp=kuwo&source=kwplayer_ar_6.4.8.0_kw.apk&p2p=1',
            '&type=convert_mv_url2&rid=', str(song['rid']),
            '&quality=', br,
            '&network=WIFI&mode=audition&format=mp4&br=&sig='
        ])
    else:
        ext = 'mp3'
        song_formats = song.get('formats', '')
        if conf['audio'] == 3 and audio_formats[3] in song_formats:
            br = audio_brs[3]
            ext = 'flac'
        elif conf['audio'] >= 2 and audio_formats[2] in song_formats:
            br = audio_brs[2]
        elif conf['audio'] >= 1 and audio_formats[1] in song_formats:
            br = audio_brs[1]
        else:
            br = audio_brs[0]
        url = ''.join([
            'user=359307055300426&prod=kwplayer_ar_6.4.8.0&corp=kuwo',
            '&source=kwplayer_ar_6.4.8.0_kw.apk&p2p=1&type=convert_url2',
            '&br=', br,
            '&format=mp3|flac|aac&sig=0&rid=', str(song['rid']),
            '&network=WIFI'
        ])

    url = 'http://mobi.kuwo.cn/mobi.s?f=kuwo&q=' + DES.base64_encrypt(url)
    song_name = (''.join(
        [song['artist'], '-', song['name'], '.', ext, ])).replace('/', '+')
    if use_mv:
        song_path = os.path.join(conf['mv-dir'], song_name)
    else:
        song_path = os.path.join(conf['song-dir'], song_name)
    if os.path.exists(song_path):
        return (True, '', song_path)
    req_content = urlopen(url)
    if not req_content:
        return (False, '', song_path)
    match = re.search('url=(\S+)\s', req_content.decode())
    if not match:
        return (False, '', song_path)
    song_link = match.group(1)
    if len(song_link) < 20:
        return (False, '', song_path)
    song_list = song_link.split('/')
    song_link = '/'.join(song_list[:3] + song_list[5:])
    # update song path
    song_path = ''.join([os.path.splitext(song_path)[0],
                         os.path.splitext(song_link)[1]])
    if os.path.exists(song_path):
        return (True, '', song_path)
    return (False, song_link, song_path)


class AsyncSong(GObject.GObject):
    '''Download song(including MV).

    Use Gobject to emit signals:
    register three signals: can-play and downloaded
    if `can-play` emited, player will receive a filename which have
    at least 1M to play.
    `chunk-received` signal is used to display the progressbar of 
    downloading process.
    `downloaded` signal may be used to popup a message to notify 
    user that a new song is downloaded.
    '''
    __gsignals__ = {
        'can-play': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
        'chunk-received': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                           (GObject.TYPE_DOUBLE, )),
        'downloaded': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
        'disk-error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
        'network-error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
    }

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.force_quit = False

    def destroy(self):
        self.force_quit = True

    def get_song(self, song, use_mv=False):
        '''Get the actual link of music file.

        If higher quality of that music unavailable, a lower one is used.
        '''
        async_call(self._download_song, song, use_mv)

    def _download_song(self, song, use_mv):
        cached, song_link, song_path = get_song_link(song, self.app.conf,
                                                     use_mv=use_mv)
        # temp file to store data
        tmp_song_path = '{0}-{1}.part'.format(song_path, int(time.time()))

        # check song already cached 
        if cached:
            self.emit('can-play', song_path)
            self.emit('downloaded', song_path)
            return

        # this song has no link to download
        if not song_link:
            logger.debug('download_song(): %s.' % song)
            self.emit('network-error', song_link)
            return

        if use_mv:
            chunk_to_play = CHUNK_MV_TO_PLAY
        else:
            chunk_to_play = CHUNK_TO_PLAY

        for retried in range(RETRIES):
            try:
                req = request.urlopen(song_link, timeout=TIMEOUT)
                received_size = 0
                can_play_emited = False
                content_length = int(req.headers.get('Content-Length'))
                fh = open(tmp_song_path, 'wb')

                while True:
                    if self.force_quit:
                        if not fh.closed:
                            fh.close()
                        if os.path.exists(song_path):
                            os.remove(song_path)
                        return
                    chunk = req.read(CHUNK)
                    received_size += len(chunk)
                    percent = received_size / content_length
                    if int(percent * 100) % 5 == 0:
                        self.emit('chunk-received', percent)
                    # this signal only emit once.
                    if ((received_size > chunk_to_play or percent > 0.4) and
                            not can_play_emited):
                        self.emit('can-play', tmp_song_path)
                        can_play_emited = True
                    if not chunk:
                        break
                    fh.write(chunk)

                fh.close()
                # download successfully
                if received_size == content_length:
                    os.rename(tmp_song_path, song_path)
                    self.emit('downloaded', song_path)
                    Utils.iconvtag(song_path, song)
                    return
                else:
                    self.emit('network-error', song_link)
                # remove temp file
                if os.path.exists(tmp_song_path):
                    os.remove(tmp_song_path)
                break

            except URLError:
                logger.error(traceback.format_exc())
            except FileNotFoundError:
                logger.error(traceback.format_exc())
                self.emit('disk-error', song_path)
                if os.path.exists(tmp_song_path):
                    os.remove(tmp_song_path)
                return

        if os.path.exists(tmp_song_path):
            os.remove(tmp_song_path)
        self.emit('network-error', song_link)

GObject.type_register(AsyncSong)
