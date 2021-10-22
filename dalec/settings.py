import sys
from typing import Any


class AppSettings(object):
    def __init__(self):
        from django.conf import settings

        self.settings = settings

    def get_setting(
        self, setting: str, default: Any = None, raise_if_not_set: bool = False
    ) -> Any:
        """
        Return a DALEC_<setting> or it's default Value if not set or raise an Exception
        """
        setting = "DALEC_" + setting
        if not hasattr(self.settings, setting):
            if raise_if_not_set:
                raise ValueError(
                    "{setting} is required in your settings.py".format(setting=setting)
                )
            return default
        return getattr(self.settings, setting)

    def get_for(self, setting, app=None, content_type=None):
        settings = []
        if app:
            app = app.strip().upper()
            settings.append("%s_%s" % (app, setting))
            if content_type:
                content_type = content_type.replace("-", "_").strip().upper()
                settings.append("%s_%s_%s" % (app, content_type, setting))
            settings.reverse()
        for specific_setting in settings:
            try:
                return self.get_setting(specific_setting, raise_if_not_set=True)
            except ValueError:
                continue
        return getattr(self, setting)

    @property
    def NB_CONTENTS_KEPT(self):
        return self.get_setting("NB_CONTENTS_KEPT", 10)

    @property
    def AJAX_REFRESH(self):
        return self.get_setting("AJAX_REFRESH", True)

    @property
    def TTL(self):
        return self.get_setting("TTL", 900)

    @property
    def CONTENT_MODEL(self):
        model = self.get_setting("CONTENT_MODEL")
        if not model:
            if "dalec_prime" not in self.settings.INSTALLED_APPS:
                raise ValueError(
                    (
                        "You must define a {setting} in your settings or "
                        "use the default one by adding dalec_prime to your INSTALLED_APPS."
                    ).format(setting="DALEC_CONTENT_MODEL")
                )
            else:
                model = "dalec_prime.Content"
        return model

    @property
    def FETCH_HISTORY_MODEL(self):
        model = self.get_setting("FETCH_HISTORY_MODEL")
        if not model:
            if "dalec_prime" not in self.settings.INSTALLED_APPS:
                raise ValueError(
                    (
                        "You must define a {setting} in your settings or "
                        "use the default one by adding dalec_prime to your INSTALLED_APPS."
                    ).format(setting="DALEC_FETCH_HISTORY_MODEL")
                )
            else:
                model = "dalec_prime.FetchHistory"
        return model

    @property
    def CSS_FRAMEWORK(self):
        return self.get_setting("CSS_FRAMEWORK", None)


# Ugly? Guido recommends this himself ...
# http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
settings = AppSettings()
settings.__name__ = __name__
sys.modules[__name__] = settings
