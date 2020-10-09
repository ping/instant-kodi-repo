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
    fullDate = fullDate.replace('Pa\u017cdziernika', 'October')
    fullDate = fullDate.replace('Listopada', 'November')
    fullDate = fullDate.replace('Grudnia', 'December')
    return fullDate

fullFormat = get_format()

channel = xbmc.getInfoLabel("ListItem.ChannelName")
title = xbmc.getInfoLabel("ListItem.Label")
genre = xbmc.getInfoLabel("ListItem.Genre")
start = extract_date("ListItem.StartDate", "ListItem.StartTime")
stop = extract_date("ListItem.EndDate", "ListItem.EndTime")
channel = channel.replace('+','')
season = xbmc.getInfoLabel("ListItem.Season")
episode = xbmc.getInfoLabel("ListItem.Episode")
episode_name = xbmc.getInfoLabel("ListItem.EpisodeName")

if season != "":
    title += " - S{}".format(season)
else:
    title += " "
if episode != "" and season != "":
    title += "E{}".format(episode)
elif episode != "":
    title += " - E{}".format(episode)
if episode_name != "":
    title += " - {}".format(episode_name)

# xbmcgui.Dialog().ok("Channel: {}".format(channel),
#                     "Title: {}".format(title),
#                     "Genre: {}".format(genre))

title = title.replace("%20", ' ')
title = title.replace(",", " -")
title = title.replace('/', '-')
title = title.replace('?', '')
title = title.replace('*', '')
title = title.replace('%2C', " -")
title = title.replace(':', " -")
title = title.replace("%3A", " -")
title = title.replace("\u0104", "A")
title = title.replace("\u0105", "a")
title = title.replace("\u0106", "C")
title = title.replace("\u0107", "c")
title = title.replace("\u0118", "E")
title = title.replace("\u0119", "e")
title = title.replace("\u0141", "L")
title = title.replace("\u0142", "l")
title = title.replace("\u0143", "N")
title = title.replace("\u0144", "n")
title = title.replace("\u00f2", "O")
title = title.replace("\u00f3", "o")
title = title.replace("\u015a", "S")
title = title.replace("\u015b", "s")
title = title.replace("\u0179", "Z")
title = title.replace("\u017a", "z")
title = title.replace("\u017b", "Z")
title = title.replace("\u017c", "z")

try:
    start = extract_date("ListItem.StartDate", "ListItem.StartTime")
    stop = extract_date("ListItem.EndDate", "ListItem.EndTime")

    try:
        cmd = "PlayMedia(plugin://plugin.video.iptv.archive.downloader/record_epg/%s/%s/%s/%s)" % (channel,
                                                                                        title,
                                                                                        start,
                                                                                        stop)
        xbmc.executebuiltin(cmd)

        message = "{}: {} ({} to {})'".format(xbmc.getInfoLabel("ListItem.ChannelName"), xbmc.getInfoLabel("ListItem.Label"), start, stop)
    except:
        xbmcgui.Dialog().notification("IPTV Archive Downloader", "Could not download recording", xbmcgui.NOTIFICATION_WARNING)
except Exception as e:
    xbmcgui.Dialog().notification("IPTV Archive Downloader", "Error parsing dates", xbmcgui.NOTIFICATION_ERROR)
    log("IPTV Archive Downloader: Error parsing dates ({})".format(e))
