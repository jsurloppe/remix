from remix import sessions


class HttpBin(sessions.RemixSession):
    base_url = "http://httpbin.org"
