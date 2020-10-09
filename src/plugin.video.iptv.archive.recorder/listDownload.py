from __future__ import unicode_literals

import locale
import time
from datetime import datetime
from dateutil import parser
from kodi_six import xbmc, xbmcgui

DATE_FORMAT = "%Y-%m-%d %H:%M:00"

def log(x):
    xbmc.log(repr(x), xbmc.LOGERROR)

def get_format():
    dateFormat = xbmc.getRegion('datelong')
    timeFormat = xbmc.getRegion('time').replace('%H%H', '%H').replace('%I%I', '%I')
    timeFormat = timeFormat.replace(":%S", "")
    return "{}, {}".format(dateFormat, timeFormat)

def extract_date(dateLabel, timeLabel):
    date = xbmc.getInfoLabel(dateLabel)
    dateNew = saneDate(date)
    timeString = xbmc.getInfoLabel(timeLabel)
    fullDate = "{}, {}".format(dateNew, timeString)
    parsedDate = parser.parse(fullDate)
    return datetime.strftime(parsedDate, DATE_FORMAT)

def saneDate(fullDate):
    fullDate = fullDate.replace('Poniedzia\u0142ek', 'Monday')
    fullDate = fullDate.replace("Wtorek", "Tuesday")
    fullDate = fullDate.replace('\u015aroda', 'Wednesday')
    fullDate = fullDate.replace('Czwartek', 'Thursday')
    fullDate = fullDate.replace('Pi\u0105tek', 'Friday')
    fullDate = fullDate.replace('Sobota', 'Saturday')
    fullDate = fullDate.replace('Niedziela', 'Sunday')
    fullDate = fullDate.replace('Stycznia', 'January')
    fullDate = fullDate.replace('Lutego', 'February')
    fullDate = fullDate.replace('Marca', 'March')
    fullDate = fullDate.replace('Kwietnia', 'April')
    fullDate = fullDate.replace('Maja', 'May')
    fullDate = fullDate.replace('Czerwca', 'June')
    fullDate = fullDate.replace('Lipca', 'July')
    fullDate = fullDate.replace('Sierpnia', 'August')
    fullDate = fullDate.replace('Wrze\u015bnia', 'September')
    fullDate = fullDate.replace('Pa\u017adziernika', 'October')
    fullDate = fullDate.replace('Listopada', 'November')
    fullDate = fullDate.replace('Grudnia', 'December')
    return fullDate

fullFormat = get_format()
dialog = xbmcgui.Dialog()
start_time = dialog.input('Enter start time', type=xbmcgui.INPUT_TIME)
end_time = dialog.input('Enter end time', type=xbmcgui.INPUT_TIME)

channel = xbmc.getInfoLabel("ListItem.ChannelName")
channel = channel.replace('+', '')
title = 'Recording'

yes_no = dialog.yesno('Confirm downloading','Your about to download {}\'s stream from {} to {}'.format(channel,start_time, end_time))

if (yes_no == 1):
    try:
        start = extract_date("ListItem.StartDate", start_time)
        stop = extract_date("ListItem.EndDate", end_time)
        log("Start: {}, End: {}".format(start, stop))
        try:
            cmd = "PlayMedia(plugin://plugin.video.iptv.archive.downloader/record_epg/%s/%s/%s/%s)" % (channel,
                                                                                                   title,
                                                                                                   start,
                                                                                                   stop)
            xbmc.executebuiltin(cmd)

            message = "{}: {} ({} to {})'".format(xbmc.getInfoLabel(
            "ListItem.ChannelName"), xbmc.getInfoLabel("ListItem.Label"), start, stop)
        except:
            xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                      "Could not download recording", xbmcgui.NOTIFICATION_WARNING)
    except Exception as e:
        xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                  "Error parsing dates", xbmcgui.NOTIFICATION_ERROR)
        log("IPTV Archive Downloader: Error parsing dates ({})".format(e))
