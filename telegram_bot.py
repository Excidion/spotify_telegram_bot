from configparser import ConfigParser
from telegram.ext import Updater, MessageHandler, BaseFilter, CommandHandler, ConversationHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import pickle
from spotify_remote import SpotifyRemote

config = ConfigParser()
config.read("config.ini")

class AdminFilter(BaseFilter):
    def filter(self, message):
        return message.from_user.username == config.get("TELEGRAM", "ADMIN")

class GeneralFilter(BaseFilter):
    def filter(self, message):
        user = message.from_user
        print(f"{user.first_name or ''} {user.last_name or ''} ({user.username or ''}): {message.text}")
        return True


class TelegramBot():
    def __init__(self, token, spotify_remote):
        self.updater = Updater(
            token = token,
            use_context = True,
        )
        dispatcher = self.updater.dispatcher
        self.spotify = spotify_remote
        self.setup_admin_id()

        COMMAND_MAP = {
            "start": self.greet,
            "now": self.print_now_playing
        }
        for command in COMMAND_MAP:
            dispatcher.add_handler(
                CommandHandler(
                    command,
                    COMMAND_MAP[command],
                    filters = GeneralFilter(),
                )
            )

        ADMIN_COMMAND_MAP = {
            "chat_id": self.print_chat_id,
            "register": self.register,
        }
        for command in ADMIN_COMMAND_MAP:
            dispatcher.add_handler(
                CommandHandler(
                    command,
                    ADMIN_COMMAND_MAP[command],
                    filters = AdminFilter() & GeneralFilter(),
                )
            )

        dispatcher.add_handler(ConversationHandler(
            entry_points = [CommandHandler("song", self.start_song_search,filters = GeneralFilter())],
            states = {
                0: [MessageHandler(Filters.text & GeneralFilter(), self.show_search_results)],
                1: [MessageHandler(Filters.text & GeneralFilter(), self.react_to_selection)],
                2: [MessageHandler(Filters.text & GeneralFilter(), self.react_to_choice)],
            },
            fallbacks = [CommandHandler("cancel", self.cancel)],
            allow_reentry = True,
        ))


    # setup methods
    def setup_admin_id(self):
        try:
            with open(".admin.p", "rb") as file:
                self.DEFAULT_CONTACT_ID = pickle.load(file)
        except FileNotFoundError:
            self.DEFAULT_CONTACT_ID = None


    # methods to use from outside
    def start_bot(self):
        self.updater.start_polling() # start mainloop
        self.message_me("Startup successfull. Spotify-Bot is now online.")

    def stop_bot(self):
        print("\nShutdown initiated.")
        self.updater.stop()


    def update_me(self, update, context):
        if update.message.chat_id == self.DEFAULT_CONTACT_ID:
            return # don't inform me about my own actions
        user = update.message.from_user
        msg = ""
        msg += f"{user.first_name or ''} {user.last_name or ''}"
        msg += f" ({user.username or ''})"
        msg += f"has added \"{update.message.text}\" to the playlist."
        self.message_me(msg)

    def message_me(self, text):
        if not self.DEFAULT_CONTACT_ID == None:
            self.send_message(text, self.DEFAULT_CONTACT_ID)
        else:
            print("Please /register your Telegram Account to use this function.")

    def send_message(self, text, id):
        self.updater.bot.send_message(chat_id=id, text=text)


    # commands
    def greet(self, update, context):
        update.message.reply_text("Hello, and welcome to the party!\nUse /song if you have a wish.")

    def print_now_playing(self, update, context):
        update.message.reply_text(self.spotify.now_playing())


    # admin commands
    def print_chat_id(self, update, context):
        update.message.reply_text(update.message.chat_id)

    def register(self, update, context):
        id = update.message.chat_id
        with open(".admin.p", "wb") as file:
            pickle.dump(id, file)
        self.DEFAULT_CONTACT_ID = id
        self.message_me("Registration successfull.")


    # advanced commands
    def start_song_search(self, update, context):
        update.message.reply_text("What do you want to listen to?")
        return 0

    def show_search_results(self, update, context):
        user_data = context.user_data
        if not "song_search_results" in user_data:
            user_data["song_search_results"] = self.spotify.search_track(update.message.text)
        options = [["Try another search.", "Stop searching."]]
        options += [[x] for x in user_data["song_search_results"].keys()]
        update.message.reply_text(
            text = "These are the songs I found. Can you see the right one?",
            reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True),
        )
        return 1

    def react_to_selection(self, update, context):
        response = update.message.text
        if response == "Try another search.":
            update.message.reply_text(
                "Okay, how is it called?",
                reply_markup = ReplyKeyboardRemove(),
            )
            del user_data["song_search_results"]
            return 0
        elif response == "Stop searching.":
            update.message.reply_text(
                "Sorry that i couldn't help you.",
                reply_markup = ReplyKeyboardRemove(),
            )
            del user_data["song_search_results"]
            return ConversationHandler.END
        elif response in context.user_data["song_search_results"]:
            id = context.user_data["song_search_results"][response]
            update.message.reply_text("Does this sound right?")
            update.message.reply_audio(
                self.spotify.get_track_preview(id),
                reply_markup = ReplyKeyboardMarkup(
                    [["Yes, that's the song!"], ["No, show me the other ones again."]],
                    one_time_keyboard = True,
                )
            )
            return 2
        else:
            return ConversationHandler.END


    def react_to_choice(self, update, context):
        response = update.message.text
        if response == "Yes, that's the song!":
            update.message.reply_text(
                "I'll add it to the queue!",
                reply_markup = ReplyKeyboardRemove(),
            )
            self.update_me(update, context)
            del context.user_data["song_search_results"]
            return ConversationHandler.END
        elif response == "No, show me the other ones.":
            options = [["Try another search.", "Stop searching."]]
            options += [[x] for x in context.user_data["song_search_results"].keys()]
            update.message.reply_text(
                text = "Here is the list again. Can you see the right one now?",
                reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True),
            )
            return 1


    def cancel(self, update, context):
        update.message.reply_text(
            "Action canceled.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
