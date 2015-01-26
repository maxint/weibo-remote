# coding: utf-8
__author__ = 'maxint'

import BaseHTTPServer
import urlparse
import pprint
import json
import logging
import time
import datetime

import weibo


log = logging.getLogger('weibo')

TOKEN_FILE = '.token.json'
DATA_FILE = '.data.json'
PP = pprint.PrettyPrinter()


def enable_log(logger, logfile):
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger.setLevel(logging.DEBUG)

    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    fileHandler.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.DEBUG)
    logger.addHandler(consoleHandler)

    log.info("Running Weibo Client")


def pprint(m):
    PP.pprint(m)


def sleep_time():
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
        log.info('Login as master %s (weibo: %s)', username, master)
        self.username = username
        self.passwd = passwd
        self.debug = debug
        self.master = master
        self.changed = False

    def load(self):
        self.wb = weibo.load(TOKEN_FILE)
        self.httpd = None
        try:
            self.wb.statuses_mentions_ids()
        except:
            self.login(True)
        try:
            d = json.load(open(DATA_FILE, 'rt'))
        except:
            d = dict()
        self.since_id = d.get('since_id', 0)

    def login(self, forcelogin):
        self.wb = weibo.Weibo('3150443457', 'e9a369d1575e399cb1d06c0a79685e67')
        self.wb.authorize(forcelogin=forcelogin)
        log.info('Start HTTP Server')
        self.httpd = BaseHTTPServer.HTTPServer(('127.0.0.1', 8000),
                                               ServerRequestHandler)
        self.httpd.handle_request()
        while not self.authorized:
            pass
        self.httpd.server_close()
        self.httpd = None
        log.info('Close HTTP server')

    def close(self):
        if self.httpd:
            self.httpd.server_close()
            self.httpd = None

    def store(self):
        if self.changed:
            s = json.dumps(dict(
                since_id=self.since_id,
            ))
            open(DATA_FILE, 'wt').write(s)
            self.changed = False

    @property
    def authorized(self):
        return self.wb.oauth.authorized

    def run_once(self):
        # test expired token
        # raise weibo.WeiboException('{"error_code": 21315}')
        mentions = self.wb.statuses_mentions()
        ids = self.wb.statuses_mentions_ids(since_id=self.since_id) or {}
        for id in ids.get('statuses', []):
            s = self.wb.statuses_show(id)
            if s:
                self.process(s['idstr'], s['text'], s['user']['name'])
        self.store()

    def run(self):
        log.debug('Start main loop')
        while True:
            try:
                self.run_once()
            except weibo.WeiboException, ex:
                log.warn('Re-login as a weibo exception occured')
                if ex.msg.get('error_code', 0) not in [21315, 21327]:
                    raise
                self.login(False)
                log.warn('Continue after re-login')
            if self.debug:
                break
            time.sleep(sleep_time())

    def save_run(self):
        try:
            self.run()
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
            code = qs['code'][0]
            log.debug('Get response code: %s', code)
            main.wb.access_token(code)
            main.wb.store(TOKEN_FILE)
            self.echoHTML('''<html>
<head>
<meta charset="utf-8"/>
<title>OK</title>
<script type="text/javascript">
setTimeout(function(){
  window.close();
},1000);
</script>
</head>
<body>Succeed. This window may be closed automatically after 1s</body>
</html> ''')


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
    try:
        main.load()
        main.run()
    except KeyboardInterrupt:
        pass
    finally:
        main.close()