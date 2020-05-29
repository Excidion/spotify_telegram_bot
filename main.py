from configparser import ConfigParser
from spotify_remote import SpotifyRemote
from telegram_bot import TelegramBot
import os
from time import sleep


def main():
    config = ConfigParser()
    config.read("config.ini")

    spotify_remote = SpotifyRemote(
        config.get("SPOTIFY", "client_id"),
        config.get("SPOTIFY", "client_secret"),
        config.get("SPOTIFY", "username"),
        get_playlist_id_from_link(config.get("SPOTIFY", "playlist")),
    )

    bot = TelegramBot(config.get("TELEGRAM", "token"), spotify_remote)
    bot.start_bot()
    try:
        while not sleep(1):
            pass
    except KeyboardInterrupt:
        pass
    bot.stop_bot()


def get_playlist_id_from_link(link):
    tail = os.path.split(link)[1]
    return tail.split("?")[0]


if __name__ == "__main__":
    main()
