from configparser import ConfigParser
from telegram.ext import (
    Updater,
    MessageHandler,
    BaseFilter,
    CommandHandler,
    ConversationHandler,
    Filters,
    CallbackContext,
)
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
import pickle
from spotify_remote import SpotifyRemote
from personal_message_handler import PersonalMessageHandler
from locations_handler import LocationsHandler
import numpy as np
import itertools
import logging
from datetime import datetime, timedelta
import pytz
from helpers import *
import io
from PIL import Image

logger = logging.getLogger(__name__)

config = ConfigParser()
config.read("config.ini")

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f%z"


class AdminFilter(BaseFilter):
    def __init__(self):
        self.admin_username = config.get("TELEGRAM", "ADMIN")

    def __call__(self, update):
        return self.filter(update.message)

    def filter(self, message):
        return message.from_user.username == self.admin_username


class UserFilter(BaseFilter):
    def __init__(self):
        self.password = config.get("TELEGRAM", "PASSWORD").lower()
        self.user_chat_ids = []

    def __call__(self, update):
        return self.filter(update.message)

    def filter(self, message):
        if message.chat_id not in self.user_chat_ids:
            message.reply_text("First use /password and tell me the magic word.")
        return message.chat_id in self.user_chat_ids

    def add_user(self, id):
        self.user_chat_ids.append(id)


