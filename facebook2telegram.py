# coding=utf-8
from __future__ import unicode_literals         #Needed for youtube-dl
import ast                                      #Used for ini settings
import ConfigParser
import logging
from time import sleep
import sys
from datetime import datetime                   #Used for date comparison

import telegram                                 #telegram-bot-python
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import Job
#from telegram.ext.dispatcher import run_async   #Needed for parallelism
from telegram.error import (TelegramError, InvalidToken, BadRequest)      #Error handling

import facebook                                 #facebook-sdk

import youtube_dl

#Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

#youtube-dl
ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s'})

#Read config file
Config = ConfigParser.SafeConfigParser()
Config.read('botsettings.ini')



#Load settings file
try:
    facebook_token = Config.get('facebook', 'token')
    facebook_pages = ast.literal_eval(Config.get("facebook", "pages"))
    facebook_refresh_rate = Config.get('facebook', 'refreshrate')
    allow_status = Config.getboolean('facebook', 'status')
    allow_photo = Config.getboolean('facebook', 'photo')
    allow_video = Config.getboolean('facebook', 'video')
    allow_link = Config.getboolean('facebook', 'link')
    allow_shared = Config.getboolean('facebook', 'shared')
    allow_message = Config.getboolean('facebook', 'message')
    telegram_token = Config.get('telegram', 'token')
    channel_id = Config.get('telegram', 'channel')
except ConfigParser.NoSectionError:
    sys.exit('Fatal Error: Missing or invalid settings file.')
except ConfigParser.NoOptionError:
    sys.exit('Fatal Error: Missing or invalid option in settings file.')
except ValueError:
    sys.exit('Fatal Error: Missing or invalid value in settings file.')
except SyntaxError:
    sys.exit('Fatal Error: Syntax error in page list.')

#Facebook
graph = facebook.GraphAPI(access_token=facebook_token, version='2.7')
#page_count = 0
#last_date_tg = 0


def parsePostDate(post):
    post_date = datetime.strptime(post['created_time'],
                                  "%Y-%m-%dT%H:%M:%S+0000")
    return post_date


print('Getting most recent posts dates...')
last_post_date = {}
last_posts = graph.get_objects(
            ids=facebook_pages,
            fields='name,posts.limit(1){created_time}')
for page in facebook_pages:
    try:
        last_post_date[page] = parsePostDate(last_posts[page]['posts']['data'][0])
        print('Page: '+last_posts[page]['name'])
        print('Last updated: '+last_post_date[page].strftime('%Y-%m-%d %H:%M:%S +0')+'\n')
        
    except KeyError:
        print('Page '+page+' not found.')

#print (last_post_date)
print('Loaded settings:')
print('Channel: ' + channel_id)
print('Refresh rate: ' + facebook_refresh_rate)
print('Allow Status: ' + str(allow_status))
print('Allow Photo: ' + str(allow_photo))
print('Allow Video: ' + str(allow_video))
print('Allow Link: ' + str(allow_link))
print('Allow Shared: ' + str(allow_shared))
print('Allow Message: ' + str(allow_message))

#Telegram
try:
    bot = telegram.Bot(token=telegram_token)
except InvalidToken:
   sys.exit('Fatal Error: Invalid Telegram Token')
updater = Updater(token=telegram_token)
dispatcher = updater.dispatcher
job_queue = updater.job_queue


def getDirectURLVideo(video_id):
    print('Getting direct URL...')
    video_post = graph.get_object(
            id=video_id,
            fields='source')

    return video_post['source']


def getDirectURLVideoYDL(URL):
    with ydl:
        result = ydl.extract_info(
            '{}'.format(URL),
            download=False # We just want to extract the info
        )

    if 'entries' in result:
        # Can be a playlist or a list of videos
        video = result['entries'][0]
    else:
        # Just a video
        video = result

    video_url = video['url']
    print(video_url)

    return video_url


def checkIfAllowedAndPost(post, bot, chat_id):
    if 'parent_id' in post and allow_shared:
        print('This is a shared post.')
        parent_post = graph.get_object(
            id=post['parent_id'],
            fields='full_picture,created_time,type,\
                    message,source,link,caption,parent_id,object_id')
        print('Accessing parent post...')
        checkIfAllowedAndPost(parent_post, bot, chat_id)
        return True

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


