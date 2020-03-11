import libtorrent
import time, sys
import xbmc, xbmcvfs
import AddonSignals
from threading import Thread

class PeertubeDownloader(Thread):
    """
    A class to download peertube torrents in the background
    """

    def __init__(self, url, temp_dir):
        """
        Initialise a PeertubeDownloader instance for downloading the torrent specified by url
        :param url, temp_dir: str
        :return: None
        """
        Thread.__init__(self)
        self.torrent = url
        self.temp_dir = temp_dir

    def run(self):
        """
        Download the torrent specified by self.torrent
        :param: None
        :return: None
        """

        xbmc.log('PeertubeDownloader: Opening bitTorent session', xbmc.LOGDEBUG)
        # Open bitTorrent session
        ses = libtorrent.session()
        ses.listen_on(6881, 6891)

        # Add torrent
        xbmc.log('PeertubeDownloader: Adding torrent ' + self.torrent, xbmc.LOGDEBUG)
        h = ses.add_torrent({'url': self.torrent, 'save_path': self.temp_dir})

        # Set sequential mode to allow watching while downloading
        h.set_sequential_download(True)

        # Download torrent
        xbmc.log('PeertubeDownloader: Downloading torrent ' + self.torrent, xbmc.LOGDEBUG)
        signal_sent = 0
        while not h.is_seed():
            xbmc.sleep(1000)
            s = h.status()
            # Inform addon that all the metadata has been downloaded and that it may start playing the torrent
            if s.state >=3 and signal_sent == 0:
                xbmc.log('PeertubeDownloader: Received all torrent metadata, notifying PeertubeAddon', xbmc.LOGDEBUG)
                i = h.torrent_file()
                f = self.temp_dir + i.name()
                AddonSignals.sendSignal('metadata_downloaded', {'file': f})
                signal_sent = 1

        # Everything is done
        return

class PeertubeService():
    """
    """

    def __init__(self):
        """
        PeertubeService initialisation function
        """

        xbmc.log('PeertubeService: Initialising', xbmc.LOGDEBUG)
        # Create our temporary directory
        self.temp = xbmc.translatePath('special://temp') + '/plugin.video.peertube/'
        if not xbmcvfs.exists(self.temp):
            xbmcvfs.mkdir(self.temp)

        return

    def download_torrent(self, data):
        """
        Start a downloader thread to download torrent specified by data['url']
        :param data: dict
        :return: None
        """

        xbmc.log('PeertubeService: Received a start_download signal', xbmc.LOGDEBUG)
        downloader = PeertubeDownloader(data['url'], self.temp) 
        downloader.start()
   
        return

    def run(self):
        """
        Main loop of the PeertubeService class, registring the start_download signal to start a 
            peertubeDownloader thread when needed, and exit when Kodi is shutting down
        """

        # Launch the download_torrent callback function when the 'start_download' signal is received
        AddonSignals.registerSlot('plugin.video.peertube', 'start_download', self.download_torrent)

        # Monitor Kodi's shutdown signal
        xbmc.log('PeertubeService: service started, Waiting for signals', xbmc.LOGDEBUG)
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                # Abort was requested while waiting. We must exit
                # TODO: Clean temporary directory
                break
       
        return

if __name__ == '__main__':
    # Start a peertubeService instance
    xbmc.log('PeertubeService: Starting', xbmc.LOGDEBUG)
    service = PeertubeService()
    service.run()
    xbmc.log('PeertubeService: Exiting', xbmc.LOGDEBUG)
