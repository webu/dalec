from dalec.proxy import Proxy


class NiceDalek(Proxy):
    """
    Fetch all the nice daleks from the whole universe
    """

    app = "nice_dalek"

    def _fetch(self, *args, **kwargs):
        """
        Ahah common! Did you really think a nice Dalek can exist?
        """
        return dict()
