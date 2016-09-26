__title__ = "remix"
__version__ = "0.1-dev"
__author__ = "Julien Surloppe"
__license__ = "New BSD"
__copyright__ = "Copyright 2016 Julien Surloppe"

from remix.sessions import remix as remix_instance, reminiscent  # noqa

head = remix_instance.head
get = remix_instance.get
post = remix_instance.post
patch = remix_instance.patch
put = remix_instance.put
delete = remix_instance.delete
options = remix_instance.options
