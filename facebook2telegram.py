# coding=utf-8
from __future__ import unicode_literals         #Needed for youtube-dl
import ast                                      #Used for ini settings
import ConfigParser
import logging
from time import sleep
from datetime import datetime                   #Used for date comparison

import telegram                                 #telegram-bot-python
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import Job
from telegram.ext.dispatcher import run_async   #Needed for parallelism
from telegram.error import (TelegramError)      #Error handling

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
Config = ConfigParser.ConfigParser()
Config.read('botsettings.ini')

#Facebook
facebook_token = Config.get('facebook', 'token')
facebook_pages = ast.literal_eval(Config.get("facebook", "pages"))
facebook_refresh_rate = Config.get('facebook', 'refreshrate')
allow_status = Config.getboolean('facebook', 'status')
allow_photo = Config.getboolean('facebook', 'photo')
allow_video = Config.getboolean('facebook', 'video')
graph = facebook.GraphAPI(access_token=facebook_token, version='2.7')
#page_count = 0
#last_date_tg = 0

#Telegram
telegram_token = Config.get('telegram', 'token')
channel_id = Config.get('telegram', 'channel')
bot = telegram.Bot(token=telegram_token)
updater = Updater(token=telegram_token)
dispatcher = updater.dispatcher
job_queue = updater.job_queue


def getDirectURLVideo(URL):
    try:
        print('Using youtube-dl...')
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

        return video_url

    except:
        print('Error in youtube-dl, skipping video...')


def checkIfAllowedAndPost(post, bot, chat_id):
    if post['type'] == 'photo' and allow_photo:
        print('This is a photo')
        postPhotoToChat(post, bot, chat_id)
        return True
    elif post['type'] == 'video' and allow_video:
        print('This is a video')
        postVideoToChat(post, bot, chat_id)
        return True
    elif post['type'] == 'status' and allow_status:
        bot.send_message(
            chat_id=chat_id,
            text=post['message']
            )
        return True
    else:
        print('This post is a {}, skipping...'.format(post['type']))
        return False


def postPhotoToChat(post, bot, chat_id):
    if 'message' in post: # If the picture post contains a message
        print('Posting photo with message...')
        bot.send_photo(
            chat_id=chat_id,
            photo=post['full_picture'],
            caption=post['message'])
    else:
        print('Posting photo...')
        bot.send_photo(chat_id=chat_id, photo=post['full_picture'])


def postVideoToChat(post, bot, chat_id):
    #TODO: If youtube link, post the link (check post['caption'])
    if 'message' in post: # If the video post contains a message
        print('Posting video with message...')
        #print(post['source'])
        try:
            bot.send_video(
                chat_id=chat_id,
                video=getDirectURLVideo(post['link']),#source is inconsistent
                caption=post['message'])
        except TelegramError:
            print('Could not post video')
            #TODO: Download with youtube-dl in case post['source'] fails
    else:
        print('Posting video...')
        #print(post['source'])
        try:
            bot.send_video(
                chat_id=chat_id,
                video=getDirectURLVideo(post['link']))#source is inconsistent
        except TelegramError:
            print('Could not post video')


def postToChatAndSleep(post, bot, chat_id, sleeptime):
    if checkIfAllowedAndPost(post, bot, chat_id):
        print('Sleeping...')
        sleep(sleeptime)


#Posts last 25 media posts from every Facebook page in botsettings.ini
@run_async
def last25(bot, job):
    chat_id = job.context
    
    print('Accessing Facebook...')
    pages_dict = graph.get_objects(
        ids=facebook_pages,
        fields='name,posts{full_picture,created_time,type,message,source,link}')
    
    print('Preparing to start list loop...')
    for page in facebook_pages:
        try:
            print('Getting list of posts for page {}...'.format(
                pages_dict[page]['name']))
            
            #Get list of last 25 posts
            posts_data = pages_dict[page]['posts']['data']

            for post in reversed(posts_data):
                postToChatAndSleep(post, bot, chat_id, 1)

        except:
            print('Page error.')
            continue


def last25_job(bot, update, job_queue):
    update.message.reply_text('Sending...')

    job_last25 = Job(last25, 1.0, repeat=False, context=channel_id)
    job_queue.put(job_last25)


def periodicUpdate(bot, job):
    bot.send_message(chat_id=job.context, text="This is a periodic update.")


def createSubscription(bot, update, job_queue, chat_data):
    chat_id = update.message.chat_id

    job_checkNew = Job(
        periodicUpdate, facebook_refresh_rate,
        repeat=True, context=update.message.chat_id)
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
last25_handler = CommandHandler('ultimos', last25_job,
                                pass_job_queue=True)
subscription_handler = CommandHandler('subscribe', createSubscription,
                                      pass_job_queue=True,
                                      pass_chat_data=True)
unsubscribe_handler = CommandHandler('unsubscribe', deleteSubscription,
                                     pass_chat_data=True)
# on command message
dispatcher.add_handler(last25_handler)
dispatcher.add_handler(subscription_handler)
dispatcher.add_handler(unsubscribe_handler)
# log all errors
dispatcher.add_error_handler(error)

updater.start_polling()

updater.idle()
