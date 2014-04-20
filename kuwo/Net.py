
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import hashlib
import json
import math
import os
import sys
import threading
import time
from urllib.error import URLError
from urllib import parse
from urllib import request

from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from kuwo import Config
from kuwo import Utils

IMG_CDN = 'http://img4.kwcdn.kuwo.cn/'
ARTIST = 'http://artistlistinfo.kuwo.cn/mb.slist?'
QUKU = 'http://qukudata.kuwo.cn/q.k?'
QUKU_SONG = 'http://nplserver.kuwo.cn/pl.svc?'
SEARCH = 'http://search.kuwo.cn/r.s?'
SONG = 'http://antiserver.kuwo.cn/anti.s?'

CHUNK = 16384                # 2**14, 16k, chunk size for file downloading 
CHUNK_TO_PLAY = 2097152      # 2**21, 2M, min size to emit can-play signal
CHUNK_APE_TO_PLAY = 8388608  # 2**23, 8M
CHUNK_MV_TO_PLAY = 8388608   # 2**23, 8M
MAXTIMES = 3                 # time to retry http connections
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
except ImportError as e:
    try:
        # Fedora: https://github.com/wbolster/plyvel
        from plyvel import DB as LevelDB
        ldb_imported = True
    except ImportError as e:
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
    except Exception as e:
        ldb_imported = False

def empty_func(*args, **kwds):
    pass

# calls f on another thread
def async_call(func, func_done, *args):
    def do_call(*args):
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e
        GLib.idle_add(lambda: func_done(result, error))

    thread = threading.Thread(target=do_call, args=args)
    thread.daemon = True
    thread.start()

def hash_byte(_str):
    return hashlib.sha512(_str.encode()).digest()

def hash_str(_str):
    return hashlib.sha1(_str.encode()).hexdigest()

def urlopen(_url, use_cache=True, retries=MAXTIMES):
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
                    pass
        except KeyError:
            pass
    for i in range(retries):
        try:
            req = request.urlopen(url, timeout=TIMEOUT)
            req_content = req.read()
            if use_cache and ldb_imported:
                ldb_put(key, str(int(time.time())).encode() + req_content)
            return req_content
        except URLError as e:
            pass
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
    except ValueError as e:
        return (None, 0)
    nodes = nodes_wrap['child']
    pages = math.ceil(int(nodes_wrap['total']) / ICON_NUM)
    return (nodes, pages)

