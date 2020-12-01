# -*- coding: utf-8 -*-

# for Windows
# old_path = 'file://localhost/'
# new_path    = ''

# for Windows(Bootcamp)
# old_path = 'file://localhost/'
# new_path    = 'E:/'

# for MacOS
# old_path = 'file:///'
# new_path    = '/'

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs

import sys
import os
import re
import base64
import datetime
import unicodedata
import urllib
import urlparse
import inspect

from xml.etree.ElementTree import *

class Const:

    # アドオン
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo('id')
    ADDON_NAME = ADDON.getAddonInfo('name')

    GET = ADDON.getSetting
    SET = ADDON.setSetting
    #STR = ADDON.getLocalizedString
    @staticmethod
    def STR(id): return Const.ADDON.getLocalizedString(id).encode('utf-8')

    # ファイル/ディレクトリパス
    PROFILE_PATH = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    LIBRARY_PATH = os.path.join(PROFILE_PATH, 'iTunes Music Library.xml')
    PLUGIN_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))
    RESOURCES_PATH = os.path.join(PLUGIN_PATH, 'resources')
    DATA_PATH = os.path.join(RESOURCES_PATH, 'data')

    # 変換関数群
    UNMARSHALLERS = {
        # collections
        'array': lambda x: [v.text for v in x],
        'dict': lambda x: dict((x[i].text, x[i+1].text) for i in range(0, len(x), 2)),
        'key': lambda x: x.text or '',
        # simple types
        'string': lambda x: x.text or '',
        'data': lambda x: base64.decodestring(x.text or ''),
        'date': lambda x: datetime.datetime(*map(int, re.findall('\d+', x.text))),
        'true': lambda x: True,
        'false': lambda x: False,
        'real': lambda x: float(x.text),
        'integer': lambda x: int(x.text),
    }

    # ユーティリティ
    @staticmethod
    def log(*messages):
        m = []
        for message in messages:
            if isinstance(message, str):
                m.append(message)
            elif isinstance(message, unicode):
                m.append(message.encode('utf-8'))
            else:
                m.append(str(message))
        frame = inspect.currentframe(1)
        xbmc.log(str('%s: %s(%d): %s: %s') % (Const.ADDON_ID, os.path.basename(frame.f_code.co_filename), frame.f_lineno, frame.f_code.co_name, str(' ').join(m)), xbmc.LOGNOTICE)

    @staticmethod
    def notify(id):
        message = Const.STR(id)
        xbmc.executebuiltin('XBMC.Notification("%s","%s",10000,"DefaultIconError.png")' % (Const.ADDON_NAME, message))

    @staticmethod
    def normalize(text):
        return unicodedata.normalize('NFC', text).encode('utf-8') if isinstance(text, unicode) else text

    @staticmethod
    def cleanup(dir):
        for root, dirs, files in os.walk(dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))


class Music:

    def __init__(self, music):
        self.music = music

    def location(self, old_path, new_path):
        location = self.music.get('Location')
        # write file locations except m4p
        if location and re.search('\.m4p$',location) is None:
            # iTunes put quote to transform space to %20 and so, we have to convert them
            location = Const.normalize(urllib.unquote(location).decode('utf-8'))
            # replace old location by the new location
            if old_path and location.find(old_path) == 0:
                location = location.replace(old_path, new_path)
        else:
            location = None
        return location

    @property
    def title(self):
        title = self.music.get('Name')
        return Const.normalize(title) if title else 'n/a'

    @property
    def artist(self):
        artist = self.music.get('Artist')
        return Const.normalize(artist) if artist else 'n/a'

    @property
    def album(self):
        album = self.music.get('Album')
        return Const.normalize(album) if album else 'n/a'

    @property
    def totalTime(self):
        totalTime = self.music.get('Total Time')
        return totalTime if totalTime else 'n/a'

    @property
    def duration(self):
        duration = self.music.get('Total Time')
        if duration:
            duration /= 1000
            hh = duration/3600
            mm = (duration-hh*3600)/60
            ss = duration%60
            if hh > 0:
                duration = '%d:%02d:%02d' % (hh,mm,ss)
            else:
                duration = '%d:%02d' % (mm,ss)
        else:
            duration = 'n/a'
        return duration

    @property
    def disc(self):
        discNumber = self.music.get('Disc Number')
        discCount = self.music.get('Disc Count')
        if discNumber and discCount:
            disc = '%d/%d' % (discNumber,discCount)
        else:
            disc = 'n/a'
        return disc

    @property
    def track(self):
        trackNumber = self.music.get('Track Number')
        trackCount = self.music.get('Track Count')
        if trackNumber and trackCount:
            track = '%d/%d' % (trackNumber,trackCount)
        else:
            track = 'n/a'
        return track

    @property
    def year(self):
        year = self.music.get('Year')
        if year:
            if year == 9999: year = 'n/a'
        else:
            year = 'n/a'
        return year

    @property
    def dateAdded(self):
        return self.music.get('Date Added', 'n/a')


