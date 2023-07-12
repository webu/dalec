from dalec.proxy import Proxy


class BadWolfProxy(Proxy):
    """
    Bad because it does not have a app name
    """

    def _fetch(self, *args, **kwargs):
        print("I can see everything. All that is. All that was. All that ever could be.")
