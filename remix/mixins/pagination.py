import re
import threading
from copy import deepcopy
from functools import partial

from . import request
from ..compat import cpu_count, queue


class Pagitator(object):
    def __init__(self, instance, *args, **kwargs):
        self._instance = instance
        self._args = list(args)
        self._kwargs = deepcopy(kwargs)

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self._args[1] is None:
            raise StopIteration

        args, kwargs = self._instance.pre_request_params(*self._args, **self._kwargs)
        response = self._instance.process_request(*args, **kwargs)
        self._args[1] = self._instance.get_next_url(response)
        return self._instance.process_response(response)


class PaginatorMixin(object):
    def get_next_url(self, response):
        raise NotImplementedError

    def request(self, *args, **kwargs):
        return Pagitator(self, *args, **kwargs)


class ConsumePaginatorMixin(object):
    def request(self, *args, **kwargs):
        paginator = super(ConsumePaginatorMixin, self).request(*args, **kwargs)
        return [page for page in paginator]


class RFC5988PaginatorMixin(PaginatorMixin):
    def get_next_url(self, response):
        try:
            return response.links["next"]["url"]
        except:
            return None


class RFC5988ThreadedPaginatorMixin(request.ThreadedRequestMixin):
    page_param = "page"
    pattern_last_page = re.compile(r"[&?]page=(\d+)")
    _sem = threading.Semaphore(cpu_count())

    def get_page_numbers(self, response):
        last_link = response.links["last"]["url"]
        return int(self.pattern_last_page.search(last_link).group(1))

    def get_next_url(self, nb_pages, method, url, **kwargs):
        params = kwargs.get("params", {})
        params.setdefault(self.page_param, 1)
        params[self.page_param] += 1
        if params[self.page_param] <= nb_pages:
            return self.get_url(url, params)

        return None, None

    def _enqueue(self, thread_queue, thread):
        thread_queue.put(thread.join())
        self._sem.release()

    def _request(self, thread_queue, max_iter, method, url, **kwargs):
        args, kwargs = self.pre_request_params(method, url, **kwargs)
        method, url = args
        response = self.process_request(method, url, **kwargs)

        nb_pages = self.get_page_numbers(response)
        thread_queue.put(self.process_response(response))

        url, params = self.get_next_url(nb_pages, method, url, **kwargs)
        kwargs.update(params=params)

        workers = []
        iterations = 1
        while url:
            if max_iter > 0 and iterations >= max_iter:
                break
            self._sem.acquire()
            thread = super(RFC5988ThreadedPaginatorMixin, self).request(method, url, **kwargs)
            worker = threading.Thread(target=self._enqueue, args=(thread_queue, thread))
            worker.start()
            workers.append(worker)
            url, params = self.get_next_url(nb_pages, method, url, **kwargs)
            kwargs.update(params=params)
            iterations += 1

        for worker in workers:
            worker.join()

        thread_queue.put(StopIteration)

    def request(self, *args, **kwargs):
        max_iter = kwargs.pop("max_iter", 0)
        thread_queue = queue.Queue(maxsize=cpu_count())
        target = partial(self._request, thread_queue, max_iter)
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.start()

        while True:
            response = thread_queue.get()
            thread_queue.task_done()
            if response is StopIteration:
                thread.join()
                break
            yield response
