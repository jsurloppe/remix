
"""Everybody-hate-me module.

Always try to import for python 3, then fallback to 2.
"""

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse  # noqa

try:
    from os import cpu_count
except ImportError:
    cpu_count = lambda: 4  # noqa lol

try:
    import queue
except ImportError:
    import Queue as queue  # noqa
