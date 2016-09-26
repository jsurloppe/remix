import json
import pickle
import re
import threading
import time
from os import environ

import pytest
from httpbin import app as httpbin
from PIL.PngImagePlugin import PngImageFile
from requests import exceptions
from requests.auth import HTTPBasicAuth

from remix import sessions
from remix.clients import HttpBin
from remix.mixins import pagination, request

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from SimpleHTTPServer import SimpleHTTPRequestHandler as BaseHTTPRequestHandler
    from BaseHTTPServer import HTTPServer


HTTP_BIN_PORT = environ.get("HTTPBIN_PORT", 5000)
HTTP_SERVER = ("localhost", 8001)
PAGINATOR_SERVER = ("localhost", 8002)

HttpBin.base_url = "http://localhost:%d" % HTTP_BIN_PORT


class PaginatorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        server_address = "http://%s:%d" % (self.server.server_address)
        try:
            query_params = self.path.split('?')[1]
            page = int(query_params.split('=')[1])
        except IndexError:
            page = 1

        links = "<%s?page=20>; rel=\"last\"" % server_address
        if page < 20:
            links += ", <%s?page=%d>; rel=\"next\"" % (server_address, page + 1)

        data = {
            "page": page
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Link", links)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("ascii"))


class TimeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        str_time = str(int(time.time()))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(str_time.encode("ascii"))


class Peekaboo(dict):
    def get(self, key):
        try:
            return pickle.loads(self[key])
        except KeyError:
            return None

    def set(self, key, value, time):
        self[key] = pickle.dumps(value)

    def cheat(self, old_key, new_key):
        self[new_key] = self.pop(old_key)


def setup_module(module):
    httpbin_server = threading.Thread(target=httpbin.run, kwargs={"port": HTTP_BIN_PORT, "threaded": True})
    httpbin_server.daemon = True

    http_server = HTTPServer(HTTP_SERVER, TimeHandler)
    paginator_server = HTTPServer(PAGINATOR_SERVER, PaginatorHandler)
    http_server = threading.Thread(target=http_server.serve_forever)
    http_server.daemon = True
    paginator_server = threading.Thread(target=paginator_server.serve_forever)
    paginator_server.daemon = True

    http_server.start()
    paginator_server.start()
    httpbin_server.start()

    time.sleep(1)


def test_httpbin():
    httpbin = HttpBin()
    data = httpbin.get("get", params={"marty": "mcfly"})
    assert(isinstance(data, dict))
    assert(data["args"]["marty"] == "mcfly")


def test_httpbin_auth():
    httpbin = HttpBin()
    httpbin.auth = HTTPBasicAuth("marty", "mcfly")
    data = httpbin.get("basic-auth/marty/mcfly")
    assert(data["authenticated"] is True and data["user"] == "marty")


def test_httpbin_fail_auth():
    httpbin = HttpBin()
    httpbin.auth = HTTPBasicAuth("biff", "tannen")
    with pytest.raises(exceptions.HTTPError) as ex:
        httpbin.get("basic-auth/marty/mcfly")
        assert(ex.status_code == 401)


def test_httpbin_threaded():
    ThreadedBin = type("ThreadedBin", (request.ThreadedRequestMixin, HttpBin), {})
    httpbin = ThreadedBin()

    start_time = time.time()

    first = httpbin.get("delay/3?n=1")
    second = httpbin.get("delay/1?n=2")
    third = httpbin.get("delay/1?n=3")
    fourth = httpbin.get("get?n=4")

    assert(fourth.join()["args"]['n'] == '4')
    assert(second.join()["args"]['n'] == '2')
    assert(third.join()["args"]['n'] == '3')
    assert(first.join()["args"]['n'] == '1')

    time_elapsed = time.time() - start_time
    assert(3 < time_elapsed < 4)


def test_httpbin_image():
    httpbin = HttpBin()
    assert(isinstance(httpbin.get("image/png"), PngImageFile))


def test_reminiscence():
    reminiscent_methods = {
        "GET": (re.compile(r"get"), re.compile(r"status/500"))
    }

    cache = Peekaboo()

    ReminiscentBin = type("ReminiscentBin",
                          (request.ReminiscentMixin, HttpBin),
                          {
                              "cold_cache": cache,
                              "reminiscent_methods": reminiscent_methods,
                              "cache_time": 999
                          })
    rbin = ReminiscentBin()
    rbin.get("get?memento=mori")
    cache.cheat("GET " + HttpBin.base_url + "/get?memento=mori", "GET " + HttpBin.base_url + "/status/500")
    response = rbin.get("status/500")

    assert(response["args"]["memento"] == "mori")
    with pytest.raises(exceptions.HTTPError):
        response = rbin.get("status/503")


def test_cache():
    reminiscent_methods = {
        "GET": (re.compile(r".*"),)
    }

    cache = Peekaboo()

    CachedClient = type("CachedClient", (request.CacheMixin, sessions.RemixSession),
                        {"hot_cache": cache,
                         "cold_cache": cache,
                         "reminiscent_methods": reminiscent_methods,
                         "cache_time": 999})
    cc = CachedClient()
    r1 = cc.get("http://%s:%d" % HTTP_SERVER)
    time.sleep(2)
    r2 = cc.get("http://%s:%d" % HTTP_SERVER)
    assert(r1 == r2)


def test_paginator():
    Paginator = type("Paginator", (pagination.RFC5988PaginatorMixin, sessions.RemixSession), {})
    paginator = Paginator()
    it = paginator.get("http://%s:%d" % PAGINATOR_SERVER)
    page = 0
    for r in it:
        page += 1
        assert(r["page"] == page)

    assert(page == 20)


def test_all_your_base():
    Paginator = type("Paginator", (pagination.ConsumePaginatorMixin,
                                   pagination.RFC5988PaginatorMixin,
                                   sessions.RemixSession), {})
    paginator = Paginator()
    r = paginator.get("http://%s:%d" % PAGINATOR_SERVER)
    assert(len(r) == 20)
    assert(sum(e["page"] for e in r) == 20 * (20 + 1) / 2)


def test_serious_business():
    Paginator = type("Paginator", (pagination.ConsumePaginatorMixin,
                                   pagination.RFC5988ThreadedPaginatorMixin,
                                   sessions.RemixSession), {})
    paginator = Paginator()
    r = paginator.get("http://%s:%d" % PAGINATOR_SERVER)
    assert(len(r) == 20)
    assert(sum(e["page"] for e in r) == 20 * (20 + 1) / 2)
