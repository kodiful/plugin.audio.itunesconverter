# -*- coding: utf-8 -*-

# for Windows
# old_path = 'file://localhost/'
# new_path = ''

# for Windows(Bootcamp)
# old_path = 'file://localhost/'
# new_path = 'E:/'

# for MacOS
# old_path = 'file:///'
# new_path = '/'


import sys
import os
import re
import base64
import datetime
import inspect
import traceback
import unicodedata
import json
import shutil

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from urllib.parse import parse_qs
from urllib.parse import unquote
from xml.etree.ElementTree import iterparse


class Common:

    # アドオン
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo('id')
    ADDON_NAME = ADDON.getAddonInfo('name')

    GET = ADDON.getSetting
    SET = ADDON.setSetting
    STR = ADDON.getLocalizedString

    # ファイル/ディレクトリパス
    PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    LIBRARY_PATH = os.path.join(PROFILE_PATH, 'iTunes Music Library.xml')
    PLUGIN_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
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
        'data': lambda x: base64.decodebytes(x.text.encode()),
        'date': lambda x: datetime.datetime(*map(int, re.findall(r'\d+', x.text))),
        'true': lambda x: True,
        'false': lambda x: False,
        'real': lambda x: float(x.text),
        'integer': lambda x: int(x.text),
    }

    # 通知
    @staticmethod
    def notify(*messages, **options):
        # アドオン
        addon = xbmcaddon.Addon()
        name = addon.getAddonInfo('name')
        # デフォルト設定
        if options.get('error'):
            image = 'DefaultIconError.png'
            level = xbmc.LOGERROR
        else:
            image = 'DefaultIconInfo.png'
            level = xbmc.LOGINFO
        # ポップアップする時間
        duration = options.get('duration', 10000)
        # ポップアップアイコン
        image = options.get('image', image)
        # メッセージ
        messages = ' '.join(map(lambda x: str(x), messages))
        # ポップアップ通知
        xbmc.executebuiltin(f'Notification("{name}","{messages}",{duration},"{image}")')
        # ログ出力
        Common.log(messages, level=level)

    # ログ
    @staticmethod
    def log(*messages, **options):
        # アドオン
        addon = xbmcaddon.Addon()
        # ログレベル、メッセージを設定
        if isinstance(messages[0], Exception):
            level = options.get('level', xbmc.LOGERROR)
            message = '\n'.join(list(map(lambda x: x.strip(), traceback.TracebackException.from_exception(messages[0]).format())))
            if len(messages[1:]) > 0:
                message += ': ' + ' '.join(map(lambda x: str(x), messages[1:]))
        else:
            level = options.get('level', xbmc.LOGINFO)
            frame = inspect.currentframe().f_back
            filename = os.path.basename(frame.f_code.co_filename)
            lineno = frame.f_lineno
            name = frame.f_code.co_name
            id = addon.getAddonInfo('id')
            message = f'Addon "{id}", File "{filename}", line {lineno}, in {name}'
            if len(messages) > 0:
                message += ': ' + ' '.join(map(lambda x: str(x), messages))
        # ログ出力
        xbmc.log(message, level)


# ユニコード正規化デコレータ
def normalize(func):
    def wrapper(*args, **kwargs):
        text = func(*args, **kwargs)
        return text and unicodedata.normalize('NFC', text)
    return wrapper


