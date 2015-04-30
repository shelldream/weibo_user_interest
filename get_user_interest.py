# -*- coding: utf-8 -*-
import sys
reload(sys).setdefaultencoding('utf-8')
from collections import Counter
import re
import codecs
import time

import jieba
import jieba.analyse
from Fetcher import *

def get_keywords(myFetcher,uid_list):
    '''
        从uid_list的所有用户信息文本中抽取关键词
        input:
            myFetcher:Fetcher对象,用于爬取用户信息
            uid_list:用户uid列表,list of unicode
        output:
            keywords:关键词列表[(关键词1,权重1)……]
    '''
    info_dict = {}
    tags = []#用户的tags信息列表
    profiles = []#用户的profile信息列表
    for uid in uid_list:
        uid = unicode(uid)
        #print uid
        info_dict = myFetcher.get_user_tags(uid)
        time.sleep(0.3)
        user_tags = info_dict['tags'] #unicode
        user_profile = info_dict['profile']
        #print user_tags+user_profile
        if len(user_tags):
            tags.append(user_tags)
        if len(user_profile):
            profiles.append(user_profile)
    tags_str = "".join(tags)
    profiles_str = "".join(profiles)
    tags_str += profiles_str
    jieba.analyse.set_stop_words('stop_words.txt')
    keywords = jieba.analyse.extract_tags(tags_str,topK=30,withWeight=True)
    return keywords

def get_interest(uid,username,passwd):
    '''
        uid:用户id,unicode
        得到uid用户所发微博中的前20高频词
    '''
    with codecs.open('stop_words.txt','r','utf-8') as fr:
        stop_words = [line.strip() for line in fr]
    stop_words.append(' ')
    stop_words.append('\n')
    stop_words.append('\t')

    myFetcher = Fetcher(username,passwd)
    myFetcher.login()

    
    follows_list = myFetcher.get_user_follows(uid)
    follows_list.append(uid)
    
    fans_list = myFetcher.get_user_fans(uid)
    print len(follows_list)
    print len(fans_list)

    follows_keywords = get_keywords(myFetcher,follows_list)
    follows_interest = {}
    for word in follows_keywords:
            follows_interest[word[0]] = word[1]

    fans_keywords = get_keywords(myFetcher,fans_list)
    fans_interest = {}
    for word in fans_keywords:
            fans_interest[word[0]] = word[1]

    user_weibos = myFetcher.get_user_weibos(uid)
    weibos = ".".join(user_weibos)

    content_interest = {}#从用户发布的微博信息中提取的兴趣关键词
    words = jieba.cut(weibos)
    filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
    all_words_count = float(len(filtered_words))
    counter = Counter(filtered_words)
    key_words = counter.most_common(30)
    outputs = []
    for item in key_words:
        if isinstance(item[0],unicode):
            k_word = item[0].decode('utf-8')
            weight = float(item[1])/all_words_count
        else:
            k_word = item[0]
            weight = float(item[1])/all_words_count
        outputs.append("%s\t%f\n"%(k_word,weight))
        content_interest[k_word] = weight

    #对两类兴趣词的权重进行归一化
    max_weight_content = max(content_interest.values())
    max_weight_follows = max(follows_interest.values())
    max_weight_fans = max(fans_interest.values())

    for word1,weight1 in content_interest.iteritems():
        weight1 /= max_weight_content

    for word2,weight2 in follows_interest.iteritems():
        weight2 /= max_weight_follows

    for word3,weight3 in fans_interest.iteritems():
        weight3 /= max_weight_fans

    interest_words = {}
    all_words = follows_interest.keys() + content_interest.keys() + fans_interest.keys()

    for word in all_words:
        content_weight = content_interest.get(word,0)
        follows_weight = follows_interest.get(word,0)
        fans_weight = fans_interest.get(word,0)
        all_weight = 0.5*follows_weight + 0.4*content_weight + 0.1*fans_weight 
        interest_words[word] = all_weight

    sorted_words = sorted(interest_words.iteritems(),key=lambda (k,v):v,reverse=True)

    for item in sorted_words[:30]:
        print item[0].encode('utf-8',''),item[1]

if __name__ == '__main__':
    username = 'kobe1994hxj@163.com'#微博登陆账号
    passwd = 'hao123'#微博登陆密码
    get_interest(u'2865191107',username,passwd)
