from configparser import ConfigParser
from spotify_remote import SpotifyRemote
from telegram_bot import TelegramBot

config = ConfigParser()
config.read("config.ini")

spotify_remote = SpotifyRemote(
    config.get("SPOTIFY", "client_id"),
    config.get("SPOTIFY", "client_secret"),
    config.get("SPOTIFY", "username")
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
