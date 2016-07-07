import discord
from discord.ext import commands
import threading
import os
from random import shuffle, choice
from cogs.utils.dataIO import fileIO
from cogs.utils import checks
from __main__ import send_cmd_help
import re
import logging
import collections
import copy
import asyncio
import math
import time
import inspect

__author__ = "tekulvw"
__version__ = "0.1.1"

log = logging.getLogger("simbad.audio")

try:
    import youtube_dl
except:
    youtube_dl = None

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except OSError:  # Incorrect bitness
    opus = False
except:  # Missing opus
    opus = None
else:
    opus = True

youtube_dl_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'outtmpl': '%(id)s',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'outtmpl': "data/audio/cache/%(id)s",
    'default_search': 'auto'
}


class MaximumLength(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class NotConnected(Exception):
    pass


class AuthorNotConnected(NotConnected):
    pass


class VoiceNotConnected(NotConnected):
    pass


class UnauthorizedConnect(Exception):
    pass


class UnauthorizedSpeak(Exception):
    pass


class UnauthorizedSave(Exception):
    pass


class ConnectTimeout(NotConnected):
    pass


class InvalidURL(Exception):
    pass


class InvalidSong(InvalidURL):
    pass


class InvalidPlaylist(InvalidSong):
    pass


class deque(collections.deque):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def peek(self):
        ret = self.pop()
        self.append(ret)
        return copy.deepcopy(ret)

    def peekleft(self):
        ret = self.popleft()
        self.appendleft(ret)
        return copy.deepcopy(ret)


class Song:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.title = kwargs.pop('title', None)
        self.id = kwargs.pop('id', None)
        self.url = kwargs.pop('url', None)
        self.webpage_url = kwargs.pop('webpage_url', "")
        self.duration = kwargs.pop('duration', "")



class Downloader(threading.Thread):
    def __init__(self, url, max_duration=None, download=False,
                 cache_path="data/audio/cache", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.max_duration = max_duration
        self.done = threading.Event()
        self.song = None
        self.failed = False
        self._download = download
        self.hit_max_length = threading.Event()
        self._yt = None

    def run(self):
        try:
            self.get_info()
            if self._download:
                self.download()
        except MaximumLength:
            self.hit_max_length.set()
        except:
            self.failed = True
        self.done.set()

    def download(self):
        self.duration_check()

        if not os.path.isfile('data/audio/cache' + self.song.id):
            video = self._yt.extract_info(self.url)
            self.song = Song(**video)

    def duration_check(self):
        log.debug("duration {} for songid {}".format(self.song.duration,
                                                     self.song.id))
        if self.max_duration and self.song.duration > self.max_duration:
            log.debug("songid {} too long".format(self.song.id))
            raise MaximumLength("songid {} has duration {} > {}".format(
                self.song.id, self.song.duration, self.max_duration))

    def get_info(self):
        if self._yt is None:
            self._yt = youtube_dl.YoutubeDL(youtube_dl_options)
        if "[SEARCH:]" not in self.url:
            video = self._yt.extract_info(self.url, download=False,
                                          process=False)
        else:
            self.url = self.url[9:]
            yt_id = self._yt.extract_info(
                self.url, download=False)["entries"][0]["id"]
            # Should handle errors here ^
            self.url = "https://youtube.com/watch?v={}".format(yt_id)
            video = self._yt.extract_info(self.url, download=False,
                                          process=False)

        self.song = Song(**video)


class Audio:
    """Music Streaming."""

    def __init__(self, bot):
        self.bot = bot
        self.queue = {}  # add deque's, repeat
        self.downloaders = {}  # sid: object
        self.settings = fileIO("data/audio/settings.json", 'load')
        self.server_specific_setting_keys = ["VOLUME", "QUEUE_MODE",
                                             "VOTE_THRESHOLD"]
        self.cache_path = "data/audio/cache"
        self.local_playlist_path = "data/audio/localtracks"

    def _add_to_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue(server)
        self.queue[server.id]["QUEUE"].append(url)

    def _add_to_temp_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue(server)
        self.queue[server.id]["TEMP_QUEUE"].append(url)

    def _addleft_to_queue(self, server, url):
        if server.id not in self.queue:
            self._setup_queue()
        self.queue[server.id]["QUEUE"].appendleft(url)

    def _cache_desired_files(self):
        filelist = []
        for server in self.downloaders:
            song = self.downloaders[server].song
            try:
                filelist.append(song.id)
            except AttributeError:
                pass
        shuffle(filelist)
        return filelist

    def _cache_max(self):
        setting_max = self.settings["MAX_CACHE"]
        return max([setting_max, self._cache_min()])  # enforcing hard limit

    def _cache_min(self):
        x = self._server_count()
        return max([60, 48 * math.log(x) * x**0.3])  # log is not log10

    def _cache_required_files(self):
        queue = copy.deepcopy(self.queue)
        filelist = []
        for server in queue:
            now_playing = queue[server].get("NOW_PLAYING")
            try:
                filelist.append(now_playing.id)
            except AttributeError:
                pass
        return filelist

    def _cache_size(self):
        songs = os.listdir(self.cache_path)
        size = sum(map(lambda s: os.path.getsize(
            os.path.join(self.cache_path, s)) / 10**6, songs))
        return size

    def _cache_too_large(self):
        if self._cache_size() > self._cache_max():
            return True
        return False

    def _clear_queue(self, server):
        if server.id not in self.queue:
            return
        self.queue[server.id]["QUEUE"] = deque()
        self.queue[server.id]["TEMP_QUEUE"] = deque()

    async def _create_ffmpeg_player(self, server, filename, local=False):
        """This function will guarantee we have a valid voice client,
            even if one doesn't exist previously."""
        voice_channel_id = self.queue[server.id]["VOICE_CHANNEL_ID"]
        voice_client = self.voice_client(server)

        if voice_client is None:
            log.debug("not connected when we should be in sid {}".format(
                server.id))
            to_connect = self.bot.get_channel(voice_channel_id)
            if to_connect is None:
                raise VoiceNotConnected("Okay somehow we're not connected and"
                                        " we have no valid channel to"
                                        " reconnect to. In other words...LOL"
                                        " REKT.")
            log.debug("valid reconnect channel for sid"
                      " {}, reconnecting...".format(server.id))
            await self._join_voice_channel(to_connect)  # SHIT
        elif voice_client.channel.id != voice_channel_id:
            # This was decided at 3:45 EST in #advanced-testing by 26
            self.queue[server.id]["VOICE_CHANNEL_ID"] = voice_client.channel.id
            log.debug("reconnect chan id for sid {} is wrong, fixing".format(
                server.id))

        # Okay if we reach here we definitively have a working voice_client

        if local:
            song_filename = os.path.join(self.local_playlist_path, filename)
        else:
            song_filename = os.path.join(self.cache_path, filename)

        use_avconv = self.settings["AVCONV"]
        volume = self.get_server_settings(server)["VOLUME"] / 100
        options = \
            '-filter "volume=volume={}" -b:a 64k -bufsize 64k'.format(volume)

        try:
            voice_client.audio_player.process.kill()
            log.debug("killed old player")
        except AttributeError:
            pass
        except ProcessLookupError:
            pass

        log.debug("making player on sid {}".format(server.id))

        voice_client.audio_player = voice_client.create_ffmpeg_player(
            song_filename, use_avconv=use_avconv, options=options)

        return voice_client  # Just for ease of use, it's modified in-place

    # TODO: _current_playlist

    # TODO: _current_song

    def _delete_playlist(self, server, name):
        if not name.endswith('.txt'):
            name = name + ".txt"
        try:
            os.remove(os.path.join('data/audio/playlists', server.id, name))
        except OSError:
            pass
        except WindowsError:
            pass

    # TODO: _disable_controls()

    async def _disconnect_voice_client(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        await voice_client.disconnect()

    async def _download_all(self, url_list):
        """
        Doesn't actually download, just get's info for uses like queue_list
        """
        downloaders = []
        for url in url_list:
            d = Downloader(url)
            d.start()
            downloaders.append(d)

        while any([d.is_alive() for d in downloaders]):
            await asyncio.sleep(0.1)

        songs = [d.song for d in downloaders]
        return songs

    async def _download_next(self, server, curr_dl, next_dl):
        """Checks to see if we need to download the next, and does.

        Both curr_dl and next_dl should already be started."""
        if curr_dl.song is None:
            # Only happens when the downloader thread hasn't initialized fully
            #   There's no reason to wait if we can't compare
            return

        max_length = self.settings["MAX_LENGTH"]

        while next_dl.is_alive():
            await asyncio.sleep(0.5)

        if curr_dl.song.id != next_dl.song.id:
            log.debug("downloader ID's mismatch on sid {}".format(server.id) +
                      " gonna start dl-ing the next thing on the queue"
                      " id {}".format(next_dl.song.id))
            try:
                next_dl.duration_check()
            except MaximumLength:
                return
            self.downloaders[server.id] = Downloader(next_dl.url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

    def _dump_cache(self, ignore_desired=False):
        reqd = self._cache_required_files()
        log.debug("required cache files:\n\t{}".format(reqd))

        opt = self._cache_desired_files()
        log.debug("desired cache files:\n\t{}".format(opt))

        prev_size = self._cache_size()

        for file in os.listdir(self.cache_path):
            if file not in reqd:
                if ignore_desired or file not in opt:
                    try:
                        os.remove(os.path.join(self.cache_path, file))
                    except OSError:
                        # A directory got in the cache?
                        pass
                    except WindowsError:
                        # Removing a file in use, reqd failed
                        pass

        post_size = self._cache_size()
        dumped = prev_size - post_size

        if not ignore_desired and self._cache_too_large():
            log.debug("must dump desired files")
            return dumped + self._dump_cache(ignore_desired=True)

        log.debug("dumped {} MB of audio files".format(dumped))

        return dumped

    # TODO: _enable_controls()

    async def _guarantee_downloaded(self, server, url):
        max_length = self.settings["MAX_LENGTH"]
        if server.id not in self.downloaders:  # We don't have a downloader
            log.debug("sid {} not in downloaders, making one".format(
                server.id))
            self.downloaders[server.id] = Downloader(url, max_length)

        if self.downloaders[server.id].url != url:  # Our downloader is old
            # I'm praying to Jeezus that we don't accidentally lose a running
            #   Downloader
            log.debug("sid {} in downloaders but wrong url".format(server.id))
            self.downloaders[server.id] = Downloader(url, max_length)

        try:
            # We're assuming we have the right thing in our downloader object
            self.downloaders[server.id].start()
            log.debug("starting our downloader for sid {}".format(server.id))
        except RuntimeError:
            # Queue manager already started it for us, isn't that nice?
            pass

        # Getting info w/o download
        self.downloaders[server.id].done.wait()

        # This will throw a maxlength exception if required
        self.downloaders[server.id].duration_check()
        song = self.downloaders[server.id].song

        log.debug("sid {} wants to play songid {}".format(server.id, song.id))

        # Now we check to see if we have a cache hit
        cache_location = os.path.join(self.cache_path, song.id)
        if not os.path.exists(cache_location):
            log.debug("cache miss on song id {}".format(song.id))
            self.downloaders[server.id] = Downloader(url, max_length,
                                                     download=True)
            self.downloaders[server.id].start()

            while self.downloaders[server.id].is_alive():
                await asyncio.sleep(0.5)

            song = self.downloaders[server.id].song
        else:
            log.debug("cache hit on song id {}".format(song.id))

        return song

    async def _join_voice_channel(self, channel):
        server = channel.server
        if server.id in self.queue:
            self.queue[server.id]["VOICE_CHANNEL_ID"] = channel.id
        try:
            await self.bot.join_voice_channel(channel)
        except asyncio.futures.TimeoutError as e:
            log.exception(e)
            raise ConnectTimeout("We timed out connecting to a voice channel")

    def _list_local_playlists(self):
        ret = []
        for thing in os.listdir(self.local_playlist_path):
            if os.path.isdir(os.path.join(self.local_playlist_path, thing)):
                ret.append(thing)
        log.debug("local playlists:\n\t{}".format(ret))
        return ret


    def _match_yt_playlist(self, url):
        if not self._match_yt_url(url):
            return False
        yt_playlist = re.compile(
            r'^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)'
            r'(\/playlist\?).*(list=)(.*)(&|$)')
        # Group 6 should be the list ID
        if yt_playlist.match(url):
            return True
        return False

    def _match_sc_url(self, url):
        sc_url = re.compile(
            r'^(https?\:\/\/)?(www\.)?(soundcloud\.com\/)')
        if sc_url.match(url):
            return True
        return False

    def _match_yt_url(self, url):
        yt_link = re.compile(
            r'^(https?\:\/\/)?(www\.|m\.)?(youtube\.com|youtu\.?be)\/.+$')
        if yt_link.match(url):
            return True
        return False

    # TODO: _next_songs_in_queue

    async def _parse_playlist(self, url):
        if self._match_sc_playlist(url):
            return await self._parse_sc_playlist(url)
        elif self._match_yt_playlist(url):
            return await self._parse_yt_playlist(url)
        raise InvalidPlaylist("The given URL is neither a Soundcloud or"
                              " YouTube playlist.")

    async def _parse_sc_playlist(self, url):
        playlist = []
        d = Downloader(url)
        d.start()

        while d.is_alive():
            await asyncio.sleep(0.5)

        for entry in d.song.entries:
            if entry["url"][4] != "s":
                song_url = "https{}".format(entry["url"][4:])
                playlist.append(song_url)
            else:
                playlist.append(entry.url)

        return playlist

    async def _parse_yt_playlist(self, url):
        d = Downloader(url)
        d.start()
        playlist = []

        while d.is_alive():
            await asyncio.sleep(0.5)

        for entry in d.song.entries:
            try:
                song_url = "https://www.youtube.com/watch?v={}".format(
                    entry['id'])
                playlist.append(song_url)
            except AttributeError:
                pass
            except TypeError:
                pass

        log.debug("song list:\n\t{}".format(playlist))

        return playlist

    async def _play(self, sid, url):
        """Returns the song object of what's playing"""
        if type(sid) is not discord.Server:
            server = self.bot.get_server(sid)
        else:
            server = sid

        assert type(server) is discord.Server
        log.debug('starting to play on "{}"'.format(server.name))

        if self._valid_playable_url(url) or "[SEARCH:]" in url:
            try:
                song = await self._guarantee_downloaded(server, url)
            except MaximumLength:
                log.warning("I can't play URL below because it is too long."
                            " Use {}audioset maxlength to change this.\n\n"
                            "{}".format(self.bot.command_prefix[0], url))
                raise
            local = False
        else:  # Assume local
            try:
                song = self._make_local_song(url)
                local = True
            except FileNotFoundError:
                raise

        voice_client = await self._create_ffmpeg_player(server, song.id,
                                                        local=local)
        # That ^ creates the audio_player property

        voice_client.audio_player.start()
        log.debug("starting player on sid {}".format(server.id))

        return song

    def _play_playlist(self, server, playlist):
        try:
            songlist = playlist.playlist
            name = playlist.name
        except AttributeError:
            songlist = playlist
            name = True

        log.debug("setting up playlist {} on sid {}".format(name, server.id))

        self._stop_player(server)
        self._stop_downloader(server)
        self._clear_queue(server)

        log.debug("finished resetting state on sid {}".format(server.id))

        self._setup_queue(server)
        self._set_queue_playlist(server, name)
        self._set_queue_repeat(server, True)
        self._set_queue(server, songlist)

    def _play_local_playlist(self, server, name):
        songlist = self._local_playlist_songlist(name)

        ret = []
        for song in songlist:
            ret.append(os.path.join(name, song))

        ret_playlist = Playlist(server=server, name=name, playlist=ret)
        self._play_playlist(server, ret_playlist)

    def _player_count(self):
        count = 0
        queue = copy.deepcopy(self.queue)
        for sid in queue:
            server = self.bot.get_server(sid)
            try:
                vc = self.voice_client(server)
                if vc.audio_player.is_playing():
                    count += 1
            except:
                pass
        return count

    def _playlist_exists(self, server, name):
        return self._playlist_exists_local(server, name) or \
            self._playlist_exists_global(name)

    def _playlist_exists_global(self, name):
        f = "data/audio/playlists"
        f = os.path.join(f, name + ".txt")
        log.debug('checking for {}'.format(f))

        return fileIO(f, 'check')

    def _playlist_exists_local(self, server, name):
        try:
            server = server.id
        except AttributeError:
            pass

        f = "data/audio/playlists"
        f = os.path.join(f, server, name + ".txt")
        log.debug('checking for {}'.format(f))

        return fileIO(f, 'check')

    def _remove_queue(self, server):
        if server.id in self.queue:
            del self.queue[server.id]

    def _save_playlist(self, server, name, playlist):
        sid = server.id
        try:
            f = playlist.filename
            playlist = playlist.to_json()
            log.debug("got playlist object")
        except AttributeError:
            f = os.path.join("data/audio/playlists", sid, name + ".txt")

        head, _ = os.path.split(f)
        if not os.path.exists(head):
            os.makedirs(head)

        log.debug("saving playlist '{}' to {}:\n\t{}".format(name, f,
                                                             playlist))
        fileIO(f, 'save', playlist)

    def _shuffle_queue(self, server):
        shuffle(self.queue[server.id]["QUEUE"])

    def _shuffle_temp_queue(self, server):
        shuffle(self.queue[server.id]["TEMP_QUEUE"])

    def _server_count(self):
        return max([1, len(self.bot.servers)])

    def _set_queue(self, server, songlist):
        if server.id in self.queue:
            self._clear_queue(server)
        else:
            self._setup_queue(server)
        self.queue[server.id]["QUEUE"].extend(songlist)

    def _set_queue_channel(self, server, channel):
        if server.id not in self.queue:
            return

        try:
            channel = channel.id
        except AttributeError:
            pass

        self.queue[server.id]["VOICE_CHANNEL_ID"] = channel

    def _set_queue_nowplaying(self, server, song):
        if server.id not in self.queue:
            return

        self.queue[server.id]["NOW_PLAYING"] = song

    def _set_queue_playlist(self, server, name=True):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id]["PLAYLIST"] = name

    def _set_queue_repeat(self, server, value):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id]["REPEAT"] = value

    def _setup_queue(self, server):
        self.queue[server.id] = {"REPEAT": False, "PLAYLIST": False,
                                 "VOICE_CHANNEL_ID": None,
                                 "QUEUE": deque(), "TEMP_QUEUE": deque(),
                                 "NOW_PLAYING": None}

    def _stop(self, server):
        self._setup_queue(server)
        self._stop_player(server)
        self._stop_downloader(server)

    async def _stop_and_disconnect(self, server):
        self._stop(server)
        await self._disconnect_voice_client(server)

    def _stop_downloader(self, server):
        if server.id not in self.downloaders:
            return

        del self.downloaders[server.id]

    def _stop_player(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        if hasattr(voice_client, 'audio_player'):
            voice_client.audio_player.stop()
            del voice_client.audio_player

    def _valid_playlist_name(self, name):
        for l in name:
            if l.isdigit() or l.isalpha() or l == "_":
                pass
            else:
                return False
        return True

    def _valid_playable_url(self, url):
        yt = self._match_yt_url(url)
        sc = self._match_sc_url(url)
        if yt or sc:  # TODO: Add sc check
            return True
        return False

    @commands.command(pass_context=True, no_pm=True, hidden=True)
    async def play(self, ctx, *, url_or_search_terms):
        url = url_or_search_terms
        server = ctx.message.server
        author = ctx.message.author
        voice_channel = author.voice_channel

        # Checking if playing in current server

        if self.is_playing(server):
            await ctx.invoke(self._queue, url=url)
            return  # Default to queue

        # Checking already connected, will join if not

        if not self.voice_connected(server):
            try:
                self.has_connect_perm(author, server)
            except AuthorNotConnected:
                await self.bot.say("You must join a voice channel before I can"
                                   " play anything.")
                return
            except UnauthorizedConnect:
                await self.bot.say("I don't have permissions to join your"
                                   " voice channel.")
                return
            except UnauthorizedSpeak:
                await self.bot.say("I don't have permissions to speak in your"
                                   " voice channel.")
                return
            else:
                await self._join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                await self._stop_and_disconnect(server)
                await self._join_voice_channel(voice_channel)

        # If not playing, spawn a downloader if it doesn't exist and begin
        #   downloading the next song

        if self.currently_downloading(server):
            await self.bot.say("I'm already downloading a file!")
            return

        if "." in url:
            if not self._valid_playable_url(url):
                await self.bot.say("That's not a valid URL.")
                return
        else:
            url = "[SEARCH:]" + url

        if "[SEARCH:]" not in url and "youtube" in url:
            url = url.split("&")[0] # Temp fix for the &list issue

        self._stop_player(server)
        self._clear_queue(server)
        self._add_to_queue(server, url)


    @commands.command(pass_context=True, no_pm=True, hidden=True)
    async def horn(self,ctx):
        urla = "https://www.youtube.com/watch?v=a_6CZ2JaEuc"
        await ctx.invoke(self.play,url_or_search_terms=urla)


    def is_playing(self, server):
        if not self.voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), 'audio_player'):
            return False
        if self.voice_client(server).audio_player.is_done():
            return False
        return True

    async def cache_manager(self):
        while self == self.bot.get_cog("Audio"):
            if self._cache_too_large():
                # Our cache is too big, dumping
                log.debug("cache too large ({} > {}), dumping".format(
                    self._cache_size(), self._cache_max()))
                self._dump_cache()
            await asyncio.sleep(5)  # No need to run this every half second

    async def cache_scheduler(self):
        await asyncio.sleep(30)  # Extra careful

        self.bot.loop.create_task(self.cache_manager())

    def currently_downloading(self, server):
        if server.id in self.downloaders:
            if self.downloaders[server.id].is_alive():
                return True
        return False

    async def disconnect_timer(self):
        stop_times = {}
        while self == self.bot.get_cog('Audio'):
            for vc in self.bot.voice_clients:
                server = vc.server
                if not hasattr(vc, 'audio_player') and \
                        (server not in stop_times or
                         stop_times[server] is None):
                    log.debug("putting sid {} in stop loop, no player".format(
                        server.id))
                    stop_times[server] = int(time.time())

                if hasattr(vc, 'audio_player'):
                    if vc.audio_player.is_done() and \
                            (server not in stop_times or
                             stop_times[server] is None):
                        log.debug("putting sid {} in stop loop".format(
                            server.id))
                        stop_times[server] = int(time.time())
                    elif vc.audio_player.is_playing():
                        stop_times[server] = None

            for server in stop_times:
                if stop_times[server] and \
                        int(time.time()) - stop_times[server] > 300:
                    # 5 min not playing to d/c
                    log.debug("dcing from sid {} after 300s".format(server.id))
                    await self._disconnect_voice_client(server)
                    stop_times[server] = None
            await asyncio.sleep(5)

    def get_server_settings(self, server):
        try:
            sid = server.id
        except:
            sid = server

        if sid not in self.settings["SERVERS"]:
            self.settings["SERVERS"][sid] = {}
        ret = self.settings["SERVERS"][sid]

        for setting in self.server_specific_setting_keys:
            if setting not in ret:
                # Add the default
                ret[setting] = self.settings[setting]
                if setting.lower() == "volume" and ret[setting] <= 1:
                    ret[setting] *= 100
        # ^This will make it so that only users with an outdated config will
        # have their volume set * 100. In theory.
        self.save_settings()

        return ret

    def has_connect_perm(self, author, server):
        channel = author.voice_channel
        if channel is None:
            raise AuthorNotConnected
        elif channel.permissions_for(server.me).connect is False:
            raise UnauthorizedConnect
        elif channel.permissions_for(server.me).speak is False:
            raise UnauthorizedSpeak
        else:
            return True
        return False

    async def queue_manager(self, sid):
        """This function assumes that there's something in the queue for us to
            play"""
        server = self.bot.get_server(sid)
        max_length = self.settings["MAX_LENGTH"]

        # This is a reference, or should be at least
        temp_queue = self.queue[server.id]["TEMP_QUEUE"]
        queue = self.queue[server.id]["QUEUE"]
        repeat = self.queue[server.id]["REPEAT"]
        last_song = self.queue[server.id]["NOW_PLAYING"]

        assert temp_queue is self.queue[server.id]["TEMP_QUEUE"]
        assert queue is self.queue[server.id]["QUEUE"]

        # _play handles creating the voice_client and player for us

        if not self.is_playing(server):
            log.debug("not playing anything on sid {}".format(server.id) +
                      ", attempting to start a new song.")
            if len(temp_queue) > 0:
                # Fake queue for irdumb's temp playlist songs
                log.debug("calling _play because temp_queue is non-empty")
                try:
                    song = await self._play(sid, temp_queue.popleft())
                except MaximumLength:
                    return
            elif len(queue) > 0:  # We're in the normal queue
                url = queue.popleft()
                log.debug("calling _play on the normal queue")
                try:
                    song = await self._play(sid, url)
                except MaximumLength:
                    return
                if repeat and last_song:
                    queue.append(last_song.webpage_url)
            else:
                song = None
            self.queue[server.id]["NOW_PLAYING"] = song
            log.debug("set now_playing for sid {}".format(server.id))
        elif server.id in self.downloaders:
            # We're playing but we might be able to download a new song
            curr_dl = self.downloaders.get(server.id)
            if len(temp_queue) > 0:
                next_dl = Downloader(temp_queue.peekleft(),
                                     max_length)
            elif len(queue) > 0:
                next_dl = Downloader(queue.peekleft(), max_length)
            else:
                next_dl = None

            if next_dl is not None:
                # Download next song
                next_dl.start()
                await self._download_next(server, curr_dl, next_dl)

    async def queue_scheduler(self):
        while self == self.bot.get_cog('Audio'):
            tasks = []
            queue = copy.deepcopy(self.queue)
            for sid in queue:
                if len(queue[sid]["QUEUE"]) == 0 and \
                        len(queue[sid]["TEMP_QUEUE"]) == 0:
                    continue
                # log.debug("scheduler found a non-empty queue"
                #           " for sid: {}".format(sid))
                tasks.append(
                    self.bot.loop.create_task(self.queue_manager(sid)))
            completed = [t.done() for t in tasks]
            while not all(completed):
                completed = [t.done() for t in tasks]
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)

    async def reload_monitor(self):
        while self == self.bot.get_cog('Audio'):
            await asyncio.sleep(0.5)

        for vc in self.bot.voice_clients:
            try:
                vc.audio_player.stop()
            except:
                pass

    def save_settings(self):
        fileIO('data/audio/settings.json', 'save', self.settings)

    def set_server_setting(self, server, key, value):
        if server.id not in self.settings["SERVERS"]:
            self.settings["SERVERS"][server.id] = {}
        self.settings["SERVERS"][server.id][key] = value

    def voice_client(self, server):
        return self.bot.voice_client_in(server)

    def voice_connected(self, server):
        if self.bot.is_voice_connected(server):
            return True
        return False

    async def voice_state_update(self, before, after):
        # Member objects
        if after is None:
            return
        server = after.server
        if server.id not in self.queue:
            return
        if after != server.me:
            return

        # Member is the bot

        if before.voice_channel != after.voice_channel:
            self._set_queue_channel(after.server, after.voice_channel)

        if before.mute != after.mute:
            vc = self.voice_client(server)
            if after.mute and vc.audio_player.is_playing():
                log.debug("Just got muted, pausing")
                vc.audio_player.pause()
            elif not after.mute and \
                    (not vc.audio_player.is_playing() and
                     not vc.audio_player.is_done()):
                log.debug("just got unmuted, resuming")
                vc.audio_player.resume()


