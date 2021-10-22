class EmptyChildProxy:
    """
    Bad because does not extends dalec.proxy.Proxy
    """

    app = "empty_child"

    def _fetch(self, *args, **kwargs):
        print("Are you my mummy?")
