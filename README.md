[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/s1cp/FacebookPages2Telegram/master/LICENSE)

# fbpages-telegram-bot (Archived)

> **This project is archived and no longer functional.** See [Why is this archived?](#why-is-this-archived) below.

A bot that forwarded Facebook page updates to a Telegram channel.

Written in Python, it used [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the [Telegram Bot API](http://core.telegram.org/bots/api) and [facebook-sdk](https://github.com/mobolic/facebook-sdk) for the [Facebook Graph API](https://developers.facebook.com/docs/graph-api).

## Why is this archived?

This bot was built in 2017 targeting Python 3.6, Facebook Graph API v2.7, and libraries that have since been abandoned or undergone breaking rewrites. It is no longer functional for the following reasons:

### Facebook API access is effectively dead for this use case

Following the Cambridge Analytica scandal in 2018, Facebook (now Meta) drastically restricted its Graph API:

- **Graph API v2.7** (used by this bot) was shut down long ago. The current version is v22+.
- Reading posts from **pages you don't manage** now requires **Business Verification** and **App Review** approval for the "Page Public Content Access" feature. Meta routinely denies hobbyist and personal projects.
- Reading posts from **pages you do manage** is still possible with a Page Access Token, but requires periodic token refresh (~60 days).

In short, the simple "create an app, get a token, read any public page" workflow this bot relied on no longer exists.

### Outdated dependencies

| Dependency | Issue |
|---|---|
| `facebook-sdk` | Last released in 2018. Unmaintained. |
| `youtube-dl` | Abandoned/DMCA'd. Superseded by [yt-dlp](https://github.com/yt-dlp/yt-dlp). |
| `python-telegram-bot` | The bot uses the old synchronous API (v12/v13). v20+ is fully async with a completely different API surface. |

### Code-level issues

- Excessive use of global variables instead of proper encapsulation
- Uses `configparser.SafeConfigParser` (removed in Python 3.12)
- Uses `print()` instead of the logging module throughout
- Several bugs (undefined variables in error paths, dead code)
- Telegram caption limit hardcoded to 200 characters (now 1024)

## Original setup instructions (for reference only)

<details>
<summary>Click to expand</summary>

### Preparatory Setup
fbpages-telegram-bot used Python 3 (developed and tested with version 3.6.0).

Required packages:
* `python-telegram-bot`
* `facebook-sdk`
* `youtube-dl`

Installed with:

``pip3 install python-telegram-bot, facebook-sdk, youtube-dl``

### Bot Setup
1. Message [@BotFather](https://t.me/BotFather) on Telegram to create a new bot and get its token.
2. Start a conversation with your new bot and send any message to it. You can go to `https://api.telegram.org/bot<BOTID>/getUpdates` to find your `user_id` or `chat_id` to use in the settings file.
3. Add your newly created bot as an administrator of the channel that will receive the posts.
4. [Create a Facebook App](https://developers.facebook.com/apps/) and then go to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/). Choose your new app in the top right corner, and then click on `Get Token`, `Get App Token`. The `Access Token` field will now have the token required for the Facebook section of the settings file.
5. Clone the repository with `git clone https://github.com/s1cp/fbpages-telegram-bot.git`
6. Enter the new directory with `cd fbpages-telegram-bot`
7. Set the appropriate values in a file called `botsettings.ini`. Use ``example.botsettings.ini`` as an example with ``cp example.botsettings.ini botsettings.ini && nano botsettings.ini``.
8. Run the bot with `python3 facebook2telegram.py`

### Bot configuration values
#### Facebook section

| Name          | Description                                                    |
|:--------------|:---------------------------------------------------------------|
| `locale`      | Facebook locale. Format example: `en-US`                       |
| `token`       | Facebook Graph API token.                                      |
| `pages`       | List of page IDs. Format example: `['123456789',pageusername']`|
| `refreshrate` | Time interval between every Facebook check, in seconds.        |
| `status`      | Allow status posts. Format: `True` or `False`                  |
| `photo`       | Allow photo posts. Format: `True` or `False`                   |
| `video`       | Allow video posts. Format: `True` or `False`                   |
| `link`        | Allow link posts. Format: `True` or `False`                    |
| `shared`      | Allow shared posts. Format: `True` or `False`                  |
| `message`     | Allow message in posts. Format: `True` or `False`              |

#### Telegram section

| Name          | Description                                                    |
|:--------------|:---------------------------------------------------------------|
| `token`       | Telegram Bot API token.                                        |
| `channel`     | Username of the channel that will receive the posts            |
| `admin`       | Optional. Bot creator's ID to receive the bot's status.        |

</details>

## License

[MIT](LICENSE)
