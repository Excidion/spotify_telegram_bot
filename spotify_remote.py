import spotipy
import spotipy.util as util
import spotipy.auth as auth
from queue import Queue
from threading import Thread
from time import sleep
import random




class SpotifyRemote:
    def __init__(self, client_id, client_secret, username, fallback_playlist_id):
        self.spotify = self.setup_spotify(client_id, client_secret)
        self.spotify_client = self.setup_spotify_client(client_id, client_secret, username)
        self.queue = SpotifyQueue(
            spotify_client = self.spotify_client,
            fallback_playlist_id = fallback_playlist_id,
        )

    def setup_spotify(self, client_id, client_secret):
        cred = auth.Credentials(
            client_id = client_id,
            client_secret = client_secret,
            redirect_uri = "http://localhost:/callback",
        )
        token = cred.request_client_token()
        return spotipy.Spotify(token=token)

    def setup_spotify_client(self, client_id, client_secret, username):
         scope = "user-modify-playback-state user-read-playback-state"
         token = util.prompt_for_user_token(
             scope = scope,
             client_id = client_id,
             client_secret = client_secret,
             redirect_uri = "http://localhost:/callback",
         )
         return spotipy.client.Spotify(token=token)


    def search_track(self, search_string):
        results = {}
        for track in self.spotify.search(search_string)[0].items:
            results[self.get_title_from_track(track)] = track.id
        return results

    def get_title_from_track(self, track):
        artists = ", ".join([artist.name for artist in track.artists])
        return f"{artists} - {track.name}"

    def get_track_preview(self, id):
        return self.spotify.track(id).preview_url

    def play_pause(self):
        try:
            self.spotify_client.playback_pause()
        except:
            self.spotify_client.playback_resume()

    def skip(self):
        self.queue.play_next_track()

    def now_playing(self):
        return self.get_title_from_track(self.spotify_client.playback().item)

    def next_song(self):
        try:
            id = self.queue.list()[0]
        except IndexError: # empty queue
            return None
        else:
            return self.get_title_from_track(self.spotify.track(id))

    def add_to_queue(self, id):
        return self.queue.put(id)




class SpotifyQueue(Queue):
    def __init__(self, spotify_client, fallback_playlist_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spotify_client = spotify_client
        self.fallback_playlist = self.spotify_client.playlist(fallback_playlist_id)
        self.playback_controller = Thread(target=self.control_playback, args=[])
        self.playback_controller.start()

    def control_playback(self):
        self.play_next_track()
        interval = 2
        while not sleep(interval):
            playback = self.spotify_client.playback()
            if playback is None:
                pass
            elif playback.item.duration_ms - playback.progress_ms <= interval*1000:
                self.play_next_track()

    def play_next_track(self):
        if not self.empty():
            id = self.get()
        else:
            id = random.choice([t.track.id for t in self.fallback_playlist.tracks.items])
        self.spotify_client.playback_start_tracks([id])

    def put(self, item, *args, **kwargs):
        if not item in self.list():
            super().put(item, *args, **kwargs)
            return True
        else:
            return False

    def list(self):
        return list(self.queue)
