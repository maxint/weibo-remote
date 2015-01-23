# coding: utf-8
__author__ = 'maxint'

import BaseHTTPServer
import weibo
import urlparse
import pprint
import json
import logging

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


class Main():
    def __init__(self, username, passwd):
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

    def store(self):
        s = json.dumps(dict(
            since_id=self.since_id,
        ))
        open(DATA_FILE, 'wt').write(s)

    def do(self):
        mentions = self.wb.statuses_mentions()
        ids = self.wb.statuses_mentions_ids(since_id=self.since_id) or {}
        for id in ids.get('statuses', []):
            s = self.wb.statuses_show(id)
            if s:
                self.process(s['id'], s['text'], s['user']['name'])

    def safe_do(self):
        try:
            while True:
                self.do()
                # TODO: sleep
                break
        finally:
            self.store()

    def process(self, id, text, user):
        log.info('User: %s, Id: %s, Content: %s', user, id, text)
        def comment(content):
            self.wb.comments_create(content, id)

        if user == 'maxint':
            if u'打卡' in text or 'checkin' in text or 'check' in text:
                log.info('check in')
                import checkin
                r, msg = checkin.checkin(self.username, self.passwd)
                log.info(str(msg))
                comment(u'成功啦！' if r else u'出错啦！' + msg)
            elif u'截图' in text:
                log.info('screen capture')

        #self.since_id = id


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


def usage():
    import sys
    print 'usage:', sys.argv[0], ' <username> <password>'

if __name__ == '__main__':
    enable_log(log, 'weibo.log')

    import sys
    if len(sys.argv) != 3:
        usage()
        sys.exit(-1)

    main = Main(sys.argv[1], sys.argv[2])
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