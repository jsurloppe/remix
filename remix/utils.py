"""You kwow, a little of this, a little of that."""


class CacheDict(dict):
    def get(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def set(self, key, value, time):
        self[key] = value


class SettingsRequired(RuntimeWarning):
    pass
