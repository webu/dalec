from dalec.proxy import Proxy


class AdiposianProxy(Proxy):
    """
    Bad because does not overide `_fetch` method and so, is useless
    """

    app = "adiposian"
