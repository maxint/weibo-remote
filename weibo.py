# coding: utf-8
__author__ = 'maxint'

import json
import logging

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import WebApplicationClient


log = logging.getLogger('weibo')

API_HOST = 'https://api.weibo.com/'


class WeiboException(Exception):
    def __init__(self, text):
        try:
            self.msg = json.loads(text)
        except:
            self.msg = dict(error=text)

    def __str__(self):
        return repr(self.msg)


class Weibo():
    def __init__(self, client_id, client_secret, token=None):
        self.oauth = OAuth2Session(redirect_uri='http://127.0.0.1:8000/response',
                                   token=token,
                                   client=WebApplicationClient(client_id=client_id,
                                                               token=token,
                                                               default_token_placement='query'))
        self.client_secret = client_secret

    def url(self, subpath):
        return API_HOST + subpath

    def authorize(self, **kwargs):
        url, _ = self.oauth.authorization_url(self.url('oauth2/authorize'), **kwargs)
        import webbrowser

        webbrowser.open(url)

    def access_token(self, code):
        self.oauth.fetch_token(token_url=self.url('oauth2/access_token'),
                               code=code,
                               client_secret=self.client_secret)

    def store(self, filename):
        s = json.dumps(dict(
            client_id=self.oauth.client_id,
            client_secret=self.client_secret,
            token=self.oauth._client.token,
        ), indent=2)
        open(filename, 'wt').write(s)

    def request(self, method, subpath, **kwargs):
        req = self.oauth.request(method, self.url(subpath), **kwargs)
        if req.ok:
            return json.loads(req.text)
        else:
            log.error(req.text)
            raise WeiboException(req.text)

    def get(self, subpath, **kwargs):
        return self.request('GET', subpath, **kwargs)

    def post(self, subpath, **kwargs):
        return self.request('POST', subpath, **kwargs)

    def users_show(self, **kwargs):
        '''@screen_name or @uid'''
        return self.get('2/users/show.json', params=kwargs)

    def comments_mentions(self):
        return self.get('2/comments/mentions.json')

    def comments_create(self, comment, id):
        return self.post('2/comments/create.json',
                         data=dict(comment=comment,
                                   id=id))

    def statuses_mentions(self, **kwargs):
        '''@since_id, @count'''
        return self.get('2/statuses/mentions.json', params=kwargs)

    def statuses_mentions_ids(self, **kwargs):
        return self.get('2/statuses/mentions/ids.json', params=kwargs)

    def statuses_show(self, id):
        return self.get('2/statuses/show.json',
                        params=dict(id=id))


def load(filename):
    '''Return None if loading failed'''
    import os.path
    if os.path.isfile(filename):
        d = json.load(open(filename, 'rt'))
        return Weibo(d['client_id'], d['client_secret'], d['token'])