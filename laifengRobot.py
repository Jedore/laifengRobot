#!/usr/bin/env python
# -*-coding:utf8 -*-

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait as WDW
# from selenium.webdriver.support import expected_conditions as EC
import websocket
import urllib
import urllib2
import requests
import re
import json
import time
import traceback
import ConfigParser
import threading
import random
import logging
import signal
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


class LFRobot(object):
    " The LFRobot class can login websocket of laifeng and send messages."

    # limit the attributer
    __slots__ = ('__roomid', '__url', '__ws', '__driver', '__conf', 'msgs',
                 '__medal', '__gift', '__lastSendstar', '__lastGift',
                 'welFans', 'welManager', 'welVisitor', 'username', 'password',
                 '__logger', 'logfile', '__timerMsg', '__liveFlag',
                 '__timerLive', '__tuling_key', '__cq', '__timerCao',
                 '__qqkey', '__qqmsg', '__attentionMsg', '__giftMsg',
                 '__robotMsg', 'page')

    def __init__(self, rid=None):
        self.__roomid = rid
        self.__url = 'http://v.laifeng.com/'
        self.__ws = None
        self.__driver = None
        self.__conf = {}              # data dic for connecting server
        self.__medal = {}             # medal dic
        self.__gift = {}              # gift dic

        self.__lastSendstar = None    # last star sender
        self.__lastGift = None        # last gift and sender
        self.msgs = []                 # random msg list
        self.welFans = None
        self.welVisitor = {}
        self.welManager = None
        self.__logger = None
        self.logfile = 'laifeng.log'
        self.__timerMsg = None
        self.__timerCao = None
        self.__timerLive = None
        self.__liveFlag = None
        self.__tuling_key = None
        self.__cq = {}
        self.__robotMsg = '主播不在家,想发啥发啥[贱]'

    def __len__(self):
        " Return the length of LFRobot."

        return 100

    def __str__(self):
        " Called when print isinstance of LFRobot."

        return 'LFRobot object (roomid: %s)' % self.roomid

    def __repr__(self):
        " Called when '>>x' x is isinstance of LFRobot."

        return 'LFRobot object (roomid: %s)' % self.roomid

    def __call__(self):
        " Call the isinstance self."

        print 'Roomid is {0}.'.format(self.__roomid)

    def __getattr__(self, attr):
        " Called when has no this attr."

        return None

    @property
    def roomid(self):
        return self.__roomid

    @roomid.setter
    def roomid(self, rid):
        if isinstance(rid, int):
            if rid <= 0:
                raise ValueError('roomid should big than 0!')
            else:
                rid = str(rid)
        elif isinstance(rid, str):
            if not rid.isdigit():
                raise ValueError('roomid should be consist of digits!')
        else:
            raise ValueError('roomid should be int or str!')
        self.__roomid = rid

    def init(self):
        " Initial configure."

        cp = ConfigParser.SafeConfigParser()
        cp.read('laifeng.conf')
        if self.__roomid:
            self.__conf['roomid'] = self.__roomid
        else:
            self.__roomid = self.__conf['roomid'] = cp.get('laifeng', 'roomid')
        self.__conf['uid'] = cp.get('laifeng', 'userid')
        self.__conf['token'] = cp.get('laifeng', 'token')
        self.__conf['mk'] = cp.get('laifeng', 'mk')
        self.__conf['yktk'] = cp.get('laifeng', 'yktk')
        self.__conf['isPushHis'] = cp.get('laifeng', 'isPushHis')
        self.__conf['ws_host'] = cp.get('laifeng', 'ws_host')

        self.welVisitor = cp.get('msg', 'welVisitor').split('|')
        self.welManager = cp.get('msg', 'welManager')
        self.welFans = cp.get('msg', 'welFans')
        self.msgs = cp.get('msg', 'msgs').split('|')
        self.__qqkey = cp.get('msg', 'qqkey')
        self.__qqmsg = cp.get('msg', 'qqmsg')
        self.__attentionMsg = cp.get('msg', 'attentionMsg')
        self.__giftMsg = cp.get('msg', 'giftMsg')

        self.__medal = json.loads(cp.get('dic', 'medal'))
        self.__gift = json.loads(cp.get('dic', 'gift'))

        # config logging
        logger = logging.getLogger()
        f = logging.FileHandler(self.logfile)
        logger.addHandler(f)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(filename)s\
                                      %(lineno)d %(message)s")
        f.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        self.__logger = logger

        self.__tuling_key = cp.get('tuling', 'APIkey')
        self.__cq = cp.get('msg', 'cq').split('|')

    def tuling_auto_reply(self, msg):
        if self.__tuling_key:
            url = "http://www.tuling123.com/openapi/api"
            body = {'key': self.__tuling_key, 'info': msg}
            r = requests.post(url, data=body)
            respond = json.loads(r.text)
            result = ''
            if respond['code'] == 100000:
                result = respond['text'].replace('<br>', '  ')
                result = result.replace(u'\xa0', u' ')
            elif respond['code'] == 200000:
                result = respond['url']
            elif respond['code'] == 302000:
                for k in respond['list']:
                    result = result + u"【" + k['source'] + u"】 " +\
                        k['article'] + "\t" + k['detailurl'] + "\n"
            else:
                result = respond['text'].replace('<br>', '  ')
                result = result.replace(u'\xa0', u' ')

            return result

    def LiveOrNolive(self):
        " Timer to check whether live or not."

        ret = urllib2.urlopen(self.__url + self.__roomid).read()
        pat = 'DDS.baseInfo = {.+isShowing:(.*?),.+?};'
        isShowing = re.search(pat, ret, re.S).group(1)

        if isShowing.lower() == 'true':
            if self.__liveFlag is None or not self.__liveFlag:
                self.__liveFlag = True
                self.__logger.info('Anchorman Live.')
        else:
            if self.__liveFlag is None or self.__liveFlag:
                self.__liveFlag = False
                self.__logger.info('Anchorman noLive.')

        # stop __timerMsg start __timerCao when nolive
        # start __timerMsg start __timerMsg when live
        if not self.__liveFlag:
            if self.__timerMsg:
                self.__timerMsg.cancel()
                self.__timerMsg = None
            if self.__timerCao is None:
                self.TimerCao()
        else:
            if self.__timerMsg is None:
                self.TimerMessage()
            if self.__timerCao:
                self.__timerCao.cancel()
                self.__timerCao = None

        self.__timerLive = threading.Timer(60, self.LiveOrNolive)
        self.__timerLive.start()

    def TimerMessage(self):
        " Timer to send random message."

        index = random.randint(0, len(self.msgs)-1)
        msg = self.genMessage(self.msgs[index])
        self.__ws.send(msg)
        self.__timerMsg = threading.Timer(180, self.TimerMessage)
        self.__timerMsg.start()

    def TimerCao(self):
        " Timer to get activity level when nolive."

        if self.__timerCao:
            self.__robotMsg = self.tuling_auto_reply(self.__robotMsg)
        msg = self.genMessage(self.__robotMsg)
        self.__ws.send(msg)
        self.__timerCao = threading.Timer(60, self.TimerCao)
        self.__timerCao.start()

    def on_message(self, ws, message):
        " Response to websocket message."

        if "1:::" == message:
            self.onInitMsg()
        elif "2:::" == message:
            ws.send("2::")
        elif "5:::" in message:
            # Don't respond to messages when nolive
            if not self.__liveFlag and self.__liveFlag is not None:
                return

            dic = json.loads(message[4:])
            mType = dic['name']
            args = dic['args'][0]

            if 'result' == mType:
                # '1':success
                if '1' == args['code']:
                    # check live or nolive
                    self.LiveOrNolive()
            elif 'enterMessage' == mType:
                self.onEnterMsg(args)
            elif 'chatMessage' == mType:
                self.onChatMsg(args)
            elif 'Chat_response' == mType:
                self.onChatResponse(args)
            elif 'attention_user_update' == mType:
                self.onAttention(args)
            elif 'sendGift' == mType:
                self.onSendgift(args)
            elif 'sendBigGift' == mType:
                pass
            elif 'sendStar' == mType:
                self.onSendstar(args)
            elif 'user_praised1' == mType:
                pass
            elif 'usercount' == mType:
                # ucount = args['usercount']
                pass
            elif 'popular_screen' == mType:
                pass
            else:
                pass

    def onInitMsg(self):
        " First batch messages to connect the websocket server."

        dic = {}
        dic['token'] = self.__conf['token']
        dic['uid'] = self.__conf['uid']
        dic['roomid'] = self.__conf['roomid']
        dic['isPushHis'] = self.__conf['isPushHis']
        dic['yktk'] = ''
        dic['endpointtype'] = "ct_, dt_1_1000|0|{0}_{1}".\
            format(self.__conf['mk'], int(time.time()*1000))
        dic_data = {'name': 'enter', 'args': [dic]}
        data = '5:::{0}'.format(json.dumps(dic_data))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'PatronSaint'
        dic['args'] = [{'rid': '{0}'.format(self.__conf['roomid'])}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'PondData'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'PondData{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'GroupColorInit'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'GroupColorInit{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'LiveTaskInit'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'LiveTaskInit{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'TaskRedPointCount'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'TaskRedPointCount{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'DailyTaskInit'
        t = int(time.time()*1000)
        dic['args'] = [{'t': 0, '_sid': 'DailyTaskInit{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

        dic.clear()
        dic['name'] = 'subscribe'
        dic['args'] = [{'isSub': 'false', 'msgName': 'BubbleUserList'}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.__ws.send(data)

    def onEnterMsg(self, arguments):
        " Response to enter message."

        body = arguments['body']
        n = body['n']
        # r = self.__conf['roomid']
        oms = body['oms']

        # not self enter
        if self.__conf['uid'] == str(body['i']):
            return

        # roal level
        l = body['l']
        # consumer-quality
        cq = None
        # activity level
        al = None
        # room manager
        rm = None
        for i in oms:
            if str(i) not in self.__medal:
                return
            medal = self.__medal[str(i)]
            if medal['medalType'] == 10:
                cq = int(medal['medalUrl'][-6: -4])
            elif medal['medalType'] == 7:
                al = int(medal['medalUrl'][-6: -4])
            elif medal['medalType'] == 6:
                rm = int(medal['medalUrl'][-6: -4])
            else:
                pass

        if rm and rm > 0:
            self.__ws.send(self.genMessage(self.welManager.format(n)))
        elif (cq and cq > 0) or (al and al > 0):
            self.__ws.send(self.genMessage(self.welFans.format(n)))
        elif l >= 10:
            msg = self.welVisitor[random.randint(0, len(self.welVisitor)-1)]
            self.__ws.send(self.genMessage(msg.format(n)))
        '''
        msg = self.welVisitor[random.randint(0, len(self.welVisitor)-1)]
        self.__ws.send(self.genMessage(msg.format(n)))
        '''

    def onChatMsg(self, arguments):
        " Response to chat message."

        body = arguments['body']
        '''
        uid = arguments['uid']
        name = body['n']
        '''
        msg = body['m']
        if self.__conf['roomid'] == '615943':
            if re.search(self.__qqkey, msg, re.I):
                self.__ws.send(self.genMessage(self.__qqmsg))

    def onChatResponse(self, arguments):
        " Record the failed chat message."

        body = arguments['body']

        # send failed
        if body['cd'] != 0:
            self.__logger.error(json.dumps(arguments))

    def onAttention(self, arguments):
        " Response to attention message."

        body = arguments['body']
        fanName = body['fanName']
        self.__ws.send(self.genMessage(self.__attentionMsg.format(fanName)))

    def onSendstar(self, arguments):
        " Response to star message."

        body = arguments['body']
        q = body['q']
        n = body['n']
        i = body['i']
        msg = None
        if 10 == q:
            msg = '感谢 {0} 星动[鼓掌]'
        elif 50 == q:
            msg = '感谢 {0} 满天星[鼓掌]'
        else:
            msg = '感谢 {0} 小星星[鼓掌]'

        # not self send and not last sender
        if (self.__conf['uid'] != str(i)) and (self.__lastSendstar != n):
            self.__ws.send(self.genMessage(msg.format(n)))
            self.__lastSendstar = n

    def onSendgift(self, arguments):
        " Response to gift message."

        body = arguments['body']
        g = body['g']

        if str(g) not in self.__gift:
            return
        gift = self.__gift[str(g)]['name']
        n = body['n']
        i = body['i']

        # not self send and not lastgift
        if self.__conf['uid'] != str(i) and self.__lastGift != (str(i)+str(g)):
            self.__ws.send(self.genMessage(self.__giftMsg.format(n, gift)))
            self.__lastGift = str(i) + str(g)     # sender and gift

    def genMessage(self, msg):
        " Generate data to send."

        data = {}
        args = [{}]
        args[0]['ai'] = '0'
        args[0]['r'] = self.__conf['roomid']
        args[0]['_sid'] = 'Chat{0}'.format(str(int(time.time()*1000)))
        args[0]['m'] = msg
        data['name'] = 'Chat'
        data['args'] = args
        return '5:::{0}'.format(json.dumps(data))

    def onError(self, ws, error):
        " The callback func when ws occur errors."

        self.__logger.error(error)

    def onClose(self, ws):
        " The callback func when ws occur close."

        # must stop timer firstly
        if self.__timerLive:
            self.__timerLive.cancel()
        if self.__timerMsg:
            self.__timerMsg.cancel()
        if self.__timerCao:
            self.__timerCao.cancel()

        if self.__driver:
            self.__driver.close()
            self.__driver.quit()

        self.__logger.info('Close ws successed.')

    def onOpen(self, ws):
        " The callback func when ws occur open."

        self.__logger.info('Connect success Roomid:{0}.'.format(self.__roomid))

    def dealPage(self):
        " Deal the html page to get some info."

        driver = self.__driver
        pat = re.compile("DDS.baseInfo = ({.*?});")
        roomInfo = pat.search(self.page, re.S).group(1)
        pat = re.compile('isShowing:(.*?),')
        isShowing = pat.search(roomInfo, re.S).group(1)
        isPushHis = '1' if isShowing.lower() == 'true' else '0'

        pat = re.compile('DDS.userInfo = ({.*?});')
        userInfo = pat.search(self.page, re.S).group(1)
        pat = re.compile('userId:(.*?),')
        userid = pat.search(userInfo, re.S).group(1)

        pat = re.compile("host:'(.*?)',")
        wurl = pat.search(roomInfo, re.S).group(1) +\
            '/{0}?isIgnoreDefaultPort=true'.format(self.__roomid)
        pat = '{"host":"(.+)"}'
        ws_host = re.search(pat, urllib2.urlopen(wurl).read()).group(1)

        mk = driver.get_cookie('mk')['value'].encode('utf8')
        tk = urllib.unquote(driver.get_cookie('imk')['value'].encode('utf8'))
        yk = driver.get_cookie('yktk')
        yktk = yk['value'].encode('utf8') if yk else ''

        if self.__roomid:
            self.__conf['roomid'] = self.__roomid
        self.__conf['uid'] = userid
        self.__conf['token'] = tk
        self.__conf['mk'] = mk
        self.__conf['isPushHis'] = isPushHis
        self.__conf['yktk'] = yktk
        self.__conf['ws_host'] = ws_host

    def openWebsocket(self):
        " Connect to the laifeng websocket."

        try:
            websocket.enableTrace(True)
            wsurl = 'ws://{0}/socket.io/1/websocket/'.\
                    format(self.__conf['ws_host'])
            self.__ws = websocket.WebSocketApp(wsurl)
            self.__ws.on_message = self.on_message
            self.__ws.on_open = self.onOpen
            self.__ws.on_close = self.onClose
            self.__ws.on_error = self.onError
            self.__ws.run_forever()
        except:
            self.__logger.error(traceback.format_exc())

    def run(self):
        " Run the LFRobot."
        self.init()
        self.__logger.info('Start laifengRobot...')
        self.openWebsocket()

    def quit(self, signum, frame):
        " Callback when type ctrl+c."

        self.__ws.close()
        self.__logger.info('Stop the robot by close the ws.')


if __name__ == '__main__':
    robot = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        robot = LFRobot(sys.argv[1])
    else:
        robot = LFRobot()

    # catch the terminal signal
    signal.signal(signal.SIGINT, robot.quit)
    signal.signal(signal.SIGTERM, robot.quit)

    robot.run()
