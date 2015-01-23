# coding: utf-8
__author__ = 'maxint'

import BaseHTTPServer
import weibo
import urlparse
import pprint
import json
import logging
import time

log = logging.getLogger('weibo')

CACHED_FILE = '.token.json'
DATA_FILE = '.data.json'
PP = pprint.PrettyPrinter()


def enable_log(loger, logfile):
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    loger.setLevel(logging.DEBUG)

    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    fileHandler.setLevel(logging.DEBUG)
    loger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.DEBUG)
    loger.addHandler(consoleHandler)

    log.info("Running Weibo Client")


def pprint(m):
    PP.pprint(m)


def sleep_time():
    import datetime
    now = datetime.datetime.now()
    h = now.hour
    m = now.minute
    s = now.second
    if h == 8 and m > 30:
        if m < 50:
            return 30
        elif m < 55:
            return 20
        elif m < 58:
            return 10
        else:
            return 1
    else:
        return 60


class Main():
    def __init__(self, username, passwd, debug=False, master='maxint'):
        try:
            self.wb = weibo.load(CACHED_FILE)
        except:
            self.wb = weibo.Weibo('3150443457', 'e9a369d1575e399cb1d06c0a79685e67')
            self.wb.authorize()
        try:
            d = json.load(open(DATA_FILE, 'rt'))
        except:
            d = dict()
        self.since_id = d.get('since_id', 0)
        self.username = username
        self.passwd = passwd
        self.debug = debug
        self.master = master
        self.changed = False

    def store(self):
        if self.changed:
            s = json.dumps(dict(
                since_id=self.since_id,
            ))
            open(DATA_FILE, 'wt').write(s)
            self.changed = False

    def do(self):
        mentions = self.wb.statuses_mentions()
        ids = self.wb.statuses_mentions_ids(since_id=self.since_id) or {}
        for id in ids.get('statuses', []):
            s = self.wb.statuses_show(id)
            if s:
                self.process(s['idstr'], s['text'], s['user']['name'])

    def safe_do(self):
        try:
            while True:
                self.do()
                self.store()
                if self.debug:
                    break
                time.sleep(sleep_time())
        finally:
            self.store()

    def weibo_comment(self, content, id):
        self.wb.comments_create(content, id)

    def checkin(self, id, text, user):
        import checkin
        log.info('== checkin')
        ss = text.split()
        if len(ss) >= 4:
            username = ss[-2]
            passwd = ss[-1]
        elif user == self.master:
            username = self.username
            passwd = self.passwd
        else:
            log.info('invalid parameters')
            self.weibo_comment(u'usage: checkin username passwd', id)
            return

        log.info("%s, %s", username, passwd)
        r, msg = checkin.checkin(username, passwd)
        log.info(str(msg))
        self.weibo_comment(u'成功啦[呵呵]' if r else u'出错啦[泪]' + msg, id)

    def process(self, id, text, user):
        log.info('User: %s, Id: %s, Content: %s', user, id, text)
        def comment(content):
            self.wb.comments_create(content, id)

        if user == self.master:
            if u'打卡' in text or 'checkin' in text or 'check' in text:
                self.checkin(id, text, user)
            elif u'截图' in text:
                log.info('== screen capture')
                comment(u'还不支持本操作[衰]')
            else:
                log.error('unknown operation')
                comment(u'还不支持本操作[衰]')
        else:
            if u'打卡' in text or 'checkin' in text or 'check' in text:
                self.checkin(id, text, user)
            else:
                log.error('unknown operation')
                comment(u'还不支持本操作[衰]')

        self.since_id = id
        self.changed = True


class ServerRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def echoHTML(self, content):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(content)
        self.wfile.close()

    def do_GET(self):
        qs = urlparse.parse_qs(urlparse.urlsplit(self.path).query)
        if 'code' in qs:
            main.wb.access_token(qs['code'][0])
            main.wb.store(CACHED_FILE)
            main.safe_do()
            self.echoHTML('OK')
            httpd.server_close()


if __name__ == '__main__':
    enable_log(log, 'weibo.log')

    import argparse
    parser = argparse.ArgumentParser(description='weibo client of a computer')
    parser.add_argument('username', help='user name of doc-server')
    parser.add_argument('password', help='password of doc-server')
    parser.add_argument('--debug', '-D', action='store_true',
                        help='enable debug')
    parser.add_argument('--master', default='maxint',
                        help='weibo master')

    args = parser.parse_args()

    main = Main(args.username, args.password, args.debug, args.master)
    if main.wb.oauth.authorized:
        main.safe_do()
    else:
        host = '127.0.0.1'
        port = 8000
        httpd = BaseHTTPServer.HTTPServer((host, port), ServerRequestHandler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()