def check_folders():
    folders = ("data/audio", "data/audio/cache", "data/audio/playlists",
               "data/audio/localtracks", "data/audio/sfx")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    default = {"VOLUME": 50, "MAX_LENGTH": 3700, "QUEUE_MODE": True,
               "MAX_CACHE": 0, "SOUNDCLOUD_CLIENT_ID": None,
               "TITLE_STATUS": True, "AVCONV": False, "VOTE_THRESHOLD": 50,
               "SERVERS": {}}
    settings_path = "data/audio/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default audio settings.json...")
        fileIO(settings_path, "save", default)
    else:  # consistency check
        current = fileIO(settings_path, "load")
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print(
                        "Adding " + str(key) + " field to audio settings.json")
            fileIO(settings_path, "save", current)


def setup(bot):
    check_folders()
    check_files()
    if youtube_dl is None:
        raise RuntimeError("You need to run `pip3 install youtube_dl`")
    if opus is False:
        raise RuntimeError(
            "Your opus library's bitness must match your python installation's"
            " bitness. They both must be either 32bit or 64bit.")
    elif opus is None:
        raise RuntimeError(
            "You need to install ffmpeg and opus. See \"https://github.com/"
            "Twentysix26/Red-DiscordBot/wiki/Requirements\"")
    try:
        bot.voice_clients
    except AttributeError:
        raise RuntimeError(
            "Your discord.py is outdated. Update to the newest one with\npip3 "
            "install --upgrade git+https://github.com/Rapptz/discord.py@async")
    n = Audio(bot)  # Praise 26
    bot.add_cog(n)
    bot.add_listener(n.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(n.queue_scheduler())
    bot.loop.create_task(n.disconnect_timer())
    bot.loop.create_task(n.reload_monitor())
    bot.loop.create_task(n.cache_scheduler())
