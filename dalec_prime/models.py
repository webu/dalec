# DALEC imports
from dalec.models import ContentBase
from dalec.models import FetchHistoryBase

__all__ = ["Content", "FetchHistory"]


class Content(ContentBase):
    pass


class FetchHistory(FetchHistoryBase):
    pass