def get_image(url, filepath=None):
    if not url or len(url) < 10:
        return None
    if not filepath:
        filename = os.path.split(url)[1]
        filepath = os.path.join(Config.IMG_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    image = urlopen(url, use_cache=False)
    if not image:
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
    url = ''.join([
        SEARCH,
        'stype=albuminfo&albumid=',
        str(albumid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return None
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return None
    songs = songs_wrap['musiclist']
    return songs

def update_liststore_images(liststore,  col, tree_iters, urls,
                            url_proxy=None, resize=IMG_SIZE):
    '''Update a banch of thumbnails consequently.

    liststore - the tree model, which has timestmap property
    col       - column index
    tree_iters - a list of tree_iters
    urls      - a list of image urls
    url_proxy - a function to reconstruct image url, this function run in 
                background thread. default is None, do nothing.
    resize    - will resize pixbuf to specific size, default is 100x100
    '''
    def update_image(filepath, tree_iter):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    filepath, resize, resize)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is not None:
                liststore[tree_path][col] = pix
        except GLib.GError:
            pass

    def get_images():
        for tree_iter, url in zip(tree_iters, urls):
            # First, check timestamp matches
            if liststore.timestamp != timestamp:
                break
            if url_proxy:
                url = url_proxy(url)
            filepath = get_image(url)
            if filepath:
                GLib.idle_add(update_image, filepath, tree_iter)

    timestamp = liststore.timestamp
    thread = threading.Thread(target=get_images, args=[])
    thread.daemon = True
    thread.start()

def update_album_covers(liststore, col, tree_iters, urls):
    def url_proxy(url):
        url = url.strip()
        if not url:
            return ''
        return ''.join([
            IMG_CDN,
            'star/albumcover/',
            url,
            ])
    update_liststore_images(liststore, col, tree_iters, urls, url_proxy)

def update_mv_images(liststore, col, tree_iters, urls):
    def url_proxy(url):
        url = url.strip()
        if not url:
            return ''
        return ''.join([
            IMG_CDN,
            'wmvpic/',
            url,
            ])
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
    except ValueError as e:
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
    try:
        artists_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    pages = int(artists_wrap['total'])
    artists = artists_wrap['artistlist']
    return (artists, pages)

def get_artist_pic_url(pic_path):
    if len(pic_path) < 5:
        return None
    if pic_path[:2] in ('55', '90',):
        pic_path = '100/' + pic_path[2:]
    url = ''.join([IMG_CDN, 'star/starheads/', pic_path, ])
    return url

def update_artist_logos(liststore, col, tree_iters, urls):
    update_liststore_images(
            liststore, col, tree_iters, urls,
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
    try:
        info = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
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
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
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
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
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
    try:
        albums_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
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
    try:
        mvs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
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
    try:
       artists_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
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
        except Exception as e:
            return None

    rid = str(song['rid'])
    (lrc_path, lrc_cached) = get_lrc_path(song)
    if lrc_cached:
        with open(lrc_path) as fh:
            return fh.read()

    lrc = _parse_lrc()
    if lrc:
        try:
            with open(lrc_path, 'w') as fh:
                fh.write(lrc)
        except FileNotFoundError as e:
            pass
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
    try:
        songs_wrap = Utils.json_loads_single(req_cache[url].decode())
    except ValueError as e:
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
    try:
        artists_wrap = Utils.json_loads_single(req_cache[url].decode())
    except ValueError as e:
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
    try:
        albums_wrap = Utils.json_loads_single(req_cache[url].decode())
    except ValueError  as e:
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
    except ValueError as e:
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
    except ValueError as e:
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
    except ValueError as e:
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

    @conf, is used to to read conf['use-ape'], conf['use-mkv'],
    conf['song-dir'] and song['mv-dir'].
    use_mv, default is False, which will get mp3 link.
    Return:
     @cached : if is True, local song exists
               if is False, no available song_link
     @song_link: music source link; if local song exists or failed to get
              music source link, returns ''
     @song_path: target abs-path this song will be cached.
    '''
    if use_mv:
        ext = 'mkv|mp4' if conf['use-mkv'] else 'mp4'
    else:
        ext = 'ape|mp3' if conf['use-ape'] else 'mp3'
    url = ''.join([
        SONG,
        'response=url&type=convert_url&format=',
        ext,
        '&rid=MUSIC_',
        str(song['rid']),
        ])
    song_name = (''.join([
        song['artist'],
        '-',
        song['name'],
        '.',
        ext,
        ])).replace('/', '+')
    if use_mv:
        song_path = os.path.join(conf['mv-dir'], song_name)
    else:
        song_path = os.path.join(conf['song-dir'], song_name)
    if os.path.exists(song_path):
        return (True, '', song_path)
    req_content = urlopen(url)
    if not req_content:
        return (False, '', song_path)
    song_link = req_content.decode()
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
            'can-play': (GObject.SIGNAL_RUN_LAST, 
                # sogn_path
                GObject.TYPE_NONE, (str, )),
            'chunk-received': (GObject.SIGNAL_RUN_LAST,
                # percent
                GObject.TYPE_NONE, (GObject.TYPE_DOUBLE, )),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                # song_path
                GObject.TYPE_NONE, (str, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, (str, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, (str, )),
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
        like this:
        response=url&type=convert_url&format=ape|mp3&rid=MUSIC_3312608
        '''
        async_call(self._download_song, empty_func, song, use_mv)

    def _download_song(self, song, use_mv):
        cached, song_link, song_path = get_song_link(
                song, self.app.conf, use_mv=use_mv)

        # check song already cached 
        if cached:
            self.emit('can-play', song_path)
            self.emit('downloaded', song_path)
            return

        # this song has no link to download
        if not song_link:
            self.emit('network-error', song_link)
            return

        chunk_to_play = CHUNK_TO_PLAY
        if self.app.conf['use-ape']:
            chunk_to_play = CHUNK_APE_TO_PLAY
        if use_mv:
            chunk_to_play = CHUNK_MV_TO_PLAY

        for retried in range(MAXTIMES):
            try:
                req = request.urlopen(song_link)
                received_size = 0
                can_play_emited = False
                content_length = int(req.headers.get('Content-Length'))
                fh = open(song_path, 'wb')

                while True:
                    if self.force_quit:
                        del req
                        fh.close()
                        os.remove(song_path)
                        return
                    chunk = req.read(CHUNK)
                    received_size += len(chunk)
                    percent = received_size / content_length
                    self.emit('chunk-received', percent)
                    # this signal only emit once.
                    if ((received_size > chunk_to_play or percent > 40) and
                            not can_play_emited):
                        can_play_emited = True
                        self.emit('can-play', song_path)
                    if not chunk:
                        break
                    fh.write(chunk)
                fh.close()
                self.emit('downloaded', song_path)
                Utils.iconvtag(song_path, song)
                return

            except URLError as e:
                pass
            except FileNotFoundError as e:
                self.emit('disk-error', song_path)
                return
        if os.path.exists(song_path):
            os.remove(song_path)
        self.emit('network-error', song_link)

GObject.type_register(AsyncSong)
