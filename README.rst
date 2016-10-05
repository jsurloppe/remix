Remix: HTTP for Super Humans
============================

Remix is a collection of mixins for the requests library.

Remix aim to reduce the repetitions of common tasks with REST API,
making them more resilient and faster.

Features
--------
- Automatic deserialization to a natural response.
- Cache.
- Iterators from pagination.
- Async requests.

Tested on Python 2.7 and 3.4, need testing but probably work on more versions.

Basic example :

.. code-block:: python

    >>> import remix
    >>> remix.get("https://httpbin.org/get")
    {'args': {},
     'headers': {'Accept': '*/*',
     'Accept-Encoding': 'gzip, deflate',
     'Host': 'httpbin.org',
     'User-Agent': 'python-remix/0.1.0'},
     'origin': '127.0.0.1',
     'url': 'https://httpbin.org/get'}
    >>> remix.get("https://httpbin.org/image/png")
    <PIL.PngImagePlugin.PngImageFile image mode=RGB size=100x100 at 0x7FEEB6162630>

Simple and fun, now let's get serious.

Usually, if you recover data on a remote API, you need to cache responses due to the limited rate,
and you probably need to be sure that the remote endpoint is before emptying your cache, or you will not have the necessary data required for your process.
Rinse and repeat.

Remix has mixins for that, all you need is a cache object with an interface similar to a django cache object,
django.core.cache.backends.db.DatabaseCache is a pretty good fit.

Be careful here, by default, we store the answer in a dict, don't do this in production unless on what you do.
(Obviously, you don't need to implement the cheat method)



.. code-block:: python

    class Peekaboo(dict):
        def get(self, key):
            try:
                return self[key]
            except KeyError:
                return None

        def set(self, key, value, time):
            self[key] = value

        def cheat(self, old_key, new_key):
            self[new_key] = self.pop(old_key)

No let's replay some test:

.. code-block:: python

    >>> from remix import reminiscent
    >>> reminiscent.cold_cache = Peekaboo()
    # no magic here, first time query, service down, exception
    >>> reminiscent.get("https://httpbin.org/status/500")
    HTTPError: 500 Server Error: INTERNAL SERVER ERROR for url: https://httpbin.org/status/500
    >>> reminiscent.get("https://httpbin.org/get")
    {'args': {},
     'headers': {'Accept': '*/*',
     'Accept-Encoding': 'gzip, deflate',
     'Host': 'httpbin.org',
     'User-Agent': 'python-remix/0.1.0'},
     'origin': '127.0.0.1',
     'url': 'https://httpbin.org/get'}
    # let's cheat for this example
    >>> reminiscent.cold_cache.cheat("GET https://httpbin.org/get", "GET https://httpbin.org/status/500")
    >>> reminiscent.get("https://httpbin.org/status/500")
    {'args': {},
     'headers': {'Accept': '*/*',
     'Accept-Encoding': 'gzip, deflate',
     'Host': 'httpbin.org',
     'User-Agent': 'python-remix/0.1.0'},
     'origin': '127.0.0.1',
     'url': 'https://httpbin.org/get'}
    # we're safe :D

You can use CacheMixin for the classic return-cache-if-last-request-was-less-than-N-seconds.

Now that we no longer need to manage your query cache and rewrite ad nauseam controls, it's time for the real fun, paginators and async requests!

remix and reminiscent are only helpers, this project is a collection of mixins intented to be subclassed.
Make non blocking requests with httpbin:

.. code-block:: python

    >>> from remix.clients import HttpBin
    >>> from remix.mixins.request import ThreadedRequestMixin
    >>> tbin = type("ThreadedBin", (ThreadedRequestMixin, HttpBin), {})()
    >>> r1 = tbin.get("delay/20")
    >>> r2 = tbin.get("delay/3")
    >>> r2.join()
    {'args': {},
     'data': '',
     ...
     'url': 'http://httpbin.org/delay/1'}
    >>> r1.join()
    [...]

Classic thread interface, except response is returned on join.
Let's consume some iterators:

.. code-block:: python

    >>> from remix.clients import GitHub
    >>> github = GitHub()
    >>> it = github.get("gists", params={"per_page": 7})
    >>> it
    <remix.clients.github.GitHub at 0x7f1c25dfd320>
    >>> gists = next(it)
    >>> len(gists)
    7

Fast paginators; multithreaded generators that return results as fast as possible (so probably not in the original order):

.. code-block:: python

    class GitHub(pagination.RFC5988ThreadedPaginatorMixin,
                 sessions.RemixSession):
        base_url = "https://api.github.com/"

.. code-block:: python

    >>> github = GitHub()
    # max_iter limit the number of pages queried, default 0, no limit.
    >>> it = github.get("gists", params={"per_page": 4}, max_iter=3)
    >>> print(len(sum(it, [])))
    12


TODO:
*****
- Replace join() by lazy object.
- Implement reference django-rest-framework paginators.
- Stream response.
- More intuitive way to return either response or iterator.
- doc and docstrings.

While working on the above features, the current implementations may or not be modified, be careful when upgrading on the early releases.

Thanks to Kenneth Reitz and all the contributors for making the awesome requests lib.
