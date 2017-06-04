[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/s1cp/FacebookPages2Telegram/master/LICENSE)
[![Python Versions](https://img.shields.io/badge/python-3.4%2C%203.5%2C%203.6-blue.svg)](https://docs.python.org/3/)
[![Contact me on Telegram](https://img.shields.io/badge/Contact-Telegram-blue.svg)](https://t.me/s1cp0)

# fbpages-telegram-bot
## Introduction
A bot to forward Facebook page updates to a Telegram channel.

This bot is written in Python and uses the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) wrapper for the [Telegram Bot API](http://core.telegram.org/bots/api) and the [facebook-sdk](https://github.com/mobolic/facebook-sdk) client library for the [Facebook Graph API](https://developers.facebook.com/docs/graph-api).

## Setup
### Preparatory Setup
fbpages-telegram-bot uses Python 3 (developed and tested with version 3.6.0), which can be downloaded [here](https://www.python.org/downloads/) if you are running Windows, or by installing the ``python3`` package with your package manager if you're running Linux.

#### Example for Linux's apt-get:

``sudo apt-get install python3 -y``

You'll also need the following packages:
* `python-telegram-bot`
* `facebook-sdk`
* `youtube-dl`

These can all be installed with:

``pip3 install python-telegram-bot, facebook-sdk, youtube-dl ``

on both Windows's Command Prompt and Linux's terminal.


### Bot Setup
To get started with the bot itself:
1. Message [@BotFather](https://t.me/BotFather) on Telegram to create a new bot and get its token.
2. Start a conversation with your new bot and send any message to it. You can go to `https://api.telegram.org/bot<BOTID>/getUpdates` to find your `user_id` or `chat_id` to use in the settings file.
3. Add your newly created bot as an administrator of the channel that will receive the posts.
4. [Create a Facebook App](https://developers.facebook.com/apps/) and then go to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/). Choose your new app in the top right corner, and then click on `Get Token`, `Get App Token`. The `Access Token` field will now have the token required for the Facebook section of the settings file.
5. Clone the repository with `git clone https://github.com/s1cp/fbpages-telegram-bot.git`
6. Enter the new directory with `cd fbpages-telegram-bot`
7. Set the appropriate values in a file called `botsettings.ini`. Use ``example.botsettings.ini`` as an example with ``cp example.botsettings.ini botsettings.ini && nano botsettings.ini``.
8. Run the bot with `python3 facebook2telegram.py`

## Bot configuration values
### Facebook section

| Name          | Description                                                |
|:--------------|:-----------------------------------------------------------|
| `token`       | Facebook Graph API token.                                  |
| `pages`       | List of page IDs. Format: `['123456789', 'pageusername']`  |
| `refreshrate` | Time interval between every Facebook check, in seconds.    |
| `status`      | Allow status posts. Format: `True` or `False`              |
| `photo`       | Allow photo posts. Format: `True` or `False`               |
| `video`       | Allow video posts. Format: `True` or `False`               |
| `link`        | Allow link posts. Format: `True` or `False`                |
| `shared`      | Allow shared posts. Format: `True` or `False`              |
| `message`     | Allow message in posts. Format: `True` or `False`          |

#### Telegram section

| Name          | Description                                                |
|:--------------|:-----------------------------------------------------------|
| `token`       | Telegram Bot API token.                                    |
| `channel`     | Username of the channel that will receive the posts        |
| `admin`       | Optional. Bot creator's ID to receive the bot's status.    |
