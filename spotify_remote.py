import spotipy
import spotipy.util as util
import spotipy.auth as auth


class SpotifyRemote():
    def __init__(self, client_id, client_secret, username):
        self.spotify = self.setup_spotify(client_id, client_secret)
        self.spotify_client = self.setup_spotify_client(client_id, client_secret, username)

    def setup_spotify(self, client_id, client_secret):
        cred = auth.Credentials(
            client_id = client_id,
            client_secret = client_secret,
            redirect_uri = "http://localhost:/callback",
        )
        token = cred.request_client_token()
        return spotipy.Spotify(token=token)


    def setup_spotify_client(self, client_id, client_secret, username):
         scope = "user-modify-playback-state"#"user-library-read"
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
            results[self.title_from_track(track)] = track.id
        return results

    def title_from_track(self, track):
        artists = ", ".join([artist.name for artist in track.artists])
        trackname = track.name
        return f"{artists} - {trackname}"


    def get_track_preview(self, id):
        return self.spotify.track(id).preview_url


    def now_playing(self):
        return "nothing" # TODO

    def add_to_queue(self, id):
        pass # TODO



if __name__ == '__main__':
    from configparser import ConfigParser
    config = ConfigParser()
    config.read("config.ini")

    sr = SpotifyRemote(
        config.get("SPOTIFY", "client_id"),
        config.get("SPOTIFY", "client_secret"),
        config.get("SPOTIFY", "username")
    )
