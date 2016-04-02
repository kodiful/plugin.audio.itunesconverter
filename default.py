# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs

import sys, urllib
import os, re
import exceptions
import base64, datetime
import codecs
import unicodedata

from xml.etree.ElementTree import *

addon = xbmcaddon.Addon('plugin.audio.itunesconverter')

template = {}
foldertree = {"m3u":[], "html":[]}

# ファイル/ディレクトリパス
profilepath = xbmc.translatePath(addon.getAddonInfo('profile').decode('utf-8'))
librarypath = os.path.join(profilepath, 'iTunes Music Library.xml')

unmarshallers = {
    # collections
    "array": lambda x: [v.text for v in x],
    "dict": lambda x: dict((x[i].text, x[i+1].text) for i in range(0, len(x), 2)),
    "key": lambda x: x.text or "",
    # simple types
    "string": lambda x: x.text or "",
    "data": lambda x: base64.decodestring(x.text or ""),
    "date": lambda x: datetime.datetime(*map(int, re.findall("\d+", x.text))),
    "true": lambda x: True,
    "false": lambda x: False,
    "real": lambda x: float(x.text),
    "integer": lambda x: int(x.text),
}


def loadplist(file):
    parser = iterparse(file)
    for action, elem in parser:
        unmarshal = unmarshallers.get(elem.tag)
        if unmarshal:
            data = unmarshal(elem)
            elem.clear()
            elem.text = data
        elif elem.tag != "plist":
           raise IOError("unknown plist type: %r" % elem.tag)
    return parser.root[0].text


def loadtemplate(file):
    # file path
    plugin_path = xbmc.translatePath(addon.getAddonInfo('path'))
    resources_path = os.path.join(plugin_path, "resources")
    data_path = os.path.join(resources_path, "data")
    # load
    f = codecs.open(os.path.join(data_path, file),'r','utf-8')
    template = f.read()
    f.close()
    return template


def setup(plist, path, fileType, isFolder=False):
    sid = plist['Playlist Persistent ID'];
    try:
        pid = plist['Parent Persistent ID'];
    except:
        pid = None
    name = plist['Name'].replace('/', ' - ')
    name = unicodedata.normalize('NFC', name)

    # skip some top level playlists
    #if not isFolder and pid is None and re.search("^(?:####!####|App|Podcast|テレビ番組|ミュージック|ムービー|ホームビデオ|ライブラリ|購入したもの)$",name) is not None:
    try:
        master = plist['Master'];
        return None
    except:
        pass
    try:
        special = plist['Distinguished Kind'];
        return None
    except:
        pass

    item = {"sid":sid, "pid":pid, "name":name}
    tree = foldertree[fileType]
    if isFolder:
        tree.append(item)

    dirs = [name]
    f1 = item
    while not f1['pid'] is None:
        pid = f1['pid']
        for i in range(len(tree)):
            f2 = tree[i]
            if f2['sid'] == pid:
                f1 = f2
                dirs.insert(0, f1['name'])
                break

    if not isFolder:
        dirs[-1] += "." + fileType

    result = path
    for d in dirs:
        result = os.path.join(result, d)

    xbmc.log(result.encode('utf-8','ignore'))
    return result


def converttom3u(p, playlist, oldmusicpath, musicpath, m3upath):
    # convert filename
    filename = setup(p, m3upath, "m3u", isFolder=False)
    if filename is None: return
    # open the future playlist file
    outf = codecs.open(filename,'w','utf-8')
    # write the m3u header
    outf.write("#EXTM3U\n")
    # dictionnary with all tracks {'Track ID : 4042},{'Track ID : 4046}, etc
    tracks = p['Playlist Items']
    # Iterate through all tracks in the current playlist
    for t in tracks:
        try:
            track_id = t['Track ID']
            music = playlist['Tracks'][str(track_id)]
            # title
            title = unicodedata.normalize('NFC', music['Name'].encode('utf-8','ignore').decode('utf-8')) # .encode().decode() makes this line work
            # total time
            totalTime = music['Total Time']
            # location
            location = music['Location']
            # write file locations except m4p
            if re.search('\.m4p$',location) is None:
                # title & duration
                outf.write("#EXTINF:%d,%s\n" % (int(totalTime/1000),title))
                # iTunes put quote to transform space to %20 and so, we have to convert them
                location = urllib.unquote(location).decode('utf-8')
                location = unicodedata.normalize('NFC', location)
                # Replace old location to the new location
                if oldmusicpath!="": location = location.replace(oldmusicpath, musicpath)
                # write the file location in the playlist file
                outf.write("%s\n" % (location))
        except:
            print 'parse failed in Track ID %s' % t['Track ID']
            pass
    outf.close()


