import tekore


class SpotifyRemote:
    def __init__(self, client_id, client_secret, username):
        self.spotify = self.setup_spotify(client_id, client_secret)
        self.spotify_client = self.setup_spotify_client(
            client_id, client_secret, username
        )

    def setup_spotify(self, client_id, client_secret):
        cred = tekore.RefreshingCredentials(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:/callback",
        )
        token = cred.request_client_token()
        return tekore.Spotify(token=token)

    def setup_spotify_client(self, client_id, client_secret, username):
        scope = "user-modify-playback-state user-read-playback-state"
        token = tekore.prompt_for_user_token(
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:/callback",
        )
        return tekore.Spotify(token=token)

    def search_track(self, search_string):
        results = {}
        for track in self.spotify.search(search_string)[0].items:
            results[self.get_title_from_track(track)] = track.uri
        return results

    def get_title_from_track(self, track):
        artists = ", ".join([artist.name for artist in track.artists])
        return f"{artists} - {track.name}"

    def get_track_preview(self, uri):
        id = tekore.from_uri(uri)[1]
        return self.spotify.track(id).preview_url

    def play_pause(self):
        try:
            self.spotify_client.playback_pause()
        except tekore.Forbidden:  # playback already paused
            self.spotify_client.playback_resume()

    def skip(self):
        self.spotify_client.playback_next()

    def now_playing(self):
        return self.get_title_from_track(
            self.spotify_client.playback_currently_playing().item
        )

    def next_song(self):
        pass  # TODO

    def add_to_queue(self, uri):
        self.spotify_client.playback_queue_add(uri)
