import threading
from copy import deepcopy
from functools import reduce

from requests import exceptions

from remix import utils


class RaiseForStatusMixin(object):
    def process_request(self, *args, **kwargs):
        response = super(RaiseForStatusMixin, self).process_request(*args, **kwargs)
        response.raise_for_status()
        return response


class LoggerMixin(object):
    logger = None


class QueryLoggerMixin(LoggerMixin):
    def process_request(self, method, url, **kwargs):
        self.logger.info("%s: %s [%s]" % (method, url, kwargs))
        return super(QueryLoggerMixin, self).process_request(method, url, **kwargs)


class ReminiscentMixin(LoggerMixin,
                       RaiseForStatusMixin):
    cache_time = 604800
    reminiscent_methods = {}
    cold_cache = None

    def __init__(self, *args, **kwargs):
        super(ReminiscentMixin, self).__init__(*args, **kwargs)
        if self.cold_cache is None:
            raise utils.SettingsRequired

    def get_cache_key(self, method, url, cache_key=None, **kwargs):
        if not cache_key:
            cache_key = "%s %s" % (method.upper(), url)

            params = kwargs.get("params", {})
            if params:
                cache_key += reduce(("%s:%s" % (key, params[key]) for key in sorted(params)), ' ')

        return cache_key

    def memento_mori(self, method, url, cache_key=None, **kwargs):
        cache_key = self.get_cache_key(method, url, cache_key, **kwargs)

        try:
            response = super(ReminiscentMixin, self).process_request(method, url, **kwargs)
            self._tdata.response_cache_key = cache_key

            return response
        except exceptions.RequestException as ex:
            cached = self.cold_cache.get(cache_key)

            if cached:
                if self.logger:
                    self.logger.warning("Reminiscence for: %s [%d]" % (ex.request.url, ex.response.status_code))
                return cached
            raise

    def process_request(self, method, url, cache_key=None, **kwargs):
        def clean_url(url):
            return url.replace(self.base_url or '', '').strip('/')

        self._tdata.response_cache_key = None
        if bool(method in self.reminiscent_methods and
                any((pattern.match(clean_url(url)) for pattern in self.reminiscent_methods[method]))):
            return self.memento_mori(method, url, cache_key, **kwargs)

        return super(ReminiscentMixin, self).process_request(method, url, **kwargs)

    def process_response(self, response):
        if self._tdata.response_cache_key:
            self.cold_cache.set(self._tdata.response_cache_key, response, self.cache_time)

        return super(ReminiscentMixin, self).process_response(response)


class CacheMixin(ReminiscentMixin):
    prefer_cache_key_suffix = ":prefercache"
    prefer_cache_time = 3600
    hot_cache = None

    def __init__(self, *args, **kwargs):
        super(CacheMixin, self).__init__(*args, **kwargs)
        if self.hot_cache is None:
            raise utils.SettingsRequired

    def process_request(self, method, url, cache_key=None, force_cache_regen=False, **kwargs):
        cache_key = self.get_cache_key(method, url, cache_key, **kwargs)
        self._tdata.prefer_cache_key = cache_key + self.prefer_cache_key_suffix

        if not force_cache_regen and self.hot_cache.get(self._tdata.prefer_cache_key):
            return self.cold_cache.get(cache_key)
        return super(CacheMixin, self).process_request(method, url, **kwargs)

    def process_response(self, response):
        response = super(CacheMixin, self).process_response(response)

        if self._tdata.response_cache_key:
            self.hot_cache.set(self._tdata.prefer_cache_key, True, self.prefer_cache_time)

        return response


class MiniThread(threading.Thread):
    # TODO: useless in python 3
    def __init__(self, target, args, kwargs, *targs, **tkwargs):
        super(MiniThread, self).__init__(target=target, args=args, kwargs=kwargs, *targs, **tkwargs)
        self._target = target
        self._args = deepcopy(args)
        self._kwargs = deepcopy(kwargs)

    def run(self):
        self.target_response = self._target(*self._args, **self._kwargs)

    def join(self):
        super(MiniThread, self).join()
        return self.target_response


class ThreadedRequestMixin(object):
    def request(self, *args, **kwargs):
        target = super(ThreadedRequestMixin, self).request
        thread = MiniThread(target=target, args=args, kwargs=kwargs)
        thread.start()
        return thread
