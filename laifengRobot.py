#!/usr/bin/env python
# -*-coding:utf8 -*-

import websocket
import urllib
import urllib2
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

    def __init__(self, roomid=None):
        self.roomid = roomid
        self.ws = None
        self.driver = None
        self.conf = {}              # data dic for connecting server
        self.lastSendstar = None    # last star sender
        self.lastGift = None        # last gift and sender
        self.logfile = 'laifeng.log'
        self.timerMsg = None

    def getConfig(self):
        " Update configure."

        cp = ConfigParser.SafeConfigParser()
        cp.read('laifeng.conf')
        # the configure when connect websocket
        if self.roomid:
            self.conf['roomid'] = self.roomid
        else:
            self.roomid = self.conf['roomid'] = cp.get('laifeng', 'roomid')
        self.conf['uid'] = cp.get('laifeng', 'userid')
        self.conf['token'] = cp.get('laifeng', 'token')
        self.conf['mk'] = cp.get('laifeng', 'mk')
        self.conf['yktk'] = cp.get('laifeng', 'yktk')
        self.conf['isPushHis'] = cp.get('laifeng', 'isPushHis')
        self.conf['ws_host'] = cp.get('laifeng', 'ws_host')
        self.url = cp.get('laifeng', 'url')
        # welcome msg list
        self.welMsg = cp.get('msg', 'welMsg').split('|')
        # message list when live
        self.msgs = cp.get('msg', 'msgs').split('|')
        # thank msg when get attentions
        self.attentionMsg = cp.get('msg', 'attentionMsg')
        # thank msg when get gifts
        self.giftMsg = cp.get('msg', 'giftMsg')
        # timer interval when live
        self.msgInterval = int(cp.get('msg', 'msgInterval'))
        # medal dictionary
        self.medal = json.loads(cp.get('dic', 'medal'))
        # gift dictionary
        self.gift = json.loads(cp.get('dic', 'gift'))

    def getLogger(self):
        # config logging
        logger = logging.getLogger()
        f = logging.FileHandler(self.logfile)
        logger.addHandler(f)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(filename)s\
                                      %(lineno)d %(message)s")
        f.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        self.logger = logger

    def TimerMessage(self):
        " Timer to send random message."

        index = random.randint(0, len(self.msgs)-1)
        if self.ws:
            self.ws.send(self.genMessage(self.msgs[index]))
        self.timerMsg = threading.Timer(self.msgInterval, self.TimerMessage)
        self.timerMsg.start()

    def on_message(self, ws, message):
        " Response to websocket message."

        if "1:::" == message:
            self.onInitMsg()
        elif "2:::" == message:
            ws.send("2::")
        elif "5:::" in message:
            dic = json.loads(message[4:])
            mType = dic['name']
            args = dic['args'][0]
            if 'result' == mType:
                # '1':success
                if '1' == args['code']:
                    self.TimerMessage()
            elif 'enterMessage' == mType:
                self.onEnterMsg(args)
            elif 'chatMessage' == mType:
                # self.onChatMsg(args)
                pass
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
        dic['token'] = self.conf['token']
        dic['uid'] = self.conf['uid']
        dic['roomid'] = self.conf['roomid']
        dic['isPushHis'] = self.conf['isPushHis']
        dic['yktk'] = ''
        dic['endpointtype'] = "ct_, dt_1_1000|0|{0}_{1}".\
            format(self.conf['mk'], int(time.time()*1000))
        dic_data = {'name': 'enter', 'args': [dic]}
        data = '5:::{0}'.format(json.dumps(dic_data))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'PatronSaint'
        dic['args'] = [{'rid': '{0}'.format(self.conf['roomid'])}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'PondData'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'PondData{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'GroupColorInit'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'GroupColorInit{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'LiveTaskInit'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'LiveTaskInit{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'TaskRedPointCount'
        t = int(time.time()*1000)
        dic['args'] = [{'_sid': 'TaskRedPointCount{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'DailyTaskInit'
        t = int(time.time()*1000)
        dic['args'] = [{'t': 0, '_sid': 'DailyTaskInit{0}'.format(t)}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)
        dic.clear()
        dic['name'] = 'subscribe'
        dic['args'] = [{'isSub': 'false', 'msgName': 'BubbleUserList'}]
        data = '5:::{0}'.format(json.dumps(dic))
        self.ws.send(data)

    def onEnterMsg(self, arguments):
        " Response to enter message."

        body = arguments['body']
        n = body['n']
        r = self.conf['roomid']
        oms = body['oms']
        # no msg when self enter
        if self.conf['uid'] == str(body['i']):
            return
        # medal level
        l = body['l']
        # consumer-quality | light
        cq = None
        # activity level    | leaves
        al = None
        # room manager
        rm = None
        for i in oms:
            if str(i) not in self.medal:
                return
            medal = self.medal[str(i)]
            if medal['medalType'] == 10:
                cq = int(medal['medalUrl'][-6: -4])
            elif medal['medalType'] == 7:
                al = int(medal['medalUrl'][-6: -4])
            elif medal['medalType'] == 6:
                rm = int(medal['medalUrl'][-6: -4])
            else:
                pass
        if (rm and rm > 0) or (cq and cq > 0) or (l >= 1) or (al > 0):
            msg = self.welMsg[random.randint(0, len(self.welMsg)-1)]
            self.ws.send(self.genMessage(msg.format(n, r)))

    def onChatMsg(self, arguments):
        " Response to chat message."
        pass

    def onChatResponse(self, arguments):
        " Record the failed chat message."

        body = arguments['body']
        # send failed
        if body['cd'] != 0:
            self.logger.error(json.dumps(arguments))

    def onAttention(self, arguments):
        " Response to attention message."

        body = arguments['body']
        fanName = body['fanName']
        self.ws.send(self.genMessage(self.attentionMsg.format(fanName)))

    def onSendstar(self, arguments):
        " Response to star message."

        body = arguments['body']
        q = body['q']
        n = body['n']
        i = body['i']
        l = body['l']
        msg = None
        if 10 == q:
            msg = '感谢 {0} 星动[鼓掌]'
        elif 50 == q:
            msg = '感谢 {0} 满天星[鼓掌]'
        else:
            msg = '感谢 {0} 小星星[鼓掌]'
        # not self send and not last sender
        '''
        if (self.conf['uid'] != str(i)) and (self.lastSendstar != n) \
           and l > 0:
        '''
        self.ws.send(self.genMessage(msg.format(n)))
        # self.lastSendstar = n

    def onSendgift(self, arguments):
        " Response to gift message."

        body = arguments['body']
        g = body['g']
        if str(g) not in self.gift:
            return
        gift = self.gift[str(g)]['name']
        n = body['n']
        i = body['i']
        # not self send and not lastgift
        # if self.conf['uid'] != str(i) and self.lastGift != (str(i)+str(g)):
        self.ws.send(self.genMessage(self.giftMsg.format(n, gift)))
        # self.lastGift = str(i) + str(g)     # sender and gift

    def genMessage(self, msg):
        " Generate data to send."

        data = {}
        args = [{}]
        args[0]['ai'] = '0'
        args[0]['r'] = self.conf['roomid']
        args[0]['_sid'] = 'Chat{0}'.format(str(int(time.time()*1000)))
        args[0]['m'] = msg
        data['name'] = 'Chat'
        data['args'] = args
        return '5:::{0}'.format(json.dumps(data))

    def onError(self, ws, error):
        " The callback func when ws occur errors."

        self.logger.error(error)

    def onClose(self, ws):
        " The callback func when ws occur close."

        # must stop timer firstly
        if self.timerMsg:
            self.timerMsg.cancel()
        if self.driver:
            self.driver.close()
            self.driver.quit()
        self.logger.info('Close ws successed.')

    def onOpen(self, ws):
        " The callback func when ws occur open."

        self.logger.info('Connect success Roomid:{0}.'.format(self.roomid))

    def dealPage(self):
        " Deal the html page to get some info."

        driver = self.driver
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
            '/{0}?isIgnoreDefaultPort=true'.format(self.roomid)
        pat = '{"host":"(.+)"}'
        ws_host = re.search(pat, urllib2.urlopen(wurl).read()).group(1)
        mk = driver.get_cookie('mk')['value'].encode('utf8')
        tk = urllib.unquote(driver.get_cookie('imk')['value'].encode('utf8'))
        yk = driver.get_cookie('yktk')
        yktk = yk['value'].encode('utf8') if yk else ''
        if self.roomid:
            self.conf['roomid'] = self.roomid
        self.conf['uid'] = userid
        self.conf['token'] = tk
        self.conf['mk'] = mk
        self.conf['isPushHis'] = isPushHis
        self.conf['yktk'] = yktk
        self.conf['ws_host'] = ws_host

    def openWebsocket(self):
        " Connect to the laifeng websocket."

        try:
            websocket.enableTrace(True)
            wsurl = 'ws://{0}/socket.io/1/websocket/'.\
                    format(self.conf['ws_host'])
            self.ws = websocket.WebSocketApp(wsurl)
            self.ws.on_message = self.on_message
            self.ws.on_open = self.onOpen
            self.ws.on_close = self.onClose
            self.ws.on_error = self.onError
            self.ws.run_forever()
        except:
            # traceback.print_exc()
            self.logger.error(traceback.format_exc())

    def run(self):
        " Run the LFRobot."
        self.getLogger()
        self.getConfig()
        self.logger.info('Start laifengRobot...')
        self.openWebsocket()

    def quit(self, signum, frame):
        " Callback when type ctrl+c."

        self.ws.close()
        self.logger.info('Stop the robot by close the ws.')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        robot = LFRobot(sys.argv[1])
    else:
        robot = LFRobot()
    # catch the terminal signal
    signal.signal(signal.SIGINT, robot.quit)
    signal.signal(signal.SIGTERM, robot.quit)
    robot.run()
