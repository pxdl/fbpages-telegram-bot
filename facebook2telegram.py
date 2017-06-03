# coding=utf-8
import ast                                      #Used for pages list in ini
import configparser                             #Used for loading configs
import json                                     #Used for tacking last dates
import logging                                  #Used for logging
import sys                                      #Used for exiting the program
from datetime import datetime                   #Used for date comparison
from urllib import request                      #Used for downloading media

import telegram                                 #telegram-bot-python
from telegram.ext import Updater
from telegram.ext import Job
from telegram.error import TelegramError        #Error handling
from telegram.error import InvalidToken         #Error handling
from telegram.error import BadRequest           #Error handling
from telegram.error import TimedOut             #Error handling

import facebook                                 #facebook-sdk

import youtube_dl                               #youtube-dl


#Logging
logging.basicConfig(
    filename='facebook2telegram.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

#youtube-dl
ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s'})


def loadSettingsFile(filename):
    '''
    Loads the settings from the .ini file
    and stores them in global variables.
    Use example.botsettings.ini as an example.
    '''
    #Read config file
    Config = configparser.SafeConfigParser()
    Config.read(filename)

    #Load config
    try:
        global facebook_token
        global facebook_pages
        global facebook_refresh_rate
        global allow_status
        global allow_photo
        global allow_video
        global allow_link
        global allow_shared
        global allow_message
        global telegram_token
        global channel_id
        global admin_id

        facebook_token = Config.get('facebook', 'token')
        facebook_pages = ast.literal_eval(Config.get("facebook", "pages"))
        facebook_refresh_rate = float(Config.get('facebook', 'refreshrate'))
        allow_status = Config.getboolean('facebook', 'status')
        allow_photo = Config.getboolean('facebook', 'photo')
        allow_video = Config.getboolean('facebook', 'video')
        allow_link = Config.getboolean('facebook', 'link')
        allow_shared = Config.getboolean('facebook', 'shared')
        allow_message = Config.getboolean('facebook', 'message')
        telegram_token = Config.get('telegram', 'token')
        channel_id = Config.get('telegram', 'channel')
        admin_id = Config.get('telegram', 'admin')

        print('Loaded settings:')
        print('Channel: ' + channel_id)
        print('Refresh rate: ' + str(facebook_refresh_rate))
        print('Allow Status: ' + str(allow_status))
        print('Allow Photo: ' + str(allow_photo))
        print('Allow Video: ' + str(allow_video))
        print('Allow Link: ' + str(allow_link))
        print('Allow Shared: ' + str(allow_shared))
        print('Allow Message: ' + str(allow_message))

        return True

    except configparser.NoSectionError:
        sys.exit('Fatal Error: Missing or invalid settings file.')

    except configparser.NoOptionError:
        sys.exit('Fatal Error: Missing or invalid option in settings file.')

    except ValueError:
        sys.exit('Fatal Error: Missing or invalid value in settings file.')

    except SyntaxError:
        sys.exit('Fatal Error: Syntax error in page list.')


def loadFacebookGraph(facebook_token):
    '''
    Initialize Facebook GraphAPI with the token loaded from the settings file
    '''
    global graph
    graph = facebook.GraphAPI(access_token=facebook_token, version='2.7')


def loadTelegramBot(telegram_token):
    '''
    Initialize Telegram Bot API with the token loaded from the settings file
    '''
    global bot
    global updater
    global dispatcher
    global job_queue
    try:
        bot = telegram.Bot(token=telegram_token)
    except InvalidToken:
       sys.exit('Fatal Error: Invalid Telegram Token')
    updater = Updater(token=telegram_token)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue


def parsePostDate(post):
    '''
    Converts 'created_time' str from a Facebook post to the 'datetime' format
    '''
    date_format = "%Y-%m-%dT%H:%M:%S+0000"
    post_date = datetime.strptime(post['created_time'], date_format)
    return post_date


class dateTimeEncoder(json.JSONEncoder):
    '''
    Converts the 'datetime' type to an ISO timestamp for the JSON dumper
    '''
    def default(self, o):
        if isinstance(o, datetime):
            serial = o.isoformat()  #Save in ISO format
            return serial

        raise TypeError('Unknown type')
        return json.JSONEncoder.default(self, o)


def dateTimeDecoder(pairs, format="%Y-%m-%dT%H:%M:%S"):
    '''
    Converts the ISO timestamp to 'datetime' type for the JSON loader
    '''
    d = {}

    for k, v in pairs:
        if isinstance(v, str):
            try:
                d[k] = datetime.strptime(v, format)
            except ValueError:
                d[k] = v
        else:
            d[k] = v

    return d


def loadDatesJSON():
    '''
    Loads the .json file containing the latest post's date for every page
    loaded from the settings file to the 'last_posts_dates' dict
    '''
    global last_posts_dates
    with open('dates.json', 'r') as f:
        last_posts_dates = json.load(f, object_pairs_hook=dateTimeDecoder)
    print('Loaded JSON file.')


def dumpDatesJSON():
    '''
    Dumps the 'last_posts_dates' dict to a .json file containing the
    latest post's date for every page loaded from the settings file.
    '''
    global last_posts_dates
    with open('dates.json', 'w') as f:
        json.dump(last_posts_dates, f,
                  sort_keys=True, indent=4, cls=dateTimeEncoder)
    print('Dumped JSON file.')


def getMostRecentPostsDates():
    '''
    Gets the date for the most recent post for every page loaded from the
    settings file. If there is a 'dates.json' file, load it. If not, fetch
    the dates from Facebook and store them in the 'dates.json' file.
    The .json file is used to keep track of the latest posts posted to
    Telegram in case the bot is restarted after being down for a while.
    '''
    print('Getting most recent posts dates...')

    global last_posts_dates
    global start_time

    start_time = None
    last_posts_dates = {}

    last_posts = graph.get_objects(
                ids=facebook_pages,
                fields='name,posts.limit(1){created_time}')

    print('Trying to load JSON file...')

    try:
        loadDatesJSON()

        for page in facebook_pages:
            if page not in last_posts_dates:
                print('Checking if page '+page+' went online...')

                try:
                    last_post = last_posts[page]['posts']['data'][0]
                    last_posts_dates[page] = parsePostDate(last_post)
                    print('Page: '+last_posts[page]['name']+' went online.')
                    dumpDatesJSON()
                except KeyError:
                    print('Page '+page+' not found.')

        start_time = 0.0 #Makes the job run its callback function immediately

    except (IOError, ValueError):
        print('JSON file not found or corrupted, fetching latest dates...')

        for page in facebook_pages:
            try:
                last_post = last_posts[page]['posts']['data'][0]
                last_posts_dates[page] = parsePostDate(last_post)
                print('Checked page: '+last_posts[page]['name'])
            except KeyError:
                print('Page '+page+' not found.')

        dumpDatesJSON()


def getDirectURLVideo(video_id):
    '''
    Get direct URL for the video using GraphAPI and the post's 'object_id'
    '''
    print('Getting direct URL...')
    video_post = graph.get_object(
            id=video_id,
            fields='source')

    return video_post['source']


def getDirectURLVideoYDL(URL):
    '''
    Get direct URL for the video using youtube-dl
    '''
    with ydl:
        result = ydl.extract_info(URL, download=False) #Just get the link

    #Check if it's a playlist
    if 'entries' in result:
        video = result['entries'][0]
    else:
        video = result

    return video['url']


def postPhotoToChat(post, post_message, bot, chat_id):
    '''
    Posts the post's picture with the appropriate caption.
    '''
    direct_link = post['full_picture']

    try:
        bot.send_photo(
            chat_id=chat_id,
            photo=post['full_picture'],
            caption=post_message)

    except BadRequest:
        '''If the picture can't be sent using its URL,
        it is downloaded locally and uploaded to Telegram.'''
        try:
            print('Sending by URL failed, downloading file...')
            request.urlretrieve(direct_link, 'temp.jpg')
            print('Sending file...')
            picture = open('temp.jpg', 'rb')
            bot.send_photo(
                chat_id=chat_id,
                photo=picture,
                caption=post_message)

        except TimedOut:
            '''If there is a timeout, try again with a higher
            timeout value for 'bot.send_photo' '''
            print('File upload timed out, trying again...')
            print('Sending file...')
            picture = open('temp.jpg', 'rb')
            bot.send_photo(
                chat_id=chat_id,
                photo=picture,
                caption=post_message,
                timeout=60)

        except BadRequest:
            raise
            print('Could not send photo file, sending link...')
            bot.send_message(    #Send direct link as a message
                chat_id=chat_id,
                text=direct_link+'\n'+post_message)
            return


def postVideoToChat(post, post_message, bot, chat_id):
    """
    This function tries to pass 3 different URLs to the Telegram API
    instead of downloading the video file locally to save bandwidth.

    *First option:  Direct video source
    *Second option: Direct video source from youtube-dl
    *Third option:  Direct video source with smaller resolution

    If all three fail, it then sends the first link as a message,
    followed by the post's message.
    (TODO: 4th option - Download file locally for upload)
    """
    #If youtube link, post the link
    if 'caption' in post and post['caption'] == 'youtube.com':
        print('Sending YouTube link...')
        bot.send_message(
            chat_id=chat_id,
            text=post['link'])
    else:
        if 'object_id' in post:
            direct_link = getDirectURLVideo(post['object_id'])

        try:
            bot.send_video(
                chat_id=chat_id,
                video=direct_link,
                caption=post_message)

        except TelegramError:        #If the API can't send the video
            try:
                print('Could not post video, trying youtube-dl...')
                bot.send_video(
                    chat_id=chat_id,
                    video=getDirectURLVideoYDL(post['link']),
                    caption=post_message)

            except TelegramError:
                try:
                    print('Could not post video, trying smaller res...')
                    bot.send_video(
                        chat_id=chat_id,
                        video=post['source'],
                        caption=post_message)

                except TelegramError:    #If it still can't send the video
                    print('Could not post video, sending link...')
                    bot.send_message(    #Send direct link as a message
                        chat_id=chat_id,
                        text=direct_link+'\n'+post_message)


def postLinkToChat(post, post_message, bot, chat_id):
    '''
    Checks if the post has a message with its link in it. If it does,
    it sends only the message. If not, it sends the link followed by the
    post's message.
    '''
    if post['link'] in post_message:
        post_link = ''
    else:
        post_link = post['link']

    bot.send_message(
        chat_id=chat_id,
        text=post_link+'\n'+post_message)


def checkIfAllowedAndPost(post, bot, chat_id):
    '''
    Checks the type of the Facebook post and if it's allowed by the
    settings file, then calls the appropriate function for each type.
    '''
    #If it's a shared post, call this function for the parent post
    if 'parent_id' in post and allow_shared:
        print('This is a shared post.')
        parent_post = graph.get_object(
            id=post['parent_id'],
            fields='full_picture,created_time,type,\
                    message,source,link,caption,parent_id,object_id')
        print('Accessing parent post...')
        checkIfAllowedAndPost(parent_post, bot, chat_id)
        return True

    '''If there's a message in the post, and it's allowed by the
    settings file, store it in 'post_message', which will be passed to
    another function based on the post type.'''
    if 'message' in post and allow_message:
        post_message = post['message']
    else:
        post_message = ''

    if post['type'] == 'photo' and allow_photo:
        print('Posting photo...')
        postPhotoToChat(post, post_message, bot, chat_id)
        return True
    elif post['type'] == 'video' and allow_video:
        print('Posting video...')
        postVideoToChat(post, post_message, bot, chat_id)
        return True
    elif post['type'] == 'status' and allow_status:
        print('Posting status...')
        bot.send_message(
            chat_id=chat_id,
            text=post['message'])
        return True
    elif post['type'] == 'link' and allow_link:
        print('Posting link...')
        postLinkToChat(post, post_message, bot, chat_id)
        return True
    else:
        print('This post is a {}, skipping...'.format(post['type']))
        return False


def postToChat(post, bot, chat_id):
    '''
    Calls another function for posting and checks if it returns True.
    '''
    if checkIfAllowedAndPost(post, bot, chat_id):
        print('Posted.')


def periodicCheck(bot, job):
    '''
    Checks for new posts for every page in the list loaded from the
    settings file, posts them, and updates the dates.json file, which
    contains the date for the latest post posted to Telegram for every
    page.
    '''
    needDump = False
    chat_id = job.context
    print('Accessing Facebook...')

    try:
        #Request to the GraphAPI with all the pages (list) and required fields
        pages_dict = graph.get_objects(
            ids=facebook_pages,
            fields='name,\
                    posts{\
                          created_time,type,message,full_picture,\
                          source,link,caption,parent_id,object_id}')

        #If there is an admin chat ID in the settings file
        if admin_id:
            try:
                #Sends a message to the bot Admin confirming the action
                bot.send_message(
                    chat_id=admin_id,
                    text='Successfully fetched Facebook posts.')

            except TelegramError:
                print('Admin ID not found.')
                print('Successfully fetched Facebook posts.')

        else:
            print('Successfully fetched Facebook posts.')

    #Error in the Facebook API
    except facebook.GraphAPIError:
        print('Error: Could not get Facebook posts.')
        '''
        TODO: 'get_object' for every page individually, due to a bug
        in the Graph API that makes some pages return an OAuthException 1,
        which in turn doesn't allow the 'get_objects' method return a dict
        that has only the working pages, which is the expected behavior
        when one or more pages in 'facbeook_pages' are offline. One possible
        workaround is to create an Extended Page Access Token instad of an
        App Token, with the downside of having to renew it every two months.
        '''
        raise
        return

    #Iterate every page in the list loaded from the settings file
    for page in facebook_pages:
        try:
            print('Getting list of posts for page {}...'.format(
                                                    pages_dict[page]['name']))

            #List of last 25 posts for current page. Every post is a dict.
            posts_data = pages_dict[page]['posts']['data']

            #List of posts posted after "last posted date" for current page
            new_posts = list(filter(
                lambda post: parsePostDate(post) > last_posts_dates[page],
                posts_data))

            if not new_posts:
                print('No new posts for this page.')
                continue    #Goes to next iteration (page)

            #Post the posts after the last post date in chronological order
            for post in reversed(new_posts):
                try:
                    print('Posting NEW post...')
                    postToChat(post, bot, chat_id)
                    last_posts_dates[page] = parsePostDate(post)
                    needDump = True
                except BadRequest:
                    print('Error: Telegram could not send the message')
                    raise
                    continue

        #If 'page' is not present in 'pages_dict' returned by the GraphAPI
        except KeyError:
            print('Page not found.')
            continue

    #After iterating through all pages
    if needDump:
        dumpDatesJSON()

    print('Checked all pages. Next check in '
          +str(facebook_refresh_rate)
          +' seconds.')


def createCheckJob(bot):
    '''
    Creates a job that periodically calls the 'periodicCheck' function
    '''
    job_queue.run_repeating(periodicCheck, facebook_refresh_rate,
                            first=start_time, context=channel_id)
    print('Job created.')
    if admin_id:
        try:
            bot.send_message(
                chat_id=admin_id,
                text='Bot Started.')
        except TelegramError:
            print('Admin ID not found.')
            print('Bot Started.')


def error(bot, update, error):
    logger.warn('Update "{}" caused error "{}"'.format(update, error))


def main():
    loadSettingsFile('botsettings.ini')
    loadFacebookGraph(facebook_token)
    loadTelegramBot(telegram_token)
    getMostRecentPostsDates()

    createCheckJob(bot)

    #Log all errors
    dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
