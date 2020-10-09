# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from xbmcswift2 import Plugin, ListItem
from collections import namedtuple
from datetime import datetime, timedelta, tzinfo
from language import get_string
import base64
import calendar
import chardet
import ctypes
import glob
import gzip
import io
import json
import os, os.path
import platform
import random
import re
import requests
import shutil
import sqlite3
import stat
import subprocess
import threading
import time
import unicodedata

try:
    from urllib.parse import quote, quote_plus, unquote_plus
    from html import unescape as html_unescape
    from io import StringIO
    class HTMLParser:
        def unescape(self, string):
            return html_unescape(string)
except ImportError:
    from urllib import quote, quote_plus, unquote_plus
    from HTMLParser import HTMLParser
    from StringIO import StringIO

import uuid
from kodi_six import xbmc, xbmcaddon, xbmcvfs, xbmcgui
from kodi_six.utils import encode_decode

def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')


def log(v):
    xbmc.log(repr(v), xbmc.LOGERROR)



plugin = Plugin()
big_list_view = True

@encode_decode
def plugin_url_for(plugin, *args, **kwargs):
    return plugin.url_for(*args, **kwargs)

if plugin.get_setting('multiline', str) == "true":
    CR = "[CR]"
else:
    CR = ""


def get_icon_path(icon_name):
    return "special://home/addons/%s/resources/img/%s.png" % (addon_id(), icon_name)


def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]", '', label, flags=re.I)
    label = re.sub(r"\[/?COLOR.*?\]", '', label, flags=re.I)
    return label


def escape( str ):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str


def unescape( str ):
    str = str.replace("&lt;", "<")
    str = str.replace("&gt;", ">")
    str = str.replace("&quot;", "\"")
    str = str.replace("&amp;", "&")
    return str


# def delete(path):
#     dirs, files = xbmcvfs.listdir(path)
#     for file in files:
#         xbmcvfs.delete(path+file)
#     for dir in dirs:
#         delete(path + dir + '/')
#     xbmcvfs.rmdir(path)

# def rmdirs(path):
#     path = xbmc.translatePath(path)
#     dirs, files = xbmcvfs.listdir(path)
#     for dir in dirs:
#         rmdirs(os.path.join(path,dir))
#     xbmcvfs.rmdir(path)


# def find(path):
#     path = xbmc.translatePath(path)
#     all_dirs = []
#     all_files = []
#     dirs, files = xbmcvfs.listdir(path)
#     for file in files:
#         file_path = os.path.join(path,file)
#         all_files.append(file_path)
#     for dir in dirs:
#         dir_path = os.path.join(path,dir)
#         all_dirs.append(dir_path)
#         new_dirs, new_files = find(os.path.join(path, dir))
#         for new_dir in new_dirs:
#             new_dir_path = os.path.join(path,dir,new_dir)
#             all_dirs.append(new_dir_path)
#         for new_file in new_files:
#             new_file = os.path.join(path,dir,new_file)
#             all_files.append(new_file)
#     return all_dirs, all_files

def check_has_db_filled_show_error_message_ifn(db_cursor):
    table_found = db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='streams'").fetchone()
    if not table_found:
        xbmcgui.Dialog().notification("IPTV Recorder", get_string("Database not found"))
        return False
    return True

