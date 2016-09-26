from remix import sessions
from remix.mixins import pagination


class GitHub(pagination.RFC5988PaginatorMixin,
             sessions.RemixSession):
    base_url = "https://api.github.com/"
