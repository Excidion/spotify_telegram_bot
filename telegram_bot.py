from configparser import ConfigParser
from telegram.ext import Updater, MessageHandler, BaseFilter, CommandHandler
import pickle

config = ConfigParser()
config.read("config.ini")

class AdminFilter(BaseFilter):
    def filter(self, message):
        user = message.from_user
        print(f"{user.first_name} {user.last_name} ({user.username}): {message.text}")
        return user.username == config["TELEGRAM"]["DEFAULT_CONTACT"]



class TelegramBot():
    def __init__(self):
        self.updater = Updater(token = config["TELEGRAM"]["BOT_TOKEN"])
        dispatcher = self.updater.dispatcher

        try:
            with open(config["TELEGRAM"]["SAVEPOINT"]+".p", "rb") as file:
                self.DEFAULT_CONTACT_ID = pickle.load(file)
        except FileNotFoundError:
            self.DEFAULT_CONTACT_ID = None


        COMMAND_MAP = {"chat_id": self.print_chat_id,
                       "register": self.register}
        for command in COMMAND_MAP:
            dispatcher.add_handler(CommandHandler(command,
                                                  COMMAND_MAP[command],
                                                  filters = AdminFilter()))

    # methods from outside
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




if __name__ == '__main__':
    bot = TelegramBot()
    bot.start_bot()

    try:
        while True:
            pass
    except Exception as e:
        print(e)

    except KeyboardInterrupt:
        bot.stop_bot()
