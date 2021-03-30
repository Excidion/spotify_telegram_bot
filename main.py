from configparser import ConfigParser
from spotify_remote import SpotifyRemote
from personal_message_handler import PersonalMessageHandler
from locations_handler import LocationsHandler
from telegram_bot import TelegramBot
from time import sleep
import logging


def main():
    config = ConfigParser()
    config.read("config.ini")

    # Enable logging
    logging.basicConfig(filename='app.log',
                        filemode='w',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    spotify_remote = SpotifyRemote(
        config.get("SPOTIFY", "CLIENT_ID"),
        config.get("SPOTIFY", "CLIENT_SECRET"),
        config.get("SPOTIFY", "USERNAME"),
    )

    personal_message_handler = PersonalMessageHandler()
    locations_handler = LocationsHandler()

    bot = TelegramBot(config.get("TELEGRAM", "TOKEN"),
                      spotify_remote, personal_message_handler, locations_handler)
    bot.start_bot()
    try:
        while not sleep(1):
            pass
    except KeyboardInterrupt:
        pass
    bot.stop_bot()


if __name__ == "__main__":
    main()