def postPhotoToChat(post, post_message, bot, chat_id):
    bot.send_photo(
        chat_id=chat_id,
        photo=post['full_picture'],
        caption=post_message)


def postVideoToChat(post, post_message, bot, chat_id):
    #This function tries to pass 3 different URLs to the Telegram API
    #instead of downloading the video file locally to save bandwidth.
    #First link: Direct video source
    #Second link: Direct video source gotten from youtube-dl
    #Third link: Direct video source with smaller resolution
    #If all three fail, it then (TODO: 4th OPTION - DOWNLOAD FILE LOCALLY
    #FOR UPLOAD) sends the first link as a message, followed by the post's
    #message
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
                    print('Could not post video, trying smaller resolution...')
                    bot.send_video(
                        chat_id=chat_id,
                        video=post['source'],
                        caption=post_message)
                except TelegramError:    #If the API still can't send the video
                    print('Could not post video, sending link...')
                    bot.send_message(    #Send direct link as a message
                        chat_id=chat_id,
                        text=direct_link+'\n'+post_message)


def postLinkToChat(post, post_message, bot, chat_id):
    if post['link'] in post_message:
        post_link = ''
    else:
        post_link = post['link']

    bot.send_message(
        chat_id=chat_id,
        text=post_link+'\n'+post_message)

def postToChatAndSleep(post, bot, chat_id, sleeptime):
    if checkIfAllowedAndPost(post, bot, chat_id):
        print('Sleeping...')
        sleep(sleeptime)

def postToChat(post, bot, chat_id):
    if checkIfAllowedAndPost(post, bot, chat_id):
        print('Posted.')


def periodicCheck(bot, job):
    chat_id = job.context
    print('Accessing Facebook...')
    try:
        pages_dict = graph.get_objects(
            ids=facebook_pages,
            fields='name,posts{\
                               full_picture,created_time,type,\
                               message,source,link,caption,parent_id,object_id}')
    except facebook.GraphAPIError:
        print('Error: Could not get Facebook posts.')
        return
    for page in facebook_pages:
        try:
            print('Getting list of posts for page {}...'.format(
                pages_dict[page]['name']))
            
            #Get list of last 25 posts
            posts_data = pages_dict[page]['posts']['data']
            new_posts = filter(lambda post: parsePostDate(post) > last_post_date[page], posts_data)
            if not new_posts:
                print('No new posts.')
                continue
            for post in reversed(new_posts):   #Chronological order
                try:
                    print('Posting NEW post...')
                    postToChat(post, bot, chat_id)
                    last_post_date[page] = parsePostDate(post)
                except BadRequest:
                    print('Error: Telegram chat not found')
                    return

        except KeyError:
            print('Page not found.')
            continue


def createSubscription(bot, update, job_queue, chat_data):
    job_checkNew = Job(
        periodicCheck, float(facebook_refresh_rate),
        repeat=True, context=channel_id)
    job_queue.put(job_checkNew)
    chat_data['job'] = job_checkNew

    update.message.reply_text('Subscribed.')


def deleteSubscription(bot, update, chat_data):
    if 'job' not in chat_data:
        update.message.reply_text('You are not subscribed.')
        return

    job_checkNew = chat_data['job']
    job_checkNew.schedule_removal()
    del chat_data['job']

    update.message.reply_text('Unsubscribed.')


def error(bot, update, error):
    logger.warn('Update "{}" caused error "{}"'.format(update, error))
    

# on different commands - answer in Telegram
subscription_handler = CommandHandler('subscribe', createSubscription,
                                      pass_job_queue=True,
                                      pass_chat_data=True)
unsubscribe_handler = CommandHandler('unsubscribe', deleteSubscription,
                                     pass_chat_data=True)
# on command message
dispatcher.add_handler(subscription_handler)
dispatcher.add_handler(unsubscribe_handler)
# log all errors
dispatcher.add_error_handler(error)

updater.start_polling()

updater.idle()
