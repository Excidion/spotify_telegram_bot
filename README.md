# Spotify Telegram Bot

## Setup
Before being able to use this bot, some setup work is required.
### Perequisites
+ [Telegram](https://telegram.org/) account.
+ [Spotify developer](https://developer.spotify.com/) account.

### Configuration
+ Create a new application at the [spotify developer dashboard](https://developer.spotify.com/dashboard/applications) and go to it's overview page.
    + Get the **Client ID** and the **Client Secret** and copy them into the [`config.ini`](config.ini).
    + Go to **Edit Settings** and add `http://localhost:/callback` to the **Redirect URIs**. Click on **Save**.
+ Contact the [@BotFather](https://t.me/BotFather) and create a new bot by texting him `/newbot`.
    + Follow his instructions until everything is ready to go.
    + Once the bot is created he will send you an access **token**. Copy this token into the [`config.ini`](config.ini).
+ In the section `TELEGRAM` in the [`config.ini`](config.ini) enter your Telegram username as the `ADMIN`. Your Telegram username will look like this: `@username`. Leave out the `@` at the beginning.
+ In the section `TELEGRAM` in the [`config.ini`](config.ini) enter a `password`. Tell this to your guests, so they can use the bot.
+ In the section `SPOTIFY` in the [`config.ini`](config.ini) enter your spotify username and a link to a spotify playlist that the bot should play from in case the the queue is empty.

### On the first start
You can now start up the bot via `python main.py` from the code directory.
There are still two tasks to do after this, that will not be required again, unless you re-install the bot.
+ On start-up the bot will open a web page in your browser and ask for access permissions to your Spotify account.
Once you give the permission you will be forwarded to another link.
Copy this link into the terminal and press enter.

+ Contact the bot from the Telegram account you set as `ADMIN` and send him the `/register` command. This way, he can save your *chat_id* to contact you with live updates.
