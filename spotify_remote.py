import tekore


class SpotifyRemote:
    def __init__(self, client_id, client_secret, username):
        self.spotify_client = self.setup_spotify_client(
            client_id, client_secret, username
        )

    def setup_spotify_client(self, client_id, client_secret, username):
        scope = "user-modify-playback-state user-read-playback-state playlist-modify-private playlist-read-private"
        token = tekore.prompt_for_user_token(
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:/callback",
        )
        return tekore.Spotify(token=token)

    def search_track(self, search_string):
        results = {}
        for track in self.spotify_client.search(search_string)[0].items:
            results[self.get_title_from_track(track)] = track.uri
        return results

    def get_title_from_track(self, track):
        artists = ", ".join([artist.name for artist in track.artists])
        return "{} | {}".format(artists, track.name)

    def get_track_preview(self, uri):
        id = tekore.from_uri(uri)[1]
        return self.spotify_client.track(id).preview_url

    def play_pause(self):
        try:
            self.spotify_client.playback_pause()
        except tekore.Forbidden:  # playback already paused
            self.spotify_client.playback_resume()

    def skip(self):
        self.spotify_client.playback_next()

    def now_playing(self):
        if self.spotify_client.playback_currently_playing() == None:
            return "I am currently not listening to music."
        return self.get_title_from_track(
            self.spotify_client.playback_currently_playing().item
        )

    def next_song(self):
        pass  # TODO

    def add_to_queue(self, uri):
        try:
            self.spotify_client.playback_queue_add(uri)
        except tekore.BadRequest or tekore.NotFound:
            return False
        else:
            return True

    def add_url(self, url):
        try:
            type, id = tekore.from_url(url)
            uri = tekore.to_uri(type, id)
        except tekore.ConversionError:
            return False
        else:
            return self.add_to_queue(uri)
