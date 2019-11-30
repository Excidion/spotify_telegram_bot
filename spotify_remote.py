import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2


class SpotifyRemote():
    def __init__(self, client_id, client_secret, username):
        auth = oauth2.SpotifyClientCredentials(
            client_id = client_id,
            client_secret = client_secret,
        )

        token = auth.get_access_token()
        self.spotify = spotipy.Spotify(auth=token)

        scope = "user-library-read"
        token = util.prompt_for_user_token(
            username,
            scope,
            client_id = client_id,
            client_secret = client_secret,
            redirect_uri = "http://localhost:/callback",
        )
        self.spotify_user = spotipy.Spotify(auth=token)


    def search_track(self, search_string):
        results = {}
        for track in self.spotify.search(search_string, type="track")["tracks"]["items"]:
            results[self.title_from_track(track)] = track["id"]
        return results

    def title_from_track(self, track):
        artists = ", ".join([artist["name"] for artist in track["artists"]])
        trackname = track["name"]
        return f"{artists} - {trackname}"


    def get_track_preview(self, id):
        return self.spotify.track(id)["preview_url"]



if __name__ == '__main__':
    from configparser import ConfigParser
    config = ConfigParser()
    config.read("config.ini")

    sr = SpotifyRemote(
        config.get("SPOTIFY", "client_id"),
        config.get("SPOTIFY", "client_secret"),
        config.get("SPOTIFY", "username")
    )
