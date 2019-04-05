from configparser import ConfigParser
from telegram.ext import Updater, MessageHandler, BaseFilter, CommandHandler, ConversationHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import pickle
from spotify_remote import SpotifyRemote

config = ConfigParser()
config.read("config.ini")

class AdminFilter(BaseFilter):
    def filter(self, message):
        user = message.from_user
        print(f"{user.first_name} {user.last_name} ({user.username}): {message.text}")
        return user.username == config.get("TELEGRAM", "DEFAULT_CONTACT")



class TelegramBot():
    def __init__(self, spotify_remote):
        self.updater = Updater(token = config.get("TELEGRAM", "BOT_TOKEN"))
        self.dispatcher = self.updater.dispatcher

        self.spotify = spotify_remote

        self.setup_admin_id()
        self.setup_admin_commands()

        self.dispatcher.add_handler(ConversationHandler(
            entry_points = [CommandHandler("song", self.start_song_search)],
            states = {0: [MessageHandler(Filters.text,
                                         self.search_for_track,
                                         pass_user_data=True)],
                      1: [MessageHandler(Filters.text,
                                         self.add_track,
                                         pass_user_data=True)]},
            fallbacks = [CommandHandler("cancel", self.cancel)]
        ))


    # setup methods
    def setup_admin_id(self):
        try:
            with open(config["TELEGRAM"]["SAVEPOINT"]+".p", "rb") as file:
                self.DEFAULT_CONTACT_ID = pickle.load(file)
        except FileNotFoundError:
            self.DEFAULT_CONTACT_ID = None

    def setup_admin_commands(self):
        ADMIN_COMMAND_MAP = {"chat_id": self.print_chat_id,
                             "register": self.register}
        for command in ADMIN_COMMAND_MAP:
            self.dispatcher.add_handler(CommandHandler(
                command,
                ADMIN_COMMAND_MAP[command],
                filters = AdminFilter()
            ))


    # methods to use from outside
    def start_bot(self):
        self.updater.start_polling() # start mainloop
        print("Startup successfull. Telegram-Bot is now online.")

    def stop_bot(self):
        print("Shutdown initiated.")
        self.updater.stop()

    def send_message(self, text, id):
        self.updater.bot.send_message(chat_id=id, text=text)

    def message_me(self, text):
        if not self.DEFAULT_CONTACT_ID == None:
            self.send_message(text, self.DEFAULT_CONTACT_ID)
        else:
            print("Please /register your Telegram Account to use this function.")


    # commands
    def print_chat_id(self, bot, update):
        chat_id = update.message.chat_id
        bot.send_message(chat_id = chat_id, text = chat_id)

    def register(self, bot, update):
        id = update.message.chat_id
        with open(config["TELEGRAM"]["SAVEPOINT"]+".p", "wb") as file:
            pickle.dump(id,file)
        self.DEFAULT_CONTACT_ID = id
        self.message_me("Registration successfull.")


    # advanced commands
    def start_song_search(self, bot, update):
        bot.send_message(chat_id=update.message.chat_id,
                         text="What do you want to listen to?")
        return 0

    def search_for_track(self, bot, update, user_data):
        results = self.spotify.search_track(update.message.text)
        options = [["Try another search.", "Stop searching."]]
        options += [[x] for x in results.keys()]
        bot.send_message(
            chat_id = update.message.chat_id,
            text = "These are the songs i found. Select the right one or try another search.",
            reply_markup = ReplyKeyboardMarkup(options, one_time_keyboard=True)
        )
        user_data["results"] = results
        return 1

    def add_track(self, bot, update, user_data):
        response = update.message.text
        if response == "Try another search.":
            update.message.reply_text("Okay, what is it?", reply_markup=ReplyKeyboardRemove())
            return 0
        elif response == "Stop searching.":
            update.message.reply_text("Sorry that i couldn't help you!", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END


        id = user_data["results"][response]
        update.message.reply_text("OK", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def cancel(self, bot, update):
        update.message.reply_text("Action canceled.")
        update.message.reply_text("", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
