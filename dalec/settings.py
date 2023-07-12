# Future imports
from __future__ import annotations

# Standard libs
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Optional

# Standard libs
import sys

# Django imports
from django.conf import settings


def get_setting(
    setting: str, default: Optional[Any] = None, raise_if_not_set: bool = False
) -> Any:
    """
    Return a DALEC_<setting> or it's default Value if not set or raise an Exception
    """
    setting = "DALEC_" + setting
    if not hasattr(settings, setting):
        if raise_if_not_set:
            raise ValueError("{setting} is required in your settings.py".format(setting=setting))
        return default
    return getattr(settings, setting)


def get_for(
    setting: str,
    app: Optional[str] = None,
    content_type: Optional[str] = None,
    default: Optional[Any] = None,
    raise_if_not_set: bool = False,
) -> Any:
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
            return get_setting(specific_setting, raise_if_not_set=True)
        except ValueError:
            continue
    if raise_if_not_set:
        return getattr(sys.modules[__name__], setting)
    return getattr(sys.modules[__name__], setting, None)


CSS_FRAMEWORK = get_setting("CSS_FRAMEWORK", None)
NB_CONTENTS_KEPT = get_setting("NB_CONTENTS_KEPT", 10)
AJAX_REFRESH = get_setting("AJAX_REFRESH", True)
TTL = get_setting("TTL", 900)

CONTENT_MODEL = get_setting("CONTENT_MODEL")
if not CONTENT_MODEL:
    if "dalec_prime" not in settings.INSTALLED_APPS:
        raise ValueError(
            (
                "You must define a {setting} in your settings or "
                "use the default one by adding dalec_prime to your INSTALLED_APPS."
            ).format(setting="DALEC_CONTENT_MODEL")
        )
    else:
        CONTENT_MODEL = "dalec_prime.Content"

FETCH_HISTORY_MODEL = get_setting("FETCH_HISTORY_MODEL")
if not FETCH_HISTORY_MODEL:
    if "dalec_prime" not in settings.INSTALLED_APPS:
        raise ValueError(
            (
                "You must define a {setting} in your settings or "
                "use the default one by adding dalec_prime to your INSTALLED_APPS."
            ).format(setting="DALEC_FETCH_HISTORY_MODEL")
        )
    else:
        FETCH_HISTORY_MODEL = "dalec_prime.FetchHistory"