@plugin.route('/play_channel/<channelname>')
def play_channel(channelname):
    conn = sqlite3.connect(xbmc.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')))
    c = conn.cursor()
    if not check_has_db_filled_show_error_message_ifn(c):
        return

    channel = c.execute("SELECT url FROM streams WHERE name=?", (channelname, )).fetchone()

    if not channel:
        return
    url = channel[0]
    #plugin.set_resolved_url(url)
    xbmc.Player().play(url)


@plugin.route('/play_external/<path>')
def play_external(path):
    cmd = [plugin.get_setting('external.player', str)]

    args = plugin.get_setting('external.player.args', str)
    if args:
        cmd.append(args)

    cmd.append(xbmc.translatePath(path))

    subprocess.Popen(cmd,shell=windows())


def xml2local(xml):
    #TODO combine
    return utc2local(xml2utc(xml))


def utc2local(utc):
    timestamp = calendar.timegm(utc.timetuple())
    local = datetime.fromtimestamp(timestamp)
    return local.replace(microsecond=utc.microsecond)


def str2dt(string_date):
    format ='%Y-%m-%d %H:%M:%S'
    try:
        res = datetime.strptime(string_date, format)
    except TypeError:
        res = datetime(*(time.strptime(string_date, format)[0:6]))
    return utc2local(res)


def total_seconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6


def windows():
    if os.name == 'nt':
        return True
    else:
        return False


def android_get_current_appid():
    with open("/proc/%d/cmdline" % os.getpid()) as fp:
        return fp.read().rstrip("\0")


def ffmpeg_location():
    ffmpeg_src = xbmc.translatePath(plugin.get_setting('ffmpeg', str))

    if xbmc.getCondVisibility('system.platform.android'):
        ffmpeg_dst = '/data/data/%s/ffmpeg' % android_get_current_appid()

        if (plugin.get_setting('ffmpeg', str) != plugin.get_setting('ffmpeg.last', str)) or (not xbmcvfs.exists(ffmpeg_dst) and ffmpeg_src != ffmpeg_dst):
            xbmcvfs.copy(ffmpeg_src, ffmpeg_dst)
            plugin.set_setting('ffmpeg.last',plugin.get_setting('ffmpeg', str))

        ffmpeg = ffmpeg_dst
    else:
        ffmpeg = ffmpeg_src

    if ffmpeg:
        try:
            st = os.stat(ffmpeg)
            if not (st.st_mode & stat.S_IXUSR):
                try:
                    os.chmod(ffmpeg, st.st_mode | stat.S_IXUSR)
                except:
                    pass
        except:
            pass
    if xbmcvfs.exists(ffmpeg):
        return ffmpeg
    else:
        xbmcgui.Dialog().notification("IPTV Recorder", get_string("ffmpeg exe not found!"))


def debug_dialog(line2, line3, line4):
    xbmcgui.Dialog().ok("Debugging", line2, line3, line4)

@plugin.route('/record_epg/<channelname>/<name>/<start>/<stop>')
def record_epg(channelname, name, start, stop):
    start = get_utc_from_string(start)
    stop = get_utc_from_string(stop)
    do_refresh = False
    watch = False
    remind = False
    channelid = None
    threading.Thread(target=record_once_thread,args=[None, do_refresh, watch, remind, channelid, channelname, start, stop, False, name]).start()

@plugin.route('/record_from_list/<channelname>/<start>/<stop>')
def record_from_list(channelname, start, stop):
    start = get_utc_from_string(start)
    stop = get_utc_from_string(stop)
    watch = False
    remind = False
    channelid = None
    threading.Thread(target=record_once_thread, args=[None, do_refresh, watch, remind, channelid, channelname, start, stop, False, name]).start()


def get_utc_from_string(date_string):
    utcnow = datetime.utcnow()
    ts = time.time()
    utc_offset = total_seconds(datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts))

    r = re.search(r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):\d{2}', date_string)
    if r:
        year, month, day, hour, minute = r.group(1), r.group(2), r.group(3), r.group(4), r.group(5)
        return utcnow.replace(day=int(day), month=int(month), year=int(year), hour=int(hour), minute=int(minute),
                              second=0, microsecond=0) - timedelta(seconds=utc_offset)

def write_in_file(file, string):
    file.write(bytearray(string.encode('utf8')))

