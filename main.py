from configparser import ConfigParser
from spotify_remote import SpotifyRemote
from telegram_bot import TelegramBot

config = ConfigParser()
config.read("config.ini")

spotify_remote = SpotifyRemote(
    config.get("SPOTIFY", "CLIENT_ID"),
    config.get("SPOTIFY", "CLIENT_SECRET")
)

bot = TelegramBot(spotify_remote)
bot.start_bot()

try:
    while True:
        pass
except KeyboardInterrupt:
    bot.stop_bot()
