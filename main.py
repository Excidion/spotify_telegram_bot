from configparser import ConfigParser
from spotify_remote import SpotifyRemote
from telegram_bot import TelegramBot
import os


def get_playlist_id_from_link(link):
    tail = os.path.split(link)[1]
    if "?" in tail:
        return tail.split("?")[0]
    else:
        return tail


config = ConfigParser()
config.read("config.ini")

spotify_remote = SpotifyRemote(
    config.get("SPOTIFY", "client_id"),
    config.get("SPOTIFY", "client_secret"),
    config.get("SPOTIFY", "username"),
    get_playlist_id_from_link(config.get("SPOTIFY", "playlist")),
)

bot = TelegramBot(
    config.get("TELEGRAM", "token"),
    spotify_remote,
)
bot.start_bot()
try:
    while True:
        pass
except KeyboardInterrupt: pass
bot.stop_bot()
