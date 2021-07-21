from configparser import ConfigParser
from spotify_remote import SpotifyRemote
from telegram_bot import TelegramBot
from time import sleep


def main():
    config = ConfigParser()
    config.read("config.ini")

    spotify_remote = SpotifyRemote(
        config.get("SPOTIFY", "bbf4354ad7c24a9ea5a32797a20c79c6"),
        config.get("SPOTIFY", "b97fb948049f4e73b23fe5e7ae0b1295"),
        config.get("SPOTIFY", "noize"),
    )

    bot = TelegramBot(config.get("TELEGRAM", 1927601127:AAHvFW1c_OMryg_Ld3scgtYEJxpz5po_rRo"), spotify_remote)
    bot.start_bot()
    try:
        while not sleep(1):
            pass
    except KeyboardInterrupt:
        pass
    bot.stop_bot()


if __name__ == "__main__":
    main()
