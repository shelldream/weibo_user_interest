#! /usr/bin/env python
#-*- coding:utf-8 -*-
'''
    Author:Xiaojun Huang
    Date:2015-03-28-15:20
    Version:0.1.0
    利用cookie模拟登录手机版新浪微博，爬取某个用户的用户信息(粉丝数、微博数、关注数、标签)
'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import cookielib
import urllib2
import urllib
import lxml.html as HTML
import re
import os
import time


class Fetcher(object):
    def __init__(self,username,pwd,cookie_filename=None):
        self.cj = cookielib.LWPCookieJar()
        if cookie_filename is not None:
            self.cj.load(cookie_filename)
        self.cookie_processor = urllib2.HTTPCookieProcessor(self.cj)
        self.opener = urllib2.build_opener(self.cookie_processor, urllib2.HTTPHandler)
        urllib2.install_opener(self.opener)

        self.username = username
        self.pwd = pwd
        #self.headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1',
        #               'Referer':'','Content-Type':'application/x-www-form-urlencoded'}
        self.headers = {  
            #'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:37.0) Gecko/20100101 Firefox/37.0',
            'Referer':'http://login.weibo.cn/login/' ,
            'Content-Type':'application/x-www-form-urlencoded'
        }  

    def get_rand(self, url):
        #headers = {'User-Agent':'Mozilla/5.0 (Windows;U;Windows NT 5.1;zh-CN;rv:1.9.2.9)Gecko/20100824 Firefox/3.6.9',
        #           'Referer':''}
        req = urllib2.Request(url ,urllib.urlencode({}), self.headers)
        resp = urllib2.urlopen(req)
        login_page = resp.read()
        rand = HTML.fromstring(login_page).xpath("//form/@action")[0]
        passwd = HTML.fromstring(login_page).xpath("//input[@type='password']/@name")[0]
        vk = HTML.fromstring(login_page).xpath("//input[@name='vk']/@value")[0]
        return rand, passwd, vk

    def login(self):
        url = 'http://login.weibo.cn/login/' #登录页面url
        #url = 'https://passport.weibo.cn/signin/login'
        rand, passwd, vk = self.get_rand(url)
        data = urllib.urlencode({'mobile': self.username,
                                    passwd: self.pwd,
                                    'remember': 'on',
                                    'backURL': 'http://weibo.cn/',
                                    'backTitle': '新浪微博',
                                    'vk': vk,
                                    'submit': '登录',
                                    'encoding': 'utf-8'})
        req = urllib2.Request(url,data,self.headers)
        resq = urllib2.urlopen(req)
        page = resq.read()
        HTML_str = HTML.fromstring(page)
        divs = HTML_str.xpath("//div[@class='tip2']//a")
        if not len(divs):
            raise LoginError("Login failed!")
        else:
            print "Login successfully!"

    def openURL(self,url,type=1):
        '''
            打开url所指向的页面，
            如果type=1，则返回该页面的HtmlElement对象
            如果type=0，怎返回该页面的str对象
        '''
        req = urllib2.Request(url,urllib.urlencode({}),self.headers)
        page = urllib2.urlopen(req).read().encode('utf-8')
        if type == 0:
            return page
        else:
            return HTML.fromstring(page)

    def get_user_weibos (self,uid,topk = 250):
        '''
            获得用户最近发布的topk条微博，默认为最近的250条
            返回微博列表
        '''
        if not isinstance(uid,unicode):
            raise ValueError('Type of uid must be unicode!')
        outputs = []
        page = 1
        while len(outputs) <= topk and page < 30:
            home_url = 'http://weibo.cn/u/' + str(uid) + "?page=" + str(page)
            HTML_str = self.openURL(home_url,0)
            time.sleep(0.3)
            if page == 1:
                weibos = re.findall(r'<span class="ctt">.*?</span>',HTML_str)[3:]
            else: 
                weibos = re.findall(r'<span class="ctt">.*?</span>',HTML_str)

            for weibo in weibos:
                weibo = re.sub(r'<.*?>','',weibo)
                outputs.append(weibo)
            page += 1
        if len(outputs) < topk:
             return outputs
        else:
            return outputs[0:topk]

    def get_user_follows(self,uid):
        '''
            input:uid,unicode
            output:follows_list,用户的关注列表
        '''
        follows_list = []
        page = 1
        while page <= 15:
            follows_page = 'http://weibo.cn/' + str(uid) + "/follow?page=" + str(page)
            HTML_str = self.openURL(follows_page)
            time.sleep(0.3)
            follows = HTML_str.xpath('//td[@ valign="top"]/a')
            #print len(follows)
            for item in follows:
                if item.text == '关注他':
                    follow_uid = re.findall(r'uid=\d+',item.attrib['href'])[0]
                    follow_uid = re.sub(r'uid=','',follow_uid)
                    follows_list.append(follow_uid)
                    #print follow_uid
            page += 1
        return follows_list

    def get_user_tags(self,uid):
        '''
            获得用户的标签信息
            input：
                用户uid,unicode
            output：
                info_dict:返回用户信息字典
                {'uid':用户的uid,tags':用户标签(每个标签以,作为分割符),'profile':用户简介信息}
        '''
        if not isinstance(uid,unicode):
            raise ValueError('Type of uid must be unicode!')
        info_dict = {}
        info_dict['uid'] = uid

        try:
            #抓取用户标签
            tags_url = 'http://weibo.cn/account/privacy/tags/?uid=' + str(uid)#标签页url
            HTML_str = self.openURL(tags_url)
            tags_words = HTML_str.xpath("//div[@class='c']//a")
            tags_filter_words = [u'皮肤',u'图片',u'条数',u'隐私',u'触屏',u'语音']
            tags_list = []
            for key,tag in enumerate(tags_words):
                if key:
                    if tag.text not in tags_filter_words:
                        tags_list.append(tag.text)
            info_dict['tags'] = ",".join(tags_list)

            info_url = 'http://weibo.cn/' + str(uid) + '/info'
            req = urllib2.Request(info_url,urllib.urlencode({}),self.headers)
            page = urllib2.urlopen(req).read().encode('utf-8')
            info_list = re.findall(r'昵称.*<br/>',page)
            if len(info_list):
                info_words = info_list[0].split('<br/>')
            filter_words = ['认证:','认证信息：']
            other_info = []
            for item in info_words:
                for word in filter_words:
                    if word in item:
                        other_info.append(re.sub(word,'',item)*5)
                if "简介:" in item:
                    other_info.append(re.sub("简介:",'',item))
            info_dict['profile'] = "".join(other_info)
        except :
            raise FetchError
        return info_dict

    def get_user_fans(self,uid):
        fans_list = []
        page = 1
        while page <= 15:
            fans_page = 'http://weibo.cn/' + str(uid) + "/fans?page=" + str(page)
            HTML_str = self.openURL(fans_page)
            time.sleep(0.5)
            fans = HTML_str.xpath('//td[@ valign="top"]/a')
            #print len(follows)
            for item in fans:
                if item.text == '关注他':
                    fans_uid = re.findall(r'uid=\d+',item.attrib['href'])[0]
                    fans_uid = re.sub(r'uid=','',fans_uid)
                    #print fans_uid
                    fans_list.append(fans_uid)
            page += 1
        return fans_list


class LoginError(Exception):
    def __init__(self,name = "Login failed!"):
        self.name = name
        self.code = 1

class FetchError(Exception):
    def __init__(self):
        self.code = 2



if __name__ == '__main__':
    username = 'kobe1993hxj@163.com'
    passwd = 'hao123'
    myFetcher = Fetcher(username,passwd)
    myFetcher.login()
    weibos = myFetcher.get_user_weibos(u'49766754')
    for weibo in weibos:
        print weibo