class Music:

    def __init__(self, music):
        self.music = music

    @normalize
    def location(self, old_path='', new_path=''):
        location = self.music.get('Location')
        # write file locations except m4p
        if location and re.search(r'\.m4p$', location) is None:
            # iTunes put quote to transform space to %20 and so, we have to convert them
            location = unquote(location)
            # replace old location by the new location
            if old_path and location.find(old_path) == 0:
                location = location.replace(old_path, new_path)
        else:
            location = None
        return location

    @property
    @normalize
    def title(self):
        return self.music.get('Name', 'n/a')

    @property
    @normalize
    def artist(self):
        return self.music.get('Artist', 'n/a')

    @property
    @normalize
    def album(self):
        return self.music.get('Album', 'n/a')

    @property
    def totalTime(self):
        return self.music.get('Total Time', 'n/a')

    @property
    def duration(self):
        duration = self.music.get('Total Time')
        if duration:
            duration //= 1000
            hh = duration // 3600
            mm = (duration - hh * 3600) // 60
            ss = duration % 60
            if hh > 0:
                duration = '%d:%02d:%02d' % (hh, mm, ss)
            else:
                duration = '%d:%02d' % (mm, ss)
        else:
            duration = 'n/a'
        return duration

    @property
    def disc(self):
        discNumber = self.music.get('Disc Number')
        discCount = self.music.get('Disc Count')
        if discNumber and discCount:
            disc = '%d/%d' % (discNumber, discCount)
        else:
            disc = 'n/a'
        return disc

    @property
    def track(self):
        trackNumber = self.music.get('Track Number')
        trackCount = self.music.get('Track Count')
        if trackNumber and trackCount:
            track = '%d/%d' % (trackNumber, trackCount)
        else:
            track = 'n/a'
        return track

    @property
    def year(self):
        year = self.music.get('Year')
        if year:
            if year == 9999:
                year = 'n/a'
        else:
            year = 'n/a'
        return year

    @property
    def dateAdded(self):
        return self.music.get('Date Added', 'n/a')

    def attributes(self, id=None):
        if Common.GET('output_link') == 'true':
            key = '<a href="%s" target="_blank">%s</a>' % (self.location(), self.title)
        else:
            key = self.title
        if id:
            key = '%s<!--%s-->' % (key, str(id))
        value = {
            'Artist': self.artist,
            'Album': self.album,
            'Year': self.year,
            'Duration': self.duration,
            'Track': self.track,
            'Disc': self.disc,
            'Added': self.dateAdded.strftime('%Y-%m-%d %H:%M:%S')
        }
        return key, value


