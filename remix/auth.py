"""Some requests auth classes."""

from requests import auth


class TokenAuth(auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = "Token %s" % self.token
        return r


class XTokenAuth(TokenAuth):
    def __call__(self, r):
        r.headers["X-Auth-Token"] = self.token
        return r


class BearerAuth(TokenAuth):
        def __call__(self, r):
            r.headers["Authorization"] = "Bearer %s" % self.token
            return r
