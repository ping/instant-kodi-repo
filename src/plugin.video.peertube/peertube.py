# A Kodi Addon to play video hosted on the peertube service (http://joinpeertube.org/)
#
# TODO: - Delete downloaded files by default
#       - Allow people to choose if they want to keep their download after watching?
#       - Do sanity checks on received data
#       - Handle languages better (with .po files)
#       - Get the best quality torrent given settings and/or available bandwidth
#         See how they do that in the peerTube client's code 

import time, sys
import urllib2, json
from urlparse import parse_qsl
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import AddonSignals

class PeertubeAddon():
    """
    Main class of the addon
    """

    def __init__(self, plugin, plugin_id):
        """
        Initialisation of the PeertubeAddon class
        :param plugin, plugin_id: str, int
        :return: None
        """

        xbmc.log('PeertubeAddon: Initialising', xbmc.LOGDEBUG)
 
        # Save addon URL and ID
        self.plugin_url = plugin
        self.plugin_id = plugin_id

        # Get an Addon instance
        addon = xbmcaddon.Addon()

        # Select preferred instance by default
        self.selected_inst = addon.getSetting('preferred_instance') 

        # Get the number of videos to show per page 
        self.items_per_page = int(addon.getSetting('items_per_page'))

        # Get the video sort method
        self.sort_method = addon.getSetting('video_sort_method')

        # Get the preferred resolution for video
        self.preferred_resolution = addon.getSetting('preferred_resolution')

        # Nothing to play at initialisation
        self.play = 0
        self.torrent_name = ''
        
        return None

    def query_peertube(self, req):
        """
        Issue a PeerTube API request and return the results
        :param req: str
        :result data: dict
        """

        # Send the PeerTube REST API request
        try:
            xbmc.log('PeertubeAddon: Issuing request {0}'.format(req), xbmc.LOGDEBUG)
            resp = urllib2.urlopen(req)
            data = json.load(resp)
        except:
            xbmcgui.Dialog().notification('Communication error', 'Error during my request on {0}'.format(self.selected_inst), xbmcgui.NOTIFICATION_ERROR)
            return None

        # Return when no results are found
        if data['total'] == 0:
            xbmc.log('PeertubeAddon: No result found', xbmc.LOGDEBUG)
            return None
        else:
            xbmc.log('PeertubeAddon: Found {0} results'.format(data['total']), xbmc.LOGDEBUG)

        return data

    def create_list(self, lst, data_type, start):
        """
        Create an array of xmbcgui.ListItem's from the lst parameter
        :param lst, data_type, start: dict, str, str
        :result listing: array
        """
        # Create a list for our items.
        listing = []
        for data in lst['data']:

            # Create a list item with a text label
            list_item = xbmcgui.ListItem(label=data['name'])
        
            if data_type == 'videos':
                # Add thumbnail
                list_item.setArt({'thumb': self.selected_inst + '/' + data['thumbnailPath']})

                # Set a fanart image for the list item.
                #list_item.setProperty('fanart_image', data['thumb'])

                # Compute media info from item's metadata
                info = {'title':data['name'],
                        'playcount': data['views'],
                        'plotoutline': data['description'],
                        'duration': data['duration']
                        }

                # For videos, add a rating based on likes and dislikes
                if data['likes'] > 0 or data['dislikes'] > 0:
                    info['rating'] = data['likes']/(data['likes'] + data['dislikes'])

                # Set additional info for the list item.
                list_item.setInfo('video', info) 

                # Videos are playable
                list_item.setProperty('IsPlayable', 'true')

                # Find the URL of the best possible video matching user's preferrence
                # TODO: Error handling
                current_res = 0
                higher_res = -1
                torrent_url = ''
                resp = urllib2.urlopen(self.selected_inst + '/api/v1/videos/' + data['uuid'])
                metadata = json.load(resp)
                xbmc.log('PeertubeAddon: Looking for the best possible video matching user preferrences', xbmc.LOGDEBUG)
                for f in metadata['files']:
                  # Get file resolution
                  res = f['resolution']['id']
                  if res == self.preferred_resolution:
                    # Stop directly, when we find the exact same resolution as the user's preferred one
                    xbmc.log('PeertubeAddon: Found video with preferred resolution', xbmc.LOGDEBUG)
                    torrent_url = f['torrentUrl'] 
                    break
                  elif res < self.preferred_resolution and res > current_res:
                    # Else, try to find the best one just below the user's preferred one
                    xbmc.log('PeertubeAddon: Found video with good lower resolution ({0})'.format(f['resolution']['label']), xbmc.LOGDEBUG)
                    torrent_url = f['torrentUrl'] 
                    current_res = res
                  elif res > self.preferred_resolution and ( res < higher_res or higher_res == -1 ):
                    # In the worth case, we'll take the one just above the user's preferred one
                    xbmc.log('PeertubeAddon: Saving video with higher resolution ({0}) as a possible alternative'.format(f['resolution']['label']), xbmc.LOGDEBUG)
                    backup_url = f['torrentUrl'] 
                    higher_res = res

                # Use smallest file with an higher resolution, when we didn't find a resolution equal or
                # slower than the user's preferred one
                if not torrent_url:
                  xbmc.log('PeertubeAddon: Using video with higher resolution as alternative', xbmc.LOGDEBUG)
                  torrent_url = backup_url

                # Compose the correct URL for Kodi
                url = '{0}?action=play_video&url={1}'.format(self.plugin_url, torrent_url)
            
            elif data_type == 'instances':
                # TODO: Add a context menu to select instance as preferred instance
                # Instances are not playable
                list_item.setProperty('IsPlayable', 'false')

                # Set URL to select this instance
                url = '{0}?action=select_instance&url={1}'.format(self.plugin_url, data['host'])

            # Add our item to the listing as a 3-element tuple.
            listing.append((url, list_item, False))

        # Add a 'Next page' button when there are more data to show
        start = int(start) + self.items_per_page
        if lst['total'] > start:
            list_item = xbmcgui.ListItem( label='Next page ({0})'.format(start/self.items_per_page) )
            url = '{0}?action=browse_{1}&start={2}'.format(self.plugin_url, data_type, start)
            listing.append((url, list_item, True))

        return listing

    def search_videos(self, start):
        """
        Function to search for videos on a PeerTube instance and navigate in the results
        :param start: string
        :result: None
        """

        # Show a 'Search videos' dialog
        search = xbmcgui.Dialog().input(heading='Search videos on ' + self.selected_inst, type=xbmcgui.INPUT_ALPHANUM)

        # Go back to main menu when user cancels
        if not search:
            return None
         
        # Create the PeerTube REST API request for searching videos
        req = '{0}/api/v1/search/videos?search={1}&count={2}&start={3}&sort={4}'.format(self.selected_inst, search, self.items_per_page, start, self.sort_method)

        # Send the query
        results = self.query_peertube(req)

        # Exit directly when no result is found
        if not results:
            xbmcgui.Dialog().notification('No videos found', 'No videos found matching query', xbmcgui.NOTIFICATION_WARNING)
            return None

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'videos', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)

        return None
        
    def browse_videos(self, start):
        """
        Function to navigate through all the video published by a PeerTube instance
        :param start: string
        :return: None
        """

        # Create the PeerTube REST API request for listing videos
        req = '{0}/api/v1/videos?count={1}&start={2}&sort={3}'.format(self.selected_inst, self.items_per_page, start, self.sort_method)

        # Send the query
        results = self.query_peertube(req)

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'videos', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)

        return None

    def browse_instances(self, start):
        """ 
        Function to navigate through all PeerTube instances
        :param start: str
        :return: None
        """

        # Create the PeerTube REST API request for browsing PeerTube instances
        req = '{0}/api/v1/instances?count={1}&start={2}'.format('https://instances.joinpeertube.org', self.items_per_page, start)

        # Send the query
        results = self.query_peertube(req)

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'instances', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)
 
        return None

    def play_video_continue(self, data):
        """
        Callback function to let the play_video function resume when the PeertubeDownloader
            has downloaded all the torrent's metadata
        :param data: dict
        :return: None
        """

        xbmc.log('PeertubeAddon: Received metadata_downloaded signal, will start playing media', xbmc.LOGDEBUG)
        self.play = 1    
        self.torrent_f = data['file']

        return None

    def play_video(self, torrent_url):
        """
        Start the torrent's download and play it while being downloaded
        :param torrent_url: str
        :return: None
        """

        xbmc.log('PeertubeAddon: Starting torrent download ({0})'.format(torrent_url), xbmc.LOGDEBUG)

        # Start a downloader thread
        AddonSignals.sendSignal('start_download', {'url': torrent_url})

        # Wait until the PeerTubeDownloader has downloaded all the torrent's metadata 
        AddonSignals.registerSlot('plugin.video.peertube', 'metadata_downloaded', self.play_video_continue)
        timeout = 0
        while self.play == 0 and timeout < 10:
            xbmc.sleep(1000)
            timeout += 1

        # Abort in case of timeout
        if timeout == 10:
            xbmcgui.Dialog().notification('Download timeout', 'Timeout fetching ' + torrent_url, xbmcgui.NOTIFICATION_ERROR)
            return None
        else:
            # Wait a little before starting playing the torrent
            xbmc.sleep(3000)

        # Pass the item to the Kodi player for actual playback.
        xbmc.log('PeertubeAddon: Starting video playback ({0})'.format(torrent_url), xbmc.LOGDEBUG)
        play_item = xbmcgui.ListItem(path=self.torrent_f)
        xbmcplugin.setResolvedUrl(self.plugin_id, True, listitem=play_item)

        return None
        
    def select_instance(self, instance):
        """
        Change currently selected instance to 'instance' parameter
        :param instance: str
        :return: None
        """
 
        self.selected_inst = 'https://' + instance
        xbmcgui.Dialog().notification('Current instance changed', 'Changed current instance to {0}'.format(self.selected_inst), xbmcgui.NOTIFICATION_INFO)
        xbmc.log('PeertubeAddon: Changing currently selected instance to {0}'.format(self.selected_inst), xbmc.LOGDEBUG)

        return None

    def main_menu(self):
        """
        Addon's main menu
        :param: None
        :return: None
        """

        # Create a list for our items.
        listing = []

        # 1st menu entry
        list_item = xbmcgui.ListItem(label='Browse selected instance')
        url = '{0}?action=browse_videos&start=0'.format(self.plugin_url)
        listing.append((url, list_item, True))

        # 2nd menu entry
        list_item = xbmcgui.ListItem(label='Search on selected instance')
        url = '{0}?action=search_videos&start=0'.format(self.plugin_url)
        listing.append((url, list_item, True))

        # 3rd menu entry
        list_item = xbmcgui.ListItem(label='Select other instance')
        url = '{0}?action=browse_instances&start=0'.format(self.plugin_url)
        listing.append((url, list_item, True))

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.plugin_id)
 
        return None

    def router(self, paramstring):
        """
        Router function that calls other functions
        depending on the provided paramstring
        :param paramstring: dict
        :return: None
        """

        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        params = dict(parse_qsl(paramstring[1:]))

        # Check the parameters passed to the plugin
        if params:
            if params['action'] == 'browse_videos':
                # Browse videos on selected instance
                self.browse_videos(params['start'])
            elif params['action'] == 'search_videos':
                # Search for videos on selected instance
                self.search_videos(params['start'])
            elif params['action'] == 'browse_instances':
                # Browse peerTube instances
                self.browse_instances(params['start'])
            elif params['action'] == 'play_video':
                # Play video from provided URL.
                self.play_video(params['url'])
            elif params['action'] == 'select_instance':
                self.select_instance(params['url'])
        else:
            # Display the addon's main menu when the plugin is called from Kodi UI without any parameters
            self.main_menu()

        return None

if __name__ == '__main__':

    # Initialise addon
    addon = PeertubeAddon(sys.argv[0], int(sys.argv[1]))
    # Call the router function and pass the plugin call parameters to it.
    addon.router(sys.argv[2])