class Converter(Common):

    def __init__(self):
        # iTunes Music Libraryへのパス
        library_path = self.GET('library_path')
        # iTunes Music Libraryの有無をチェック
        if not xbmcvfs.exists(library_path):
            self.notify(self.STR(30103))
            xbmc.executebuiltin('Addon.OpenSettings(%s)' % self.ADDON_ID)
            xbmc.executebuiltin('SetFocus(-100)')  # select 1st category
            xbmc.executebuiltin('SetFocus(-80)')  # select 1st control
            sys.exit()
        # iTunes Music Libraryを所定のフォルダへコピー
        try:
            xbmcvfs.copy(library_path, self.LIBRARY_PATH)
        except Exception:
            self.notify(self.STR(30105))
            xbmc.executebuiltin('Addon.OpenSettings(%s)' % self.ADDON_ID)
            xbmc.executebuiltin('SetFocus(-100)')  # select 1st category
            xbmc.executebuiltin('SetFocus(-80)')  # select 1st control
            sys.exit()
        # m3uのパスをチェック
        m3u_path = xbmcvfs.translatePath('special://profile/playlists/music/')
        if os.path.isdir(m3u_path):
            shutil.rmtree(m3u_path)
        os.makedirs(m3u_path)
        self.m3u_path = m3u_path
        # htmlのパスをチェック
        html_path = ''
        if self.GET('create_html') != 'none':
            html_path = self.GET('html_path')
            if os.path.isdir(html_path):
                shutil.rmtree(html_path)
                os.makedirs(html_path)
            else:
                self.notify(self.STR(30104))
                xbmc.executebuiltin('Addon.OpenSettings(%s)' % self.ADDON_ID)
                xbmc.executebuiltin('SetFocus(-99)')  # select 2nd category
                xbmc.executebuiltin('SetFocus(-79)')  # select 2nd control
                sys.exit()
        self.html_path = html_path
        # ファイルパス変換
        if self.GET('translate_path') == 'true':
            self.new_path = self.GET('music_path')
            self.old_path = self.GET('oldmusic_path')
        else:
            self.new_path = self.old_path = ''

    def loadplist(self, file):
        parser = iterparse(file)
        for action, elem in parser:
            unmarshal = self.UNMARSHALLERS.get(elem.tag)
            if unmarshal:
                data = unmarshal(elem)
                elem.clear()
                elem.text = data
            elif elem.tag != 'plist':
                raise IOError('unknown plist type: %r' % elem.tag)
        return parser.root[0].text

    def convert_to_m3u(self):
        # 作業変数を初期化
        buf = {}
        # 全てのプレイリストについて
        for p in self.playlist['Playlists']:
            sid = p.get('Playlist Persistent ID')
            pid = p.get('Parent Persistent ID')
            name = p['Name'].replace('/', ' - ')
            # フォルダ
            if 'Folder' in p:
                if buf.get(sid) is None:
                    if pid is None:
                        buf[sid] = os.path.join(self.m3u_path, name)
                    else:
                        buf[sid] = os.path.join(buf[pid], name)
                    os.makedirs(buf[sid])
            # アイテム
            elif 'Playlist Items' in p:
                if buf.get(pid) is not None:
                    # m3uファイルを作成
                    with open(os.path.join(buf[pid], '%s.m3u' % name), 'w', encoding='utf-8', errors='ignore') as f:
                        # m3uヘッダを書き込む
                        f.write('#EXTM3U\n')
                        # プレイリストの全てのトラックについて
                        for item in p['Playlist Items']:
                            try:
                                id = item['Track ID']
                                music = Music(self.playlist['Tracks'][str(id)])
                                # 属性を書き込む
                                location = music.location(self.old_path, self.new_path)
                                if location:
                                    f.write('#EXTINF:{totalTime},{title}\n'.format(
                                        totalTime=music.totalTime // 1000,
                                        title=music.title))
                                    f.write('{location}\n'.format(
                                        location=location))
                            except Exception as err:
                                self.log('parse failed in Track ID %s: %s' % (id, err))

    def convert_to_html(self):
        # 作業変数を初期化
        buf = {}
        # テンプレートを読み込む
        with open(os.path.join(self.DATA_PATH, 'playlist.html'), 'r', encoding='utf-8') as f:
            playlist = f.read()
        # テンプレートを読み込む
        with open(os.path.join(self.DATA_PATH, 'index.html'), 'r', encoding='utf-8') as f:
            index = f.read()
        # 全てのプレイリストについて
        for p in self.playlist['Playlists']:
            sid = p.get('Playlist Persistent ID')
            pid = p.get('Parent Persistent ID')
            name = p['Name'].replace('/', ' - ')
            # フォルダ
            if 'Folder' in p:
                if buf.get(sid) is None:
                    if pid is None:
                        buf[sid] = os.path.join(self.html_path, name)
                    else:
                        buf[sid] = os.path.join(buf[pid], name)
                    os.makedirs(buf[sid])
            # アイテム
            elif 'Playlist Items' in p:
                if buf.get(pid) is not None:
                    data = {}
                    for item in p['Playlist Items']:
                        try:
                            id = item['Track ID']
                            music = Music(self.playlist['Tracks'][str(id)])
                            key, value = music.attributes()
                            data[key] = value
                        except Exception as err:
                            self.log('parse failed in Track ID %s: %s' % (id, err))
                    # htmlファイルを作成
                    with open(os.path.join(buf[pid], '%s.html' % name), 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(playlist.format(title=name,
                                                data=json.dumps(data),
                                                crumbs=json.dumps(self.crumbs(os.path.join(buf[pid], name), True))))
        # インデクス
        for root, dirs, files in os.walk(self.html_path):
            data = {}
            for item in sorted([x for x in dirs] + [x for x in files]):
                if item.find('.html') > -1:
                    data['<a href="%s">%s</a>' % (item, item.replace('.html', ''))] = {'': ''}
                else:
                    data['<a href="%s/index.html">%s</a>' % (item, item)] = {'': ''}
            # htmlファイルを作成
            with open(os.path.join(root, 'index.html'), 'w', encoding='utf-8', errors='ignore') as f:
                f.write(index.format(
                    title=os.path.basename(root) or 'Top',
                    data=json.dumps(data),
                    crumbs=json.dumps(self.crumbs(root, False))))

    def convert_to_tree(self):
        # 作業変数を初期化
        top = {}
        buf = {}
        # テンプレートを読み込む
        with open(os.path.join(self.DATA_PATH, 'playlist.html'), 'r', encoding='utf-8') as f:
            playlist = f.read()
        # 全てのプレイリストについて
        for p in self.playlist['Playlists']:
            sid = p.get('Playlist Persistent ID')
            pid = p.get('Parent Persistent ID')
            name = p['Name'].replace('/', ' - ')
            # フォルダ
            if 'Folder' in p:
                if buf.get(sid) is None:
                    if pid is None:
                        buf[sid] = top['%s<!--%s-->' % (name, str(sid))] = {}
                    else:
                        buf[sid] = buf[pid]['%s<!--%s-->' % (name, str(sid))] = {}
            # アイテム
            elif 'Playlist Items' in p:
                if buf.get(pid) is not None:
                    buf[sid] = buf[pid]['%s<!--%s-->' % (name, str(sid))] = {}
                    for item in p['Playlist Items']:
                        try:
                            id = item['Track ID']
                            music = Music(self.playlist['Tracks'][str(id)])
                            key, value = music.attributes(str(id))
                            buf[sid][key] = value
                        except Exception as err:
                            self.log('parse failed in Track ID %s: %s' % (id, err))
        # htmlファイルを作成
        with open(os.path.join(self.html_path, 'index.html'), 'w', encoding='utf-8', errors='ignore') as f:
            f.write(playlist.format(title='Tree', data=json.dumps(self.sort(top)), crumbs=json.dumps([])))

    def sort(self, node):
        if node[list(node.keys())[0]].get('Added') is None:
            buf = {}
            for key in sorted(node.keys()):
                buf[key] = node[key]
            node = buf
            for key in node.keys():
                node[key] = self.sort(node[key])
        return node
    
    def crumbs(self, path, leaf):
        path = path.replace(self.html_path, '').strip('/')
        if len(path) > 0:
            items = path.split('/')
            buf = [items.pop()]
            if leaf:
                buf.append('<a href="%s">%s</a>' % ('.', items.pop()))
            for i in range(len(items)):
                buf.append('<a href="%s">%s</a>' % ('/'.join(['..'] * (i+1)), items[-i-1]))
            buf.append('iTunes Playlists | <a href="%s">%s</a>' % ('/'.join(['..'] * (len(items)+1)), 'Top'))
        else:
            buf = ['iTunes Playlists | Top']
        return list(reversed(buf))
    
    def convert(self):
        # 開始通知
        xbmc.executebuiltin('Notification("%s","Updating playlists...",3000,"DefaultIconInfo.png")' % self.ADDON_NAME)
        # load playlist
        self.playlist = self.loadplist(self.LIBRARY_PATH)
        # generate m3u playlists
        self.convert_to_m3u()
        # generate html playlists
        if self.GET('create_html') == 'none':
            pass
        elif self.GET('create_html') == 'separated':
            self.convert_to_html()
        elif self.GET('create_html') == 'combined':
            self.convert_to_tree()
        # 完了通知
        xbmc.executebuiltin('Notification("%s","Playlists have been updated",10000,"DefaultIconInfo.png")' % self.ADDON_NAME)


if __name__ == '__main__':
    args = parse_qs(sys.argv[2][1:])
    action = args.get('action')
    if action is None:
        if xbmcgui.Dialog().yesno(Common.ADDON_NAME, Common.STR(30202)):
            xbmc.executebuiltin('RunPlugin(plugin://%s/?action=convert)' % Common.ADDON_ID)
    else:
        Converter().convert()
