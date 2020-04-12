# -*- coding: utf-8 -*-

import configparser
import tweepy
import datetime
import time
import re
import smtplib
import MeCab
import collections
import pprint
import json
import emoji

from wordcloud import WordCloud
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os

from datetime import datetime as dt
from email.mime.text import MIMEText
from email.utils import formatdate

import time

m = MeCab.Tagger('-Ochasen')
m.parse("")

#configuretion
config = configparser.ConfigParser()
config.read('config.ini')

CONSUMER_KEY = config.get('twitter', 'CONSUMER_KEY')
CONSUMER_SECRET = config.get('twitter', 'CONSUMER_SECRET')
ACCESS_TOKEN = config.get('twitter', 'ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = config.get('twitter', 'ACCESS_TOKEN_SECRET')

SMTP_SERVER = config.get('mail', 'SMTP_SERVER')
MAIL_ADDRESS = config.get('mail', 'MAIL_ADDRESS')
MAIL_PASSWORD = config.get('mail', 'MAIL_PASSWORD')
MAIL_TO_ADDRESS = config.get('mail', 'MAIL_TO_ADDRESS')

def get_twitter_message(q_words, count):
    #twitter auth.
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit = True)
    # search
    list_text = []
    query = q_words + " exclude:retweets"
    now = datetime.datetime.now()
    #print(query)
    tweets = api.search(q=query, result_type = 'recent', count=count, tweet_mode="extended")
    next_max_id = tweets[-1].id

    for tweet in tweets:
        list_text.append(tweet.full_text)

    i = 1
    time.sleep(5)

    while True:
        i += 1
        print('pages：' + str(i))
        try:
            tweets = api.search(q=query, count=count, max_id=next_max_id-1, tweet_mode="extended")

            for tweet in tweets:
                list_text.append(tweet.full_text)

        except tweepy.error.TweepError as tweeperror:
            print(tweeperror)
            time.sleep(60)
            continue

        try:
            next_max_id = tweets[-1].id
            post_date = tweets[-1].created_at + datetime.timedelta(hours=+9)
            print(post_date)

        except IndexError as ie:
            print(ie)
            break
            
        if (now - post_date) > datetime.timedelta(minutes=60):
            break
        else:
            time.sleep(1)

    list_tmp = []
    text_count = 0
    # text
    for text in list_text:
        text_count += 1
        text_tmp = text
        text_tmp = re.sub('RT .*', '', text_tmp)
        text_tmp = re.sub('@.*', '', text_tmp)
        text_tmp = re.sub('http.*', '', text_tmp)
        text_tmp = re.sub('https.*', '', text_tmp)
        text_tmp = re.sub('#.*', '', text_tmp)
        text_tmp = re.sub('\n', '', text_tmp)
        text_tmp = ''.join(c for c in text_tmp if c not in emoji.UNICODE_EMOJI)
        text_tmp = text_tmp.strip()
        if text_tmp != '':
            list_tmp.append(text_tmp)
#
    list_tmp = list(set(list_tmp))
    text = '\n'.join(list_tmp)
    return text, text_count
#

def create_message(from_addr, to_addr, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Date'] = formatdate()
    return msg

def send_mail(from_addr, to_addr, body_msg):
    smtpobj = smtplib.SMTP(SMTP_SERVER, 587)
    smtpobj.ehlo()
    smtpobj.starttls()
    smtpobj.ehlo()
    smtpobj.login(MAIL_ADDRESS, MAIL_PASSWORD)
    smtpobj.sendmail(MAIL_ADDRESS, to_addr, body_msg.as_string())
    smtpobj.close()

def mail_loop(q_words):

    # m = MeCab.Tagger('-Ochasen')
    # m.parse("")

    count = 200
    text, text_count = get_twitter_message(q_words, count)
    print(q_words + str(text_count) + "行")

    # Parse To Node.
    node = m.parseToNode(text)

    wc_words = ""
    words = []
    node = node.next

    while node:
        hinshi_1 = node.feature.split(",")[0]
        hinshi_2 = node.feature.split(",")[1]

        if hinshi_1 in ["名詞","動詞","形容詞"]:
            if hinshi_2 not in ["接尾", "非自立", ]:
                origin = node.surface
                #print(origin + hinshi_1 + hinshi_2)
                words.append(origin)
                #wc_words += re.sub(r'[^\\]', '', origin) + " "
                wc_words += origin + " "


        node = node.next

    count_twords = collections.Counter(words)
    pprint.pprint(count_twords.most_common(100))

    tdatetime = dt.now()
    str_ymd = tdatetime.strftime('%Y%m%d%H%M%S')
    subject = str_ymd

    # mail_text = json.dumps(count_twords)

    # create json file
    #with open(str_ymd + '.txt', 'w', encoding='utf-8',errors='ignore') as fw:
    #    json.dump(count_twords, fw, indent=4, ensure_ascii=False)

    body_msg = create_message(MAIL_ADDRESS, MAIL_TO_ADDRESS, subject, text)
    send_mail(MAIL_ADDRESS, MAIL_TO_ADDRESS, body_msg)

    return wc_words, text_count

def draw_wordcloud(wc_words, wc_filename):

    wordc = WordCloud(font_path="/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        background_color='black',
        width=800,height=600)
    wordc.generate(wc_words)
    wordc.to_file(wc_filename)

def tw_png(text, wc_filename):
    #twitter auth.
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit = True)

    while(True):
        try:
            api.update_with_media(filename=wc_filename,status=text)
            break
        except tweepy.TweepError as e:
            if (e.reason == "[{'message': 'Rate limit exceeded', 'code': 88}]" 
                or e.reason == "[{'message': 'Over capacity', 'code': 130}]"):

                print('sleep in 15 minutes.)')
                print(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
                time.sleep(60 * 15)

            else:
                break

def get_trend_words():
    #　twitter auth.
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    #　search JP trend.
    results = api.trends_place(id = 23424856)
    list_trend = []
    for result in results:
        for trend in result['trends']:
            list_trend.append(trend['name'])

    return list_trend

#
#   __main__
#

if __name__ == "__main__":

    while(True):

        t_words = get_trend_words()
        tdatetime = dt.now()
        str_ymd = tdatetime.strftime('%m/%d_%H:%M')
        
        l = 0

        for q_words in t_words:
            #q_words = "ニュース"
            print(q_words)
            wc_words, list_count = mail_loop(q_words)
            wc_filename = "wc.png"
            draw_wordcloud(wc_words, wc_filename)
            tw_text = " キーワード「 " + q_words + " 」（"+ str(list_count)+ " tweets）　 ６０分の言葉（実験中）#６０分のつぶやき #ワードクラウド " + str_ymd
            tw_png(tw_text, wc_filename)

            l += 1
            if l > 5:
                break

            time.sleep(180)
        
        sleeptime = 3600 * 12
        print(str(sleeptime) + ' seconds')
        time.sleep(sleeptime)
