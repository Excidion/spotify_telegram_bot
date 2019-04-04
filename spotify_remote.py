import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2


class SpotifyRemote():
    def __init__(self, client_id, client_secret):
        auth = oauth2.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        token = auth.get_access_token()
        self.spotify = spotipy.Spotify(auth=token)


    def search_track(self, search_string):
        results = {}
        for track in self.spotify.search(search_string, type="track")["tracks"]["items"]:
            artists = ", ".join([artist["name"] for artist in track["artists"]])
            trackname = track["name"]
            id = track["id"]
            results[f"{artists} - {trackname}"] = id
        return results

    def get_track_preview(self, id):
        return self.spotify.track(id)["preview_url"]