class Converter:

    def __init__(self):
        # iTunes Music Libraryへのパス
        library_path = Const.GET('library_path')
        # iTunes Music Libraryの有無をチェック
        if not xbmcvfs.exists(library_path):
            Const.notify(30103)
            xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
            xbmc.executebuiltin('SetFocus(100)') # select 1st category
            xbmc.executebuiltin('SetFocus(200)') # select 1st control
            sys.exit()
        # iTunes Music Libraryを所定のフォルダへコピー
        try:
            xbmcvfs.copy(library_path, Const.LIBRARY_PATH)
        except:
            Const.notify(30105)
            xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
            xbmc.executebuiltin('SetFocus(100)') # select 1st category
            xbmc.executebuiltin('SetFocus(200)') # select 1st control
            sys.exit()
        # m3uのパスをチェック
        m3u_path = xbmc.translatePath('special://profile/playlists/music/')
        if os.path.isdir(m3u_path):
            Const.cleanup(m3u_path)
        else:
            os.makedirs(m3u_path)
        self.m3u_path = m3u_path
        # htmlのパスをチェック
        html_path = ''
        if Const.GET('create_html') == 'true':
            html_path = Const.GET('html_path')
            if os.path.isdir(html_path):
                Const.cleanup(html_path)
            else:
                Const.notify(30104)
                xbmc.executebuiltin('Addon.OpenSettings(%s)' % Const.ADDON_ID)
                xbmc.executebuiltin('SetFocus(101)') # select 2nd category
                xbmc.executebuiltin('SetFocus(201)') # select 2nd control
                sys.exit()
        self.html_path = html_path
        # ファイルパス変換
        if Const.GET('translate_path') == 'true':
            self.new_path = Const.GET('music_path')
            self.old_path = Const.GET('oldmusic_path')
        else:
            self.new_path = self.old_path = ''

    def loadplist(self, file):
        parser = iterparse(file)
        for action, elem in parser:
            unmarshal = Const.UNMARSHALLERS.get(elem.tag)
            if unmarshal:
                data = unmarshal(elem)
                elem.clear()
                elem.text = data
            elif elem.tag != 'plist':
                raise IOError('unknown plist type: %r' % elem.tag)
        return parser.root[0].text

    def setup_path(self, plist, fileType=None):
        # skip some top level playlists
        if plist.get('Master'): return None
        if plist.get('Distinguished Kind'): return None
        # append node to tree
        item = {
            'sid': plist.get('Playlist Persistent ID'),
            'pid': plist.get('Parent Persistent ID'),
            'name': Const.normalize(plist['Name'].replace('/', ' - '))
        }
        tree = self.tree
        if fileType is None:
            tree.append(item)
        dirs = [item['name']]
        f1 = item
        while not f1['pid'] is None:
            pid = f1['pid']
            for f2 in tree:
                if f2['sid'] == pid:
                    f1 = f2
                    dirs.insert(0, f1['name'])
                    break
        if fileType:
            dirs[-1] += '.' + fileType
        result = self.root
        for d in dirs:
            result = os.path.join(result, d)
        return result

    def write_m3u(self, p):
        # このプレイリストのファイルパス
        filepath = self.setup_path(p, fileType='m3u')
        if filepath is None: return
        # 書き込み先のファイルを開く
        with open(filepath, 'w') as f:
            # m3uヘッダを書き込む
            f.write('#EXTM3U\n')
            # プレイリストの全てのトラックについて
            for t in p['Playlist Items']:
                try:
                    trackId = t['Track ID']
                    music = Music(self.playlist['Tracks'][str(trackId)])
                    # 属性を書き込む
                    location = music.location(self.old_path, self.new_path)
                    if location:
                        f.write('#EXTINF:{totalTime},{title}\n'.format(
                            totalTime=int(music.totalTime/1000),
                            title=music.title))
                        f.write('{location}\n'.format(
                            location=location))
                except:
                    Const.log('parse failed in Track ID %s' % t['Track ID'])

    def write_html(self, p):
        # このプレイリストのファイルパス
        filepath = self.setup_path(p, fileType='html')
        if filepath is None: return
        # 書き込み先のファイルを開く
        with open(filepath, 'w') as f:
            # htmlヘッダを書き込む
            f.write(self.template['header'].format(
                title=Const.normalize(p['Name'])))
            # プレイリストの全てのトラックについて
            for t in p['Playlist Items']:
                try:
                    trackId = t['Track ID']
                    music = Music(self.playlist['Tracks'][str(trackId)])
                    # 属性を書き込む
                    f.write(self.template['description'].format(
                        trackId=trackId,
                        title=music.title,
                        artist=music.artist,
                        album=music.album,
                        year=music.year,
                        duration=music.duration,
                        track=music.track,
                        disc=music.disc,
                        dateAdded=music.dateAdded))
                except:
                    Const.log('parse failed in Track ID %s' % t['Track ID'])
            # htmlフッタを書き込む
            f.write(self.template['footer'])

    def write_index(self, root, dirname):
        dirpath = os.path.join(root, dirname)
        filepath = os.path.join(dirpath, 'index.html')
        with open(filepath, 'w') as f:
            # htmlヘッダを書き込む
            f.write(self.template['header'].format(
                title=dirname if dirname else 'iTunes'))
            # ディレクトリの自分以外のファイルについて
            for link in sorted(os.listdir(dirpath)):
                if link != 'index.html':
                    f.write(self.template['index'].format(
                        link=link,
                        name=link.replace('.html', '')))
            # htmlフッタを書き込む
            f.write(self.template['footer'])

    def convert_to_m3u(self):
        # 作業変数を初期化
        self.tree = []
        self.root = self.m3u_path
        # 全てのプレイリストについて
        for p in self.playlist['Playlists']:
            # ディレクトリを作成
            if 'Folder' in p:
                os.makedirs(self.setup_path(p))
            # ファイルを作成
            elif 'Playlist Items' in p:
                self.write_m3u(p)

    def convert_to_html(self):
        # 作業変数を初期化
        self.tree = []
        self.root = self.html_path
        # テンプレートを読み込む
        self.template = {}
        for section in ('header','footer','description','index'):
            with open(os.path.join(Const.DATA_PATH, section),'r') as f:
                self.template[section]  = f.read()
        # 全てのプレイリストについて
        for p in self.playlist['Playlists']:
            # ディレクトリを作成
            if 'Folder' in p:
                os.makedirs(self.setup_path(p))
            # ファイルを作成
            elif 'Playlist Items' in p:
                self.write_html(p)
        # 各ディレクトリにインデクスファイルを作成
        for root, dirs, files in os.walk(self.html_path, topdown=False):
            for name in dirs:
                self.write_index(root, name)
            self.write_index(root, '')

    def convert(self):
        # 開始通知
        xbmc.executebuiltin('XBMC.Notification("%s","Updating playlists...",3000,"DefaultIconInfo.png")' % Const.ADDON_NAME)
        # load playlist
        self.playlist = self.loadplist(Const.LIBRARY_PATH)
        # generate m3u playlists
        self.convert_to_m3u()
        # generate html playlists
        if Const.GET('create_html') == 'true': self.convert_to_html()
        # 完了通知
        xbmc.executebuiltin('XBMC.Notification("%s","Playlists have been updated",10000,"DefaultIconInfo.png")' % Const.ADDON_NAME)


if __name__  == '__main__':
    args = urlparse.parse_qs(sys.argv[2][1:])
    action = args.get('action')
    if action is None:
        if xbmcgui.Dialog().yesno(Const.ADDON_NAME, Const.STR(30202)):
            xbmc.executebuiltin('XBMC.RunPlugin(plugin://%s/?action=convert)' % Const.ADDON_ID)
    else:
        Converter().convert()
