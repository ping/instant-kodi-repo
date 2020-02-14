# -*- coding: utf-8 -*-

import sys
from urllib import urlencode

import inputstreamhelper
import requests
import simplejson as json
import xbmc
import xbmcgui
import xbmcplugin
from urlparse import parse_qsl

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]

# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])


VIDEOS = [
    {
        'name': "ViuTV",
        'thumb': 'https://static.viu.tv/public/images/amsUpload/201701/1484127151250_ChannelLogo99.jpg',
        'video': 'https://dummy/viutv99.m3u8',
    },
    {
        'name': "now 新聞台",
        'thumb': "http://www.nettv.live/uploads/18/1-1PG11QQ2114.jpg",
        'video': 'https://dummy/now332.m3u8',
    },
    {
        'name': "now 直播台",
        'thumb': "http://www.nettv.live/uploads/18/1-1PG11I415a1.jpg",
        'video': 'https://dummy/now331.m3u8',
    },
    {
        'name': '香港開電視',
        'thumb': 'http://plib.aastocks.com/aafnnews/image/medialib/20181026093830853_m.jpg',
        'video': 'http://media.fantv.hk/m3u8/archive/channel2.m3u8',
    },
    {
        'name': "有線 新聞台",
        'thumb': "http://cn.itver.cc/wp-content/uploads/2015/05/cable-tv.jpg",
        'video': 'https://dummy/cabletv109.m3u8',
    },
    {
        'name': "有線 直播新聞台",
        'thumb': "http://cn.itver.cc/wp-content/uploads/2015/05/cable-tv.jpg",
        'video': 'https://dummy/cabletv110.m3u8',
    },
    {
        'name': "港台電視 31",
        'thumb': 'https://www.rthk.hk/assets/rthk/images/tv/player/500x281.jpg',
        'video': 'https://www.rthk.hk/feeds/dtt/rthktv31_https.m3u8',
    },
    {
        'name': "港台電視 32",
        'thumb': 'https://www.rthk.hk/assets/rthk/images/tv/player/500x281.jpg',
        'video': 'https://www.rthk.hk/feeds/dtt/rthktv32_https.m3u8',
    },
]


def get_cabletv(ch):
    params = {
        "device": "aos_mobile",
        "method": "streamingGenerator2",
        "quality": "m",
        "uuid": "",
        "is_premium": "0",
        "network": "wifi",
        "platform": "1",
        "deviceToken": "",
        "appVersion": "6.3.4",
        "market": "G",
        "lang": "zh_TW",
        "version": "6.3.4",
        "osVersion": "23",
        "channel_id": "106",
        "deviceModel": "KODI",
        "type": "live",
    }

    if ch == '109':
        params["channel_no"] = "_9"
        params["vlink"] = "_9"
    elif ch == '110':
        params["channel_no"] = "_10"
        params["vlink"] = "_10"

    response = requests.get(
        'https://mobileapp.i-cable.com/iCableMobile/API/api.php',
        headers={
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 6.0.1; F8132 Build/35.0.A.1.282)',
        },
        params={
            'data': json.dumps(params),
        }
    )

    return response.json()['result']['stream']


def get_viutv():
    response = requests.post(
        'https://api.viu.now.com/p8/2/getLiveURL',
        json={
            'callerReferenceNo': "20190625160500",
            'channelno': "099",
            'deviceId': "7849989bff631f5888",
            'deviceType': "5",
            'format': "HLS",
            'mode': "prod",
        }
    )

    return response.json()['asset']['hls']['adaptive'][0]


def get_nowtv(ch):
    response = requests.post(
        'https://hkt-mobile-api.nowtv.now.com/09/1/getLiveURL',
        json={
            "channelno": ch,
            "mode": "prod",
            "audioCode": "",
            "format": "HLS",
            "callerReferenceNo": "20140702122500",
        }
    )

    return response.json()['asset']['hls']['adaptive'][0]


def get_apple(url):
    response = requests.get(
        url,
    )

    videos = []
    for item in response.json()['content']:
        title = None
        max_video_res = 0
        image = None
        video = None

        for media in item['mediaGroup']:
            if media['type'] == 'videos':
                video_res = int(media['quality'].replace('p', ''))
                if video_res > max_video_res:
                    title = media['title']
                    max_video_res = video_res
                    image = media['largePath']
                    video = media['url']

        videos.append({
            'name': title,
            'thumb': image,
            'video': video,
        })

    return videos


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def list_videos(category=None):
    xbmcplugin.setContent(_handle, 'videos')

    if not category:
        videos = VIDEOS
    elif '蘋果動新聞' in category:
        for v in VIDEOS:
            if v['name'] == category:
                videos = get_apple(v['data_url'])
                break

    for video in videos:
        list_item = xbmcgui.ListItem(label=video['name'])

        list_item.setInfo('video', {
            'title': video['name'],
            'mediatype': 'video',
        })

        list_item.setArt({
            'thumb': video['thumb'],
            'icon': video['thumb'],
            'fanart': video['thumb'],
        })

        if 'video' in video:
            list_item.setProperty('IsPlayable', 'true')

            url = get_url(
                action='play',
                video=video['video'],
            )

            is_folder = False
        elif 'data_url' in video:
            url = get_url(
                action='listing',
                category=video['name'],
            )

            is_folder = True

        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)

    xbmcplugin.endOfDirectory(_handle)


def play_video(STREAM_URL):
    if '.mpd' in STREAM_URL:
        PROTOCOL = 'mpd'
        is_helper = inputstreamhelper.Helper(PROTOCOL)
        if is_helper.check_inputstream():
            playitem = xbmcgui.ListItem(path=STREAM_URL)
            playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
            playitem.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            xbmc.Player().play(item=STREAM_URL, listitem=playitem)
    else:
        playitem = xbmcgui.ListItem(path=STREAM_URL)
        xbmcplugin.setResolvedUrl(_handle, True, listitem=playitem)


def router(paramstring):
    params = dict(parse_qsl(paramstring))

    if params:
        if params['action'] == 'listing':
            list_videos(params['category'])
        elif params['action'] == 'play':
            if params['video'] == 'https://dummy/now332.m3u8':
                url = get_nowtv('332')
            elif params['video'] == 'https://dummy/now331.m3u8':
                url = get_nowtv('331')
            elif params['video'] == 'https://dummy/viutv99.m3u8':
                url = get_viutv()
            elif params['video'] == 'https://dummy/cabletv109.m3u8':
                url = get_cabletv('109')
            elif params['video'] == 'https://dummy/cabletv110.m3u8':
                url = get_cabletv('110')
            else:
                url = params['video']

            play_video(url)
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        list_videos()


if __name__ == '__main__':
    router(sys.argv[2][1:])
