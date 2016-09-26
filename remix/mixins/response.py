import io

from PIL import Image

Image.preinit()


class ContentResponseMixin(object):
    def process_response(self, response):
        return response.content


class JSONResponseMixin(object):
    def process_response(self, response):
        return response.json()


class ImageResponseMixin(object):
    def process_response(self, response):
        io_buffer = io.BytesIO(response.content)
        return Image.open(io_buffer)


class MagicResponseMixin(object):
    _content_types_mixins = dict({
        "application/json": JSONResponseMixin,
    }, **dict.fromkeys(Image.MIME.values(), ImageResponseMixin))

    def process_response(self, response):
        content_type = response.headers.get("Content-Type").split(';')[0]
        klass = self._content_types_mixins.get(content_type, ContentResponseMixin)
        return klass.process_response(self, response)
