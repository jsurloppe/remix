"""Remix core."""

import copy
import re
import threading

from requests import sessions

from remix import __version__

from . import utils
from .compat import urlparse
from .mixins import request, response


class BaseRemixSession(sessions.Session):
    base_url = None
    auth = None
    trailing_slash = False
    headers = {
        "User-Agent": "python-remix/%s" % __version__
    }

    def __init__(self, base_url=None, auth=None, trailing_slash=False, headers=None):
        self._tdata = threading.local()

        cls_headers = copy.copy(self.headers)
        cls_auth = copy.copy(self.auth)

        super(BaseRemixSession, self).__init__()

        self.base_url = base_url or self.base_url
        self.auth = auth or cls_auth
        self.trailing_slash = trailing_slash or self.trailing_slash
        self.headers.update(headers or cls_headers)

    def get_url(self, url, params=None):
        url_split = urlparse.urlsplit(url)
        # fully qualified url, don't alter
        if url_split.scheme:
            params = params or {}
            query_params = urlparse.parse_qs(url_split.query)
            params.update(query_params)
            return urlparse.urlunsplit((url_split.scheme, url_split.netloc, url_split.path, '', '')), params

        if url.startswith('/'):
            url = url.lstrip('/')

        if self.trailing_slash and not url.endswith('/'):
            url += '/'

        return urlparse.urljoin(self.base_url, url), params

    def pre_request_params(self, method, url, **kwargs):
        params = kwargs.get("params")
        url, params = self.get_url(url, params)
        kwargs.update(params=params)
        return (method, url), kwargs

    def request(self, *args, **kwargs):
        args, kwargs = self.pre_request_params(*args, **kwargs)
        response = self.process_request(*args, **kwargs)
        return self.process_response(response)

    def process_request(self, *args, **kwargs):
        return super(BaseRemixSession, self).request(*args, **kwargs)

    def process_response(self, response):
        return response


class RemixSession(request.RaiseForStatusMixin,
                   response.MagicResponseMixin,
                   response.ContentResponseMixin,  # python2 compat
                   response.ImageResponseMixin,  # python2 compat
                   response.JSONResponseMixin,  # python2 compat
                   BaseRemixSession):
    pass


class ReminiscentSession(request.ReminiscentMixin, RemixSession):
    cold_cache = utils.CacheDict()
    reminiscent_methods = {
        "GET": [re.compile(r".*")]
    }

remix = RemixSession()
reminiscent = ReminiscentSession()