def record_once_thread(programmeid, do_refresh=True, watch=False, remind=False, channelid=None, channelname=None, start=None,stop=None, play=False, title=None):
    #TODO check for ffmpeg process already recording if job is re-added  
    conn = sqlite3.connect(xbmc.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    cursor = conn.cursor()
    if not check_has_db_filled_show_error_message_ifn(cursor):
        return
   
    programme = {}
  
    if channelid is not None:
        programme["channelid"] = channelid
    if start:
        programme["start"] = datetime2timestamp(start)
    if stop:
        programme["stop"] = datetime2timestamp(stop)

    nfo = {}
    nfo["programme"] = programme

    if not start and not stop:
        return
    
    local_starttime = utc2local(start)
    local_endtime = utc2local(stop)

    if channelid:
        channel = cursor.execute("SELECT name, url FROM streams WHERE tvg_id=? AND tvg_name=?", (channelid, channelname)).fetchone()
        if not channel:
            channel = cursor.execute("SELECT name, url FROM streams WHERE tvg_id=? AND name=?", (channelid, channelname)).fetchone()
    else:
        channel = cursor.execute("SELECT name, url FROM streams WHERE name=?", (channelname,)).fetchone()
        if not channel:
            channel = cursor.execute("SELECT name, url FROM streams WHERE tvg_name=?", (channelname,)).fetchone()

    if not channel:
        log("No channel {} {}".format(channelname, xbmc.LOGERROR))
        return

    name, url = channel
    if not channelname:
        channelname = name
    nfo["channel"] = {"channelname":channelname}
    if not url:
        log("No url for {} {}".format(channelname, xbmc.LOGERROR))
        return

    url_headers = url.split('|', 1)
    url = url_headers[0]
    headers = {}
    if len(url_headers) == 2:
        sheaders = url_headers[1]
        aheaders = sheaders.split('&')
        if aheaders:
            for h in aheaders:
                k, v = h.split('=', 1)
                headers[k] = unquote_plus(v)

    ftitle = sane_name(title)
    fchannelname = sane_name(channelname)

    folder = ""

    folder = fchannelname
    if ftitle:
        filename = "%s - %s - %s" % (ftitle, fchannelname, local_starttime.strftime("%Y-%m-%d %H-%M"))
    else:
        filename = "%s - %s" % (fchannelname, local_starttime.strftime("%Y-%m-%d %H-%M"))

    
    before = int(plugin.get_setting('minutes.before', str) or "0")
    after = int(plugin.get_setting('minutes.after', str) or "0")
    local_starttime = local_starttime - timedelta(minutes=before)
    local_endtime = local_endtime + timedelta(minutes=after)

    now = datetime.now()   
    if (local_starttime < now) and (local_endtime > now):
        local_starttime = now
        # immediate = True
        past_recording = False
        xbmcgui.Dialog().ok("Can not download live stream","Please try when programme has finished")
        return
    elif (local_starttime < now) and (local_endtime < now):
        # immediate = True
        # local_starttime = now
        past_recording = True
    else:
        # immediate = False
        past_recording = False
        xbmcgui.Dialog().ok("Can not download live stream",
                            "Please try when programme has finished")
        return

    kodi_recordings = xbmc.translatePath(plugin.get_setting('recordings', str))
    ffmpeg_recordings = plugin.get_setting('ffmpeg.recordings', str) or kodi_recordings
    # if series:
    #     dir = os.path.join(kodi_recordings, "TV", folder)
    #     ffmpeg_dir = os.path.join(ffmpeg_recordings, "TV", folder)
    # elif movie:
    #     dir = os.path.join(kodi_recordings, "Movies", folder)
    #     ffmpeg_dir = os.path.join(ffmpeg_recordings, "Movies", folder)
    # else:
    dir = os.path.join(kodi_recordings, folder)
    ffmpeg_dir = os.path.join(ffmpeg_recordings, folder)
    xbmcvfs.mkdirs(dir)
    path = os.path.join(dir, filename)
    json_path = path + '.json'
    nfo_path = path + '.nfo'
    jpg_path = path + '.jpg'
    path = path + '.' + plugin.get_setting('ffmpeg.ext', str)
    path = path.replace("\\", "\\\\")
    ffmpeg = ffmpeg_location()
    if not ffmpeg:
        return

    # Get artwork
    if plugin.get_setting('artwork', bool):
        artwork_url = xbmc.getInfoLabel("ListItem.Icon")
        r = requests.get(artwork_url, stream=True)

        if r.status_code == 200:
            # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
            r.raw.decode_content = True
            with open(jpg_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            log('Image sucessfully Downloaded: {}'.format(jpg_path))
        else:
            log('Image Couldn\'t be retreived')

    # Get and write info
    if plugin.get_setting('nfo', bool):
        plot = xbmc.getInfoLabel("ListItem.Plot")
        nfo_nfo = "Channel: {}\nTitle: {}\nStart: {} - End: {}\nPlot: {}".format(fchannelname,ftitle,start, stop, plot)
        nfo_nfo += "\n\nDownloaed using IPTV Archive Downloader\nhttps://github.com/tbrek/IPTV-Archive-Downloader"
        f = xbmcvfs.File(nfo_path,'w')
        write_in_file(f,nfo_nfo)
        f.close()

    # Write JSON
    if plugin.get_setting('json', bool):
        json_nfo = json.dumps(nfo)
        f = xbmcvfs.File(json_path,'w')
        write_in_file(f, json_nfo)
        f.close()
    
    # Make sure you're in the right timezone
    time_shift = int(plugin.get_setting('external.m3u.shift.1', str) or "0")
    utc = int(datetime2timestamp(local_starttime) - (3600 * time_shift ))
    lutc = int(datetime2timestamp(local_endtime) - (3600 * time_shift ))
    lengthSeconds = lutc-utc
    partLength = int(plugin.get_setting('part.length', str) or "3600")
    # log("Part length: {}s".format(partLength))
    numberOfParts = (lutc-utc)/partLength
    # log("Number of parts: {}".format(numberOfParts))
    remainingSeconds = lengthSeconds-(numberOfParts*partLength)
    xbmcgui.Dialog().notification("Downloading: {}".format(channelname), title, sound=True)
    # Recording hour bits
    for part in range(0, numberOfParts): 
        cmd = [ffmpeg]
        start=utc+(part*partLength)
        stop=start+partLength
        duration=partLength
        # log("Recordind part: {}/{}. Start: {}. Stop: {}".format(part,numberOfParts,start,stop))
        # log("Filename: {}_{}".format(filename,part))
        tempFilename = filename+"_"+"{}".format(part)
        cmd, ffmpeg_recording_path = getCmd(start, stop, cmd, past_recording, url, headers, ffmpeg_dir, tempFilename, duration)
        # log("Command: {}".format(cmd))
        recordSegment(cmd, ffmpeg_recording_path)        
    # Recording remaining minutes
    if remainingSeconds !=0:
        cmd = [ffmpeg]
        start = utc+(partLength * numberOfParts)
        stop = start + remainingSeconds
        # log("Recording remaining seconds: {} from: {}".format(remainingSeconds, start))
        # log("Filename: {}_{}".format(filename,numberOfParts))
        tempFilename = filename+"_"+"{}".format(numberOfParts)
        cmd, ffmpeg_recording_path = getCmd(start,stop, cmd, past_recording, url, headers, ffmpeg_dir, tempFilename, remainingSeconds)
        recordSegment(cmd, ffmpeg_recording_path)
        numberOfParts += 1
    # Do you want to concat it all together  
    if plugin.get_setting('join.segments', bool):
               
        # Concating fragments
        ffmpeg_recording_path = os.path.join(ffmpeg_dir, filename + '.' + plugin.get_setting('ffmpeg.ext', str))
        temp_file_path = os.path.join(ffmpeg_dir, filename + '-temp.' + plugin.get_setting('ffmpeg.ext', str))
        tempFile = open(temp_file_path, "w")
        for fileName in sorted(os.listdir(ffmpeg_dir)):
            if fileName.startswith(filename+"_") and fileName.endswith(".ts"):
                # log("Joining: {}".format(fileName))
                temp = open(ffmpeg_dir+"/"+fileName, "r")
                tempFile.write(temp.read())
                temp.close()
                os.remove(ffmpeg_dir+"/"+fileName)
        tempFile.close()
        # Fixing timestamps
        # log("Fixing timestamps from: {}".format(temp_file_path))
        # log("New file: {}".format(ffmpeg_recording_path))
        cmd = [ffmpeg]
        cmd.append("-i")
        cmd.append(temp_file_path)
        probe_cmd = cmd
        cmd = probe_cmd + \
            ["-fflags", "+genpts",
             "-vcodec", "copy", "-acodec", "copy"]
        if (plugin.get_setting('ffmpeg.pipe', str) == 'true') and not (windows() and (plugin.get_setting('task.scheduler', str) == 'true')):
            cmd = cmd + ['-f', 'mpegts', '-']
        else:
            cmd.append(ffmpeg_recording_path)
        # log("Command: {}".format(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
        f = xbmcvfs.File(ffmpeg_recording_path, "w")
        f.write(bytearray(repr(p.pid).encode('utf-8')))
        f.close()
        video = xbmcvfs.File(ffmpeg_recording_path, "w")
        # playing = False
        while True:
            data = p.stdout.read(1000000)
            if data:
                video.write(bytearray(data))
            else:
                break
        video.close()
        os.remove(temp_file_path)

    xbmcgui.Dialog().ok("Downloading completed",
                        "{} from {} downloaded successfuly.".format(title, channelname))

    if do_refresh:
        refresh()

def recordSegment(cmd, ffmpeg_recording_path):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
    f = xbmcvfs.File(ffmpeg_recording_path, "w")
    f.write(bytearray(repr(p.pid).encode('utf-8')))
    f.close()
    video = xbmcvfs.File(ffmpeg_recording_path, "w")
    # playing = False
    while True:
        data = p.stdout.read(1000000)
        if data:
            video.write(bytearray(data))
        else:
            break
    video.close()

def getCmd(start, stop, cmd, past_recording, url, headers, ffmpeg_dir, filename, duration):
    cmd.append("-i")

    # Check if we are recording from archive
    if past_recording:
        cmd.append(url+"?utc={}&lutc={}".format(start,stop))
    else:
        cmd.append(url)
    for h in headers:
        cmd.append("-headers")
        cmd.append("%s:%s" % (h, headers[h]))
    probe_cmd = cmd
    ffmpeg_recording_path = os.path.join(ffmpeg_dir, filename + '.' + plugin.get_setting('ffmpeg.ext', str))
    cmd = probe_cmd + ["-y", "-t", str(duration), "-fflags","+genpts","-vcodec","copy","-acodec","copy"]
    ffmpeg_reconnect = plugin.get_setting('ffmpeg.reconnect', bool)
    if ffmpeg_reconnect:
        cmd = cmd + ["-reconnect_at_eof", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "300"]
    ffmpeg_args = plugin.get_setting('ffmpeg.args', str)
    if ffmpeg_args:
        cmd = cmd + ffmpeg_args.split(' ')
    if (plugin.get_setting('ffmpeg.pipe', str) == 'true') and not (windows() and (plugin.get_setting('task.scheduler', str) == 'true')):
        cmd = cmd + ['-f', 'mpegts','-']
    else:
        cmd.append(ffmpeg_recording_path)
    return cmd, ffmpeg_recording_path

@plugin.route('/convert/<path>')
def convert(path):
    input = xbmcvfs.File(path,'rb')
    output = xbmcvfs.File(path.replace('.ts','.mp4'),'wb')
    error = open(xbmc.translatePath("special://profile/addon_data/plugin.video.iptv.archive.downloader/errors.txt"), "w", encoding='utf-8')

    cmd = [ffmpeg_location(),"-fflags","+genpts","-y","-i","-","-vcodec","copy","-acodec","copy","-f", "mpegts", "- >>"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error, shell=windows())
    t = threading.Thread(target=read_thread,args=[p,output])
    t.start()
    while True:
        data_bytes = bytes(input.readBytes(100000))
        if not data_bytes:
            break
        p.stdin.write(bytearray(data_bytes))
    p.stdin.close()
    error.close()

def read_thread(p,output):
    while True:
        data = p.stdout.read(100000)
        if not len(data):
            break
        output.write(data)
    output.close()

def sane_name(name):
    if not name:
        return
    # if windows() or (plugin.get_setting('filename.urlencode', str) == 'true'):
        name = quote(name.encode('utf-8'))
        name = name.replace("%20",' ')
        name = name.replace(",", " -")
        name = name.replace('/', "%2F")
        name = name.replace('%2C', " -")
        name = name.replace(':', " -")
        name = name.replace("%3A", " -")
        name = name.replace("%C4%84", "A")
        name = name.replace("%C4%85", "a")
        name = name.replace("%C4%86", "C")
        name = name.replace("%C4%87", "c")
        name = name.replace("%C4%98", "E")
        name = name.replace("%C4%99", "e")
        name = name.replace("%C5%81", "L")
        name = name.replace("%C5%82", "l")
        name = name.replace("%C5%83", "N")
        name = name.replace("%C5%84", "n")
        name = name.replace("%C5%93", "O")
        name = name.replace("%C3%B3", "o")
        name = name.replace("%C5%9A", "S")
        name = name.replace("%C5%9B", "s")
        name = name.replace("%C5%B9", "Z")
        name = name.replace("%C5%BA", "z")
        name = name.replace("%C5%BB", "Z")
        name = name.replace("%C5%BC", "z")
    # else:
        # _quote = {'"': '%22', '|': '%7C', '*': '%2A', '/': '%2F', '<': '%3C', ':': '%3A', '\\': '%5C', '?': '%3F', '>': '%3E'}
        # for char in _quote:
            # name = name.replace(char, _quote[char])
    return name

def refresh():
    containerAddonName = xbmc.getInfoLabel('Container.PluginName')
    AddonName = xbmcaddon.Addon().getAddonInfo('id')
    if (containerAddonName == AddonName) and (plugin.get_setting('refresh', str) == 'true') :
        xbmc.executebuiltin('Container.Refresh')

def datetime2timestamp(dt):
    epoch=datetime.fromtimestamp(0.0)
    td = dt - epoch
    return (td.microseconds + (td.seconds + td.days * 86400) * 10**6) / 10**6

def timestamp2datetime(ts):
    return datetime.fromtimestamp(ts)

def time2str(t):
    return "%02d:%02d" % (t.hour,t.minute)

def str2time(s):
    return datetime.time(hour=int(s[0:1],minute=int(s[3:4])))

def day(timestamp):
    if timestamp:
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        if today.date() == timestamp.date():
            return get_string('Today')
        elif tomorrow.date() == timestamp.date():
            return get_string('Tomorrow')
        elif yesterday.date() == timestamp.date():
            return get_string('Yesterday')
        else:
            return get_string(timestamp.strftime("%A"))

def focus(i):

    #TODO find way to check this has worked (clist.getSelectedPosition returns -1)
    xbmc.sleep(int(plugin.get_setting('scroll.ms', str) or "0"))
    #TODO deal with hidden ..
    win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    cid = win.getFocusId()
    if cid:
        clist = win.getControl(cid)
        if clist:
            try: clist.selectItem(i)
            except: pass


@plugin.route('/service')
def service():
    threading.Thread(target=service_thread).start()


@plugin.route('/full_service')
def full_service():
    xmltv()
    service_thread()


@plugin.route('/service_thread')
def service_thread():
    conn = sqlite3.connect(xbmc.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()
    if not check_has_db_filled_show_error_message_ifn(cursor):
        return

    refresh()

def find_files(root):
    dirs, files = xbmcvfs.listdir(root)
    found_files = []
    for dir in dirs:
        path = os.path.join(xbmc.translatePath(root), dir)
        found_files = found_files + find_files(path)
    file_list = []
    for file in files:
        if file.endswith('.' + plugin.get_setting('ffmpeg.ext', str)):
            file = os.path.join(xbmc.translatePath(root), file)
            file_list.append(file)
    return found_files + file_list


def xml2utc(xml):
    if len(xml) == 14:
        xml = xml + " +0000"
    match = re.search(r'([0-9]{4})([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{2}) ([+-])([0-9]{2})([0-9]{2})', xml)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6))
        sign = match.group(7)
        hours = int(match.group(8))
        minutes = int(match.group(9))
        dt = datetime(year, month, day, hour, minute, second)
        td = timedelta(hours=hours, minutes=minutes)
        if sign == '+':
            dt = dt - td
        else:
            dt = dt + td
        return dt
    return ''

@plugin.route('/xmltv')
def xmltv():
    load_groups = plugin.get_storage('load_groups')
    load_channels = {}

    dialog = xbmcgui.DialogProgressBG()
    dialog.create("IPTV Recorder", get_string("Loading data..."))

    profilePath = xbmc.translatePath(plugin.addon.getAddonInfo('profile'))
    xbmcvfs.mkdirs(profilePath)

    shifts = {}
    streams_to_insert = []

    for x in ["1","2"]:
        dialog.update(0, message=get_string("Finding streams"))
        mode = plugin.get_setting('external.m3u.'+x, str)
        if mode == "0":
            if x == "1":
                try:
                    m3uPathType = xbmcaddon.Addon('pvr.iptvsimple').getSetting('m3uPathType')
                    if m3uPathType == "0":
                        path = xbmcaddon.Addon('pvr.iptvsimple').getSetting('m3uPath')
                    else:
                        path = xbmcaddon.Addon('pvr.iptvsimple').getSetting('m3uUrl')
                except:
                    path = ""
            else:
                path = ""
        elif mode == "1":
            path = plugin.get_setting('external.m3u.file.'+x, str)
        else:
            path = plugin.get_setting('external.m3u.url.'+x, str)

        if path:

            m3uFile = 'special://profile/addon_data/plugin.video.iptv.archive.downloader/channels'+x+'.m3u'

            xbmcvfs.copy(path, m3uFile)
            f = open(xbmc.translatePath(m3uFile),'rb')
            data = f.read()
            data = data.decode('utf8')
            settings_shift = float(plugin.get_setting('external.m3u.shift.'+x, str))
            global_shift = settings_shift

            header = re.search('#EXTM3U(.*)', data)
            if header:
                tvg_shift = re.search('tvg-shift="(.*?)"', header.group(1))
                if tvg_shift:
                    tvg_shift = tvg_shift.group(1)
                    if tvg_shift:
                        global_shift = float(tvg_shift) + settings_shift

            channels = re.findall('#EXTINF:(.*?)(?:\r\n|\r|\n)(.*?)(?:\r\n|\r|\n|$)', data, flags=(re.I | re.DOTALL))
            total = len(channels)
            i = 0
            for channel in channels:

                name = None
                if ',' in re.sub('tvg-[a-z]+"[^"]*"','',channel[0], flags=re.I):
                    name = channel[0].rsplit(',', 1)[-1].strip()
                    name = name.replace('+','')
                    #name = name.encode("utf8")

                tvg_name = re.search('tvg-name="(.*?)"', channel[0], flags=re.I)
                if tvg_name:
                    tvg_name = tvg_name.group(1) or None
                #else:
                    #tvg_name = name

                tvg_id = re.search('tvg-id="(.*?)"', channel[0], flags=re.I)
                if tvg_id:
                    tvg_id = tvg_id.group(1) or None

                tvg_logo = re.search('tvg-logo="(.*?)"', channel[0], flags=re.I)
                if tvg_logo:
                    tvg_logo = tvg_logo.group(1) or None

                shifts[tvg_id] = global_shift
                tvg_shift = re.search('tvg-shift="(.*?)"', channel[0], flags=re.I)
                if tvg_shift:
                    tvg_shift = tvg_shift.group(1)
                    if tvg_shift and tvg_id:
                        shifts[tvg_id] = float(tvg_shift) + settings_shift

                url = channel[1]
                search = plugin.get_setting('m3u.regex.search', str)
                replace = plugin.get_setting('m3u.regex.replace', str)
                if search:
                    url = re.sub(search, replace, url)

                groups = re.search('group-title="(.*?)"', channel[0], flags=re.I)
                if groups:
                    groups = groups.group(1) or None

                streams_to_insert.append((name, tvg_name, tvg_id, tvg_logo, groups, url.strip(), i))
                i += 1
                percent = 0 + int(100.0 * i / total)
                dialog.update(percent, message=get_string("Finding streams"))


    '''
    missing_streams = conn.execute('SELECT name, tvg_name FROM streams WHERE tvg_id IS null OR tvg_id IS ""').fetchall()
    sql_channels = conn.execute('SELECT id, name FROM channels').fetchall()
    lower_channels = {x[1].lower():x[0] for x in sql_channels}
    for name, tvg_name in missing_streams:
        if tvg_name:
            tvg_id = None
            _tvg_name = tvg_name.replace("_"," ").lower()
            if _tvg_name in lower_channels:
                tvg_id = lower_channels[_tvg_name]
                conn.execute("UPDATE streams SET tvg_id=? WHERE tvg_name=?", (tvg_id, tvg_name))
        elif name.lower() in lower_channels:
            tvg_id = lower_channels[name.lower()]
            conn.execute("UPDATE streams SET tvg_id=? WHERE name=?", (tvg_id, name))
    '''
    
    for _, _, tvg_id, _, groups, _, _ in streams_to_insert:
        if groups in load_groups:
            load_channels[tvg_id] = ""

    dialog.update(0, message=get_string("Creating database"))
    databasePath = os.path.join(profilePath, 'xmltv.db')
    conn = sqlite3.connect(databasePath, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    conn.execute('DROP TABLE IF EXISTS streams')
    conn.execute('CREATE TABLE IF NOT EXISTS streams(uid INTEGER PRIMARY KEY ASC, name TEXT, tvg_name TEXT, tvg_id TEXT, tvg_logo TEXT, groups TEXT, url TEXT, tv_number INTEGER)')
  
    dialog.update(0, message=get_string("Updating database"))
    conn.executemany("INSERT OR IGNORE INTO streams(name, tvg_name, tvg_id, tvg_logo, groups, url, tv_number) VALUES (?, ?, ?, ?, ?, ?, ?)", streams_to_insert)
    conn.commit()
    conn.close()

    dialog.update(100, message=get_string("Finished loading data"))
    time.sleep(1)
    dialog.close()
    return


@plugin.route('/nuke')
def nuke():

    if not (xbmcgui.Dialog().yesno("IPTV Archive Downloader", get_string("Delete Everything and Start Again?"))):
        return

    xbmcvfs.delete(xbmc.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')))
    time.sleep(5)
    full_service()


@plugin.route('/')
def index():
    items = []
    context_items = []
    
    items.append(
        {
            'label': get_string("Recordings Folder"),
            'path': plugin.get_setting('recordings', str),
            'thumbnail': get_icon_path('recordings'),
            'context_menu': context_items,
        })

    items.append(
        {
            'label': get_string("Delete all settings"),
            'path': plugin_url_for(plugin, 'nuke'),
            'thumbnail': get_icon_path('settings'),
            'context_menu': context_items,
        })
    
    
    return items


if __name__ == '__main__':
    plugin.run()

    containerAddonName = xbmc.getInfoLabel('Container.PluginName')
    AddonName = xbmcaddon.Addon().getAddonInfo('id')

    if containerAddonName == AddonName:

        if big_list_view == True:

            view_mode = int(plugin.get_setting('view.mode', str) or "0")

            if view_mode:
                plugin.set_view_mode(view_mode)