class TelegramBot:
    def __init__(
        self, token, spotify_remote, personal_message_handler, locations_handler
    ):
        self.updater = Updater(
            token=token,
            use_context=True,
        )
        self.user_filter = UserFilter()
        dispatcher = self.updater.dispatcher
        self.spotify = spotify_remote
        self.setup_admin_id()
        self.personal_messages = personal_message_handler
        self.locations = locations_handler

        COMMAND_MAP = {
            "start": self.greet,
            "now": self.print_now_playing,
            "next": self.print_next_song,
            "help": self.send_help,
            "rank": self.print_leaderboard,
        }
        for command in COMMAND_MAP:
            dispatcher.add_handler(
                CommandHandler(
                    command,
                    COMMAND_MAP[command],
                )
            )

        ADMIN_COMMAND_MAP = {
            "chat_id": self.print_chat_id,
            "register": self.register,
            "skip": self.skip_track,
            "stop": self.stop_listening,
            "p": self.play_pause,
            "hm": self.provide_unlistened_songs_details,
        }
        # "listen": self.start_listening,
        for command in ADMIN_COMMAND_MAP:
            dispatcher.add_handler(
                CommandHandler(
                    command,
                    ADMIN_COMMAND_MAP[command],
                    filters=AdminFilter(),
                )
            )

        # conversation with admin for starting listening session
        dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        "listen",
                        self.start_listening,
                        filters=AdminFilter(),
                    ),
                ],
                states={
                    0: [
                        MessageHandler(
                            Filters.text, self.react_to_location_sharing_selection
                        )
                    ]
                },
                fallbacks=[CommandHandler("cancel", self.cancel)],
                allow_reentry=True,
            )
        )

        # conversation for adding song to queue
        dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        "song",
                        self.start_song_search,
                        filters=self.user_filter,
                    ),
                ],
                states={
                    0: [MessageHandler(Filters.text, self.show_search_results)],
                    1: [MessageHandler(Filters.text, self.react_to_selection)],
                    2: [MessageHandler(Filters.text, self.react_to_choice)],
                    3: [MessageHandler(Filters.text, self.react_to_message_option)],
                    4: [MessageHandler(Filters.text, self.react_to_message_content)],
                },
                fallbacks=[CommandHandler("cancel", self.cancel)],
                allow_reentry=True,
            )
        )

        #  adding songs to queue by sending link
        dispatcher.add_handler(
            MessageHandler(Filters.entity("url") & self.user_filter, self.add_url)
        )

        # conversation for entering password
        dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        "password",
                        self.ask_for_password,
                    ),
                ],
                states={
                    0: [MessageHandler(Filters.text, self.check_password)],
                },
                fallbacks=[CommandHandler("cancel", self.cancel)],
                allow_reentry=True,
            )
        )
        # log all errors
        dispatcher.add_error_handler(self.error)

        location_handler = MessageHandler(Filters.location, self.location)

        dispatcher.add_handler(location_handler)

        dispatcher.add_handler(MessageHandler(Filters.text, self.default_message))

        self.last_playing = ""
        self.last_playing_progress = 0
        self.listening = False
        self.songs_to_listen = []
        self.current_lat = 0
        self.current_lon = 0
        self.record_location = False
        self.locations_during_song = []
        self.previous_message = ""
        self.activate_locations = False
        self.location_request_time = datetime.now(pytz.utc)
        self.want_to_listen = False
        self.job = ""
        self.last_song_length = 0
        self.pervious_country = ""
        self.is_paused = False

    # setup methods

    def setup_admin_id(self):
        try:
            with open(".admin.p", "rb") as file:
                self.DEFAULT_CONTACT_ID = pickle.load(file)
        except FileNotFoundError:
            logging.error("Exception occurred", exc_info=True)
            self.DEFAULT_CONTACT_ID = None

    def add_new_songs_to_queue(self, unlistened_songs):
        new_songs = list(
            itertools.filterfalse(lambda x: x in self.songs_to_listen, unlistened_songs)
        )
        logger.info("{} new songs will be added to queue.".format(len(new_songs)))
        for song in new_songs:
            self.spotify.add_to_queue(song["uri"])
            logger.info(
                "Song with uri {} sent by {} (chat_id: {}) added to queue.".format(
                    song["uri"], song["first_name"], song["chat_id"]
                )
            )
        self.songs_to_listen = unlistened_songs

    def is_new_song(self, currently_playing_uri, current_progress, is_paused):
        # check if just paused
        if is_paused:
            return False
        return self.last_playing != currently_playing_uri or (
            self.last_playing == currently_playing_uri
            and current_progress < self.last_playing_progress
        )

    def handle_location_tracking(self, chat_id):
        # turn on location data recording through the location() function
        self.record_location = True
        # add the first coordinates. The location() function will trigger on any future location updates
        self.locations_during_song.append(
            {
                "lon": self.current_lon,
                "lat": self.current_lat,
                "time": datetime.now(pytz.utc).__str__(),
            }
        )
        try:
            self.pervious_country, weather_string = get_weather_text(
                config.get("WEATHER", "API_KEY"), self.current_lat, self.current_lon
            )
        except:
            self.message_me(
                "Not able to retrieve weather data for lat:{}, lon:{}.".format(
                    self.current_lat, self.current_lon
                )
            )
            return
        self.send_message(
            weather_string + " Let me send you my exact location: ", chat_id
        )
        self.send_location(self.current_lat, self.current_lon, chat_id)

    def end_session(self):
        if self.activate_locations and self.record_location:
            self.save_locations()
        self.activate_locations = False
        self.record_location = False
        self.songs_to_listen = []
        self.listening = False
        self.want_to_listen = False
        self.is_paused = False
        self.message_me("You are now offline.")

    def check_if_song_change(self, context: CallbackContext):
        currently_playing = self.spotify.spotify_client.playback_currently_playing()
        if currently_playing is None:
            self.last_playing = None
            logger.info("No active device.")
            self.message_me("No Active Device. Please go online on Spotify.")
            if self.listening:
                removal = self.job.schedule_removal()
                if removal is None:
                    logger.info("Job Successfully Removed.")
                    self.end_session()
                else:
                    logger.error(
                        "A problem occurred when attempting to remove the job."
                    )
                    self.message_me(
                        "A problem occurred when attempting to remove the job. Please try again with /stop."
                    )
            else:
                self.message_me("You are already offline.")
        elif currently_playing is not None and currently_playing.item is not None:
            # add any newly added songs to the spotify queue
            currently_playing_uri = currently_playing.item.uri
            self.is_paused = not currently_playing.is_playing
            unlistened_songs = self.personal_messages.get_unlistened_messages()
            self.add_new_songs_to_queue(unlistened_songs)
            # if song change
            if self.is_new_song(
                currently_playing_uri, currently_playing.progress_ms, self.is_paused
            ):
                logger.info(
                    "Song changed from {} to {}.".format(
                        self.last_playing, currently_playing_uri
                    )
                )
                # if location recording is on, then save locations for previous song
                if self.record_location:
                    self.save_locations()

                for song in unlistened_songs:
                    # check if song was sent by someone
                    if currently_playing_uri == song["uri"]:
                        logger.info(
                            "Current song {} matches a sent and unlistened song.".format(
                                currently_playing_uri
                            )
                        )
                        message = self.personal_messages.find_message(
                            currently_playing_uri
                        )
                        self.last_song_length = currently_playing.item.duration_ms
                        if message["chat_id"] is not None:
                            # send the personal_message to my telegram
                            self.message_me(
                                "sent by {}. {}".format(
                                    message["first_name"], message["content"]
                                )
                            )
                            logger.info(
                                "Message from {} with content: {} sent at {}.".format(
                                    message["first_name"],
                                    message["content"],
                                    message["timestamp"],
                                )
                            )
                            # notify sender of song that I just started listening
                            try:
                                song_title = (
                                    self.spotify.get_title_from_track(
                                        currently_playing.item
                                    )
                                    .split("|")[-1]
                                    .strip()
                                )
                                self.send_message(
                                    'Thanks for sending me the song "{}". I just started listening to it.'.format(
                                        song_title
                                    ),
                                    message["chat_id"],
                                )
                            except:
                                self.message_me(
                                    "Not able to send message to chat with chat_id {}. Marking it listened.".format(
                                        message["chat_id"]
                                    )
                                )
                                self.personal_messages.mark_message_listened(message)
                                return
                            # start recording locations if tracking is activated
                            if self.activate_locations:
                                self.handle_location_tracking(message["chat_id"])
                            self.personal_messages.mark_message_listened(message)
                            # add the song to the designated playlist if name is set
                            if config.get("SPOTIFY", "PLAYLIST_NAME") is not None:
                                try:
                                    self.add_to_playlist(
                                        config.get("SPOTIFY", "PLAYLIST_NAME"),
                                        currently_playing_uri,
                                    )
                                except:
                                    self.message_me(
                                        "Not able to add song with uri {} to playlist with name: {}".format(
                                            currently_playing_uri,
                                            config.get("SPOTIFY", "PLAYLIST_NAME"),
                                        )
                                    )
                            self.previous_message = message
                            logger.info(
                                "Thank you message sent and song added to playlist."
                            )
                        break  # exit loop once message found
            self.last_playing = currently_playing_uri
            self.last_playing_progress = currently_playing.progress_ms

    # methods to use from outside
    def start_bot(self):
        self.updater.start_polling()  # start mainloop
        logger.info("Startup successfull. Bot online")
        print("Startup successfull. Spotify-Bot is now online.")

    def stop_bot(self):
        logger.info("Shutdown initiated. Bot going offline.")
        self.message_me("Shutdown initiated.")
        self.force_stop_listening()
        self.updater.stop()

    def message_me(self, text):
        if self.DEFAULT_CONTACT_ID is not None:
            self.send_message(text, self.DEFAULT_CONTACT_ID)
        else:
            logger.info("Please /register your Telegram Account to use this function.")
            print("Please /register your Telegram Account to use this function.")

    def send_message(self, text, id):
        self.updater.bot.send_message(chat_id=id, text=text)

    def send_image(self, image, id):
        byte_image = io.BufferedReader(io.BytesIO(image))
        self.updater.bot.send_photo(chat_id=id, photo=byte_image)

    def send_location(self, lat, lon, id):
        self.updater.bot.send_location(chat_id=id, latitude=lat, longitude=lon)

    # gets triggered on a location message
    # keeps updating self.current_lat and self.current_lon from the live location message
    def location(self, update, context):
        message = None
        if update.edited_message:
            if self.want_to_listen and update.edited_message["date"].strftime(
                DATETIME_FORMAT
            ) < self.location_request_time.strftime(DATETIME_FORMAT):
                print("update", update)
                self.message_me(
                    "It appears you are already sharing a live location. Please turn that off first."
                )
                return
            message = update.edited_message
        else:
            message = update.message
        self.current_lat = message.location.latitude
        self.current_lon = message.location.longitude
        if self.record_location == True and not self.is_paused:
            self.locations_during_song.append(
                {
                    "lon": self.current_lon,
                    "lat": self.current_lat,
                    "time": datetime.now(pytz.utc).__str__(),
                }
            )
        if self.listening == False and self.want_to_listen == True:
            self.start_job()

    def save_locations(self):
        logger.info(
            "Saving locations for personal message with id: {}.".format(
                self.previous_message["id"]
            )
        )
        if len(self.locations_during_song) > 0:

            length_listened_text, duration_listened = prepare_listened_length_message(
                self.locations_during_song, self.last_song_length, DATETIME_FORMAT
            )
            distance_traveled = calculate_distance(self.locations_during_song)
            speed_during_song = round(
                distance_traveled / (duration_listened.seconds / 3600), 2
            )
            self.locations.add(
                self.locations_during_song,
                self.previous_message["id"],
                self.previous_message["chat_id"],
                self.previous_message["username"],
                self.previous_message["first_name"],
                self.previous_message["last_name"],
                distance_traveled,
                speed_during_song,
                duration_listened.seconds,
                self.pervious_country,
            )
            speed_listened_text = prepare_distance_traveled_message(
                distance_traveled,
                speed_during_song,
                float(config.get("GENERAL", "MY_AVERAGE_CYCLING_SPEED")),
            )
            self.send_message(
                "I just finished listening to your song! "
                + length_listened_text
                + "Let me send you a map of the route on which you accompanied me with your song:",
                self.previous_message["chat_id"],
            )
            self.send_image(
                draw_map(self.locations.find_locations(self.previous_message["id"])),
                self.previous_message["chat_id"],
            )
            self.send_message(speed_listened_text, self.previous_message["chat_id"])
        self.locations_during_song = []
        self.record_location = False

    # commands
    def greet(self, update, context):
        update.message.reply_text(
            "\n".join(
                [
                    "Hey there \U0001F64B,",
                    "",
                    "Welcome to the greatest bot on Telegram!",
                    "",
                    "First use /password (<- click here) to verify you are really allowed to use this beast \U0001F510.",
                    "",
                    "Afterwards use /song to send me some music \U0001F3B6 and then watch the magic happen as I listen to it.",
                    "",
                    "The goal is to accompany me over the longest distance with your songs. Only the distance that I ride \U0001F6B4 while listening to your songs is counted.",
                    "",
                    "If we remember our highschool physics then distance = time * speed. So the goal is to send me energizing songs (so I cycle faster: \U00002B06 speed) that I like (so I listen longer: \U00002B06 time).",
                    "",
                    "If you are stuck at any point, use /help.",
                    "",
                    "To see my current top DJs, use /rank.",
                ]
            ),
        )

    def print_now_playing(self, update, context):
        update.message.reply_text(self.spotify.now_playing())

    def print_leaderboard(self, update, context):
        username = update.message.from_user.username
        chat_id = update.message.chat.id
        leadership_string = self.locations.build_leaderboard(chat_id)
        update.message.reply_text(leadership_string)

    def print_next_song(self, update, context):
        next = self.spotify.next_song()
        if next is not None:
            update.message.reply_text(f'Next up is "{next}".')
        else:
            update.message.reply_text(
                "The queue is empty. Why don't you suggest a /song ?"
            )

    def send_help(self, update, context):
        update.message.reply_text(
            "\n".join(
                [
                    "Help incoming....",
                    "",
                    "Use the /password (<- click on it) command and enter the password when prompted.",
                    "",
                    "Next use the /song (<- click on it) command and follow the instructions to send me a song.",
                    "",
                    "Use /rank (<- click on it) to see how you measure against the other great DJs out there.",
                    "",
                    "If you want step by step instructions on how to use the bot, then click on the following link: https://youtu.be/d8HdV3U9Rs8.",
                ]
            ),
        )

    def remove_job_if_exists(self, name):
        # Remove job with given name. Returns whether job was removed.
        current_jobs = self.updater.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True

    # admin commands
    def force_stop_listening(self):
        if self.listening:
            job_removed = self.remove_job_if_exists("my_job")
            if job_removed:
                logger.info("Job Successfully Removed.")
                self.end_session()
            else:
                logger.error("A problem occurred when attempting to remove the job.")
                self.message_me("A problem occurred when attempting to remove the job.")
        else:
            self.message_me("You are already offline.")

    def stop_listening(self, update, context):
        self.force_stop_listening()

    def add_to_playlist(self, playlist_name, item):
        playlist_id = None
        for playlist in self.spotify.spotify_client.playlists(
            config.get("SPOTIFY", "USERNAME")
        ).items:
            if playlist.name == playlist_name:
                playlist_id = playlist.id
                break
        if playlist_id is None:
            new_playlist = self.spotify.spotify_client.playlist_create(
                config.get("SPOTIFY", "USERNAME"),
                playlist_name,
                public=False,
                description="this playlist contains all the songs sent to me, which I already listened to",
            )
            playlist_id = new_playlist.id
        self.spotify.spotify_client.playlist_add(playlist_id, [item])

    def print_chat_id(self, update, context):
        update.message.reply_text(update.message.chat_id)

    def register(self, update, context):
        id = update.message.chat_id
        with open(".admin.p", "wb") as file:
            pickle.dump(id, file)
        self.DEFAULT_CONTACT_ID = id
        self.message_me("Registration successfull.")

    def skip_track(self, update, context):
        update.message.reply_text("I will skip this one.")
        self.spotify.skip()
        update.message.reply_text(f'Next one is "{self.spotify.now_playing()}".')

    def play_pause(self, update, context):
        self.spotify.play_pause()

    def provide_unlistened_songs_details(self, update, context):
        unlistened_songs_info = ""
        unlistened_songs = self.personal_messages.get_unlistened_messages()
        unlistened_songs_info += (
            "You have {} songs waiting to be listened to.\n".format(
                len(unlistened_songs)
            )
        )
        count = 1
        for song in unlistened_songs:
            unlistened_songs_info += "\nSong {} sent by {} at {}".format(
                count, song["first_name"], song["timestamp"]
            )
            count += 1
        self.message_me(unlistened_songs_info)

    # session setup
    def start_listening(self, update, context):
        currently_playing = self.spotify.spotify_client.playback_currently_playing()
        if currently_playing is None:
            logger.info("No active device on start-up.")
            self.message_me(
                "No Active Device. Please go online on Spotify and then type /listen again."
            )
            return
        if self.listening:
            self.message_me("You are already online.")
            return
        self.want_to_listen = True
        reply_keyboard = ReplyKeyboardMarkup(
            [["No."], ["Yes."]],  # [{"text": "Yes.", "request_location": True}]
            one_time_keyboard=True,
        )
        update.message.reply_text(
            "Enable location tracking features?",
            reply_markup=reply_keyboard,
        )
        return 0

    def start_job(self):
        if self.listening:
            self.message_me("You are already online. Use /stop to stop listening")
            return
        self.job = self.updater.job_queue.run_repeating(
            self.check_if_song_change, interval=1, first=0, name="my_job"
        )
        logger.info("Job started.")
        self.listening = True
        self.message_me(
            "You are now online. A total of {} songs are waiting for you.".format(
                len(self.personal_messages.get_unlistened_messages())
            )
        )

    def react_to_location_sharing_selection(self, update, context):
        response = update.message.text
        if response == "No.":
            update.message.reply_text(
                "Setup complete without location tracking feature.",
                reply_markup=ReplyKeyboardRemove(),
            )
            self.start_job()

        if response == "Yes.":
            update.message.reply_text(
                "Setup complete with location tracking feature. Please now share your live location for 8 hours!",
                reply_markup=ReplyKeyboardRemove(),
            )
            self.activate_locations = True
            # since telegram timestamps are in utc time
            self.location_request_time = datetime.now(pytz.utc)
        return ConversationHandler.END

    # song search
    def start_song_search(self, update, context):
        update.message.reply_text("What's the song called? Type the name now.")
        return 0

    def show_search_results(self, update, context):
        user_data = context.user_data
        if "song_search_results" not in user_data:
            user_data["song_search_results"] = self.spotify.search_track(
                update.message.text
            )
        options = [["Try another search.", "Stop searching."]]
        options += [[x] for x in user_data["song_search_results"].keys()]
        update.message.reply_text(
            text="These are the songs I found. Can you see the right one?",
            reply_markup=ReplyKeyboardMarkup(options, one_time_keyboard=True),
        )
        return 1

    def react_to_selection(self, update, context):
        response = update.message.text
        if response == "Try another search.":
            update.message.reply_text(
                "Okay, how is it called?",
                reply_markup=ReplyKeyboardRemove(),
            )
            del context.user_data["song_search_results"]
            return 0

        elif response == "Stop searching.":
            update.message.reply_text(
                "Sorry that I couldn't help you.",
                reply_markup=ReplyKeyboardRemove(),
            )
            del context.user_data["song_search_results"]
            return ConversationHandler.END

        elif response in context.user_data["song_search_results"]:
            id = context.user_data["song_search_results"][response]
            context.user_data["selection_id"] = id
            preview_url = self.spotify.get_track_preview(id)
            reply_keyboard = ReplyKeyboardMarkup(
                [
                    ["Yes, that's the song!"],
                    ["No, show me the other ones again."],
                ],
                one_time_keyboard=True,
            )
            if preview_url is None:
                update.message.reply_text(
                    "Are you sure you want to add the song to my Spotify Queue?",
                    reply_markup=reply_keyboard,
                )
            else:
                update.message.reply_text("Does this sound right?")
                update.message.reply_audio(
                    self.spotify.get_track_preview(id),
                    reply_markup=reply_keyboard,
                )
            return 2

    def react_to_choice(self, update, context):
        response = update.message.text
        if response == "Yes, that's the song!":
            reply_keyboard = ReplyKeyboardMarkup(
                [
                    ["Yes, I want to add a message!"],
                    ["No, I don't want to add a message."],
                ],
                one_time_keyboard=True,
            )
            update.message.reply_text(
                "Do you want to add a message? \U0001F4DD \n(This message will be played to me at the start of your song.)",
                reply_markup=reply_keyboard,
            )
            del context.user_data["song_search_results"]
            return 3
        elif response == "No, show me the other ones again.":
            options = [["Try another search.", "Stop searching."]]
            options += [[x] for x in context.user_data["song_search_results"].keys()]
            update.message.reply_text(
                text="Here is the list again. Can you see the right one now?",
                reply_markup=ReplyKeyboardMarkup(options, one_time_keyboard=True),
            )
            return 1

    def react_to_message_option(self, update, context):
        response = update.message.text
        if response == "Yes, I want to add a message!":
            update.message.reply_text("Type the message now.")
            return 4
        elif response == "No, I don't want to add a message.":
            self.personal_messages.add(
                "",
                context.user_data["selection_id"],
                update.message.from_user.first_name,
                update.message.from_user.last_name,
                update.message.from_user.username,
                update.message.chat.id,
            )
            response = "Song added."
            update.message.reply_text(response, reply_markup=ReplyKeyboardRemove())
            new_song_dict = self.personal_messages.get_last_added_message()
            new_song_added_by = new_song_dict["first_name"]
            self.message_me(f"A new song from {new_song_added_by} was added.")
            return ConversationHandler.END

    def react_to_message_content(self, update, context):
        message_content = update.message.text
        self.personal_messages.add(
            message_content,
            context.user_data["selection_id"],
            update.message.from_user.first_name,
            update.message.from_user.last_name,
            update.message.from_user.username,
            update.message.chat.id,
        )

        response = "Song and message added."
        update.message.reply_text(response, reply_markup=ReplyKeyboardRemove())
        new_song_dict = self.personal_messages.get_last_added_message()
        new_song_added_by = new_song_dict["first_name"]
        self.message_me(f"A new song from {new_song_added_by} was added.")
        return ConversationHandler.END

    # add song via url
    def add_url(self, update, context):
        url = update.message.text
        url = url.split("?")[0]  # remove everything after "?"
        success = self.spotify.add_url(url)
        if success:
            update.message.reply_text("Added it to the queue!")
        else:
            update.message.reply_text("Please send a valid link to a Spotify song.")

    # password check
    def ask_for_password(self, update, context):
        update.message.reply_text(
            config.get("TELEGRAM", "PASSWORD_QUESTION")
            + "\nHint: "
            + config.get("TELEGRAM", "PASSWORD_HINT")
        )
        return 0

    def check_password(self, update, context):
        if update.message.text.lower() == self.user_filter.password:
            self.user_filter.add_user(update.message.chat_id)
            update.message.reply_text("That's correct. \U0001F513")
            update.message.reply_text("Use /song to send me a song.")
            return ConversationHandler.END
        else:
            update.message.reply_text(
                "Nah, nah, nah. You didn't say the magic word. \U0001F512"
            )
            return 0

    # general conversation commands
    def cancel(self, update, context):
        update.message.reply_text(
            "Action canceled.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    def default_message(self, update, context):
        update.message.reply_text(
            "Sorry I am stupid and can only respond to a given set of commands \U0001F643. Use /start if you are new here, else use /help to see the list of commands that I understand."
        )

    # logging
    def error(self, update, context):
        # Log Errors caused by Updates.
        logger.error('Update "%s" caused error "%s"', update, context.error)
        self.send_message(
            "Error in {}'s Bot. Check logs please. {} {}".format(
                config.get("TELEGRAM", "ADMIN"), datetime.now().__str__(), context.error
            ),
            self.DEFAULT_CONTACT_ID,
        )  # hardcoded to mine
        self.updater.bot.send_document(
            chat_id=self.DEFAULT_CONTACT_ID, document=open("app.log", "rb")
        )