def converttohtml(p, playlist, htmlpath):
    # convert filename
    filename = setup(p, htmlpath, "html", isFolder=False)
    if filename is None: return
    # open the future playlist file
    outf = codecs.open(filename,'w','utf-8')
    # write html header
    outf.write(template['header'].format(title=p['Name']))
    # dictionary with all tracks {'Track ID : 4042},{'Track ID : 4046}, etc
    tracks = p['Playlist Items']
    # iterate through all tracks in the current playlist
    for t in tracks:
        # trackId
        trackId = t['Track ID']
        music = playlist['Tracks'][str(trackId)]
        # name
        try:
            name = music['Name']
        except:
            name = "n/a"
        # artist
        try:
            artist = music['Artist']
        except:
            artist = "n/a"
        # album
        try:
            album = music['Album']
        except:
            album = "n/a"
        # totaltime
        try:
            totalTime = music['Total Time']
            totalTime /= 1000
            hh = totalTime/3600
            mm = (totalTime-hh*3600)/60
            ss = totalTime%60
            if hh > 0:
                duration = "%d:%02d:%02d" % (hh,mm,ss)
            else:
                duration = "%d:%02d" % (mm,ss)
        except:
            duration = "n/a"
        # disc
        try:
            discNumber = music['Disc Number']
            discCount = music['Disc Count']
            disc = "%d/%d" % (discNumber,discCount)
        except:
            disc = "n/a"
        # track
        try:
            trackNumber = music['Track Number']
            trackCount = music['Track Count']
            track = "%d/%d" % (trackNumber,trackCount)
        except:
            try:
                if trackNumber > 100:
                    track = trackNumber-100
                else:
                    track = trackNumber
            except:
                track = "n/a"
        # year
        try:
            year = music['Year']
            if year == 9999: year = "n/a"
        except:
            year = "n/a"
        # date added
        dateAdded = music['Date Added']
        # write as html
        outf.write(template['description'].format(trackId=trackId,name=name,artist=artist,album=album,year=year,duration=duration,track=track,disc=disc,dateAdded=dateAdded))
    # write html footer
    outf.write(template['footer'])
    outf.close()


def converttoindex(root, dirname):
    dirpath = os.path.join(root, dirname)
    filename = os.path.join(dirpath, "index.html")
    outf = codecs.open(filename,'w','utf-8')
    if dirname == "":
        outf.write(template['header'].format(title="iTunes"))
    else:
        outf.write(template['header'].format(title=dirname))
    for link in os.listdir(dirpath):
        if link != "index.html":
            outf.write(template['index'].format(link=link,name=link.replace(".html", "")))
    outf.write(template['footer'])
    outf.close()


def main():

    # for Windows
    # oldmusicpath = "file://localhost/"
    # musicpath    = ""

    # for Windows(Bootcamp)
    # oldmusicpath = "file://localhost/"
    # musicpath    = "E:/"

    # for MacOS
    # oldmusicpath = "file:///"
    # musicpath    = "/"

    # itunes music library
    librarysrc = addon.getSetting('library_path').decode('utf-8')

    # check file
    if not xbmcvfs.exists(librarysrc):
        builtin = 'XBMC.Notification("iTunes Playlist Converter","%s",10000,"DefaultIconError.png")' % addon.getLocalizedString(30901)
        xbmc.executebuiltin(builtin.encode('utf-8','ignore'))
        addon.openSettings()
        sys.exit()

    # copy file
    try:
        xbmcvfs.copy(librarysrc, librarypath)
    except:
        builtin = 'XBMC.Notification("iTunes Playlist Converter","%s",10000,"DefaultIconError.png")' % addon.getLocalizedString(30903)
        xbmc.executebuiltin(builtin.encode('utf-8','ignore'))
        addon.openSettings()
        sys.exit()

    # htmlpath
    if addon.getSetting('create_html') == "false":
        htmlpath = ""
    else:
        htmlpath = addon.getSetting('html_path').decode('utf-8')
        if htmlpath == "" or not os.path.isdir(htmlpath):
            builtin = 'XBMC.Notification("iTunes Playlist Converter","%s",10000,"DefaultIconError.png")' % addon.getLocalizedString(30902)
            xbmc.executebuiltin(builtin.encode('utf-8','ignore'))
            addon.openSettings()
            sys.exit()

    # file path translation
    if addon.getSetting('translate_path') == "false":
        musicpath = oldmusicpath = ""
    else:
        musicpath = addon.getSetting('music_path').decode('utf-8')
        oldmusicpath = addon.getSetting('oldmusic_path').decode('utf-8')

    # m3u path
    m3upath = xbmc.translatePath('special://profile/playlists/music/').decode('utf-8')
    if not os.path.isdir(m3upath):
        os.makedirs(m3upath)
    else:
        # cleanup
        for root, dirs, files in os.walk(m3upath, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    # htmlpath
    if htmlpath != "" and os.path.isdir(htmlpath):
        # cleanup
        for root, dirs, files in os.walk(htmlpath, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    # load playlist
    playlist = loadplist(librarypath)

    # load templates
    for section in ["header","footer","description","index"]:
        template[section] = loadtemplate(section)

    # iterate through all playlists
    for p in playlist['Playlists']:
        # folder
        if 'Folder' in p:
            # make m3u directories
            dirname = setup(p, m3upath, "m3u", isFolder=True)
            os.makedirs(dirname)
            # make html directories
            if htmlpath != "":
                dirname = setup(p, htmlpath, "html", isFolder=True)
                os.makedirs(dirname)
        # playlist
        elif 'Playlist Items' in p:
            # convert to m3u file
            converttom3u(p, playlist, oldmusicpath, musicpath, m3upath)
            # convert to html file
            if htmlpath != "":
                converttohtml(p, playlist, htmlpath)

    # make html indices
    if htmlpath != "":
        for root, dirs, files in os.walk(htmlpath, topdown=False):
            for name in dirs:
                converttoindex(root, name)
            converttoindex(root, "")

    # notify & exit
    xbmc.executebuiltin('XBMC.Notification("Playlist Converter","Playlists have been Updated",10000,"DefaultIconInfo.png")')
    xbmc.executebuiltin('XBMC.ActivateWindow(Music,Playlists)')


if __name__  == '__main__': main()
