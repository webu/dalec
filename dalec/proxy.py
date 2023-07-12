# Future imports
from __future__ import annotations

# Standard libs
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict, Union, Type, Optional, Tuple
    from typing_extensions import Literal
    from django.db.models import Model
    from django.db.models.query import QuerySet
    from dalec.models import ContentBase, FetchHistoryBase

# Standard libs
from datetime import timedelta
from importlib import import_module

# Django imports
from django.apps import apps
from django.utils import timezone

try:
    # Django imports
    from django.utils.decorators import classproperty  # type: ignore
except ImportError:
    from django.utils.functional import classproperty  # type: ignore

# DALEC imports
from dalec import settings as app_settings

__all__ = ["ProxyPool", "Proxy"]


class ProxyPool:
    """
    Pool to register / load dalec children proxies
    """

    _proxies: Dict[str, Proxy] = {}

    @classmethod
    def unregister(cls, app: str) -> Union[Proxy, None]:
        """
        Remove from the pool the proxy registered for this app
        Return the removed proxy if it was existant or None"""
        return cls._proxies.pop(app, None)

    @classmethod
    def register(cls, proxy: Union[Proxy, Type[Proxy]], override: bool = False) -> None:
        """
        register a proxy instance into the pool
        if the proxy app is already registed, it will raise a ValueError unless you explicitely
        want to override it.
        """
        if isinstance(proxy, type):
            proxy = proxy()
        if not isinstance(proxy, Proxy):
            raise ValueError("Your proxy must extends `dalec.proxy.Proxy`")
        if not proxy.app:
            raise ValueError("Your proxy must set it's app name in its `app` attribute")
        if proxy.app in cls._proxies and not override and cls._proxies[proxy.app] != proxy:
            raise ValueError('A proxy is already registered for app "{app}"'.format(app=proxy.app))
        cls._proxies[proxy.app] = proxy

    @classmethod
    def get(cls, app: str, autoload: bool = True) -> Proxy:
        """
        Return the proxy registered for the given app.
        If it does not exists, the default behaviour is to try to autoload it
        from the module dalec_<app>.proxy
        Raise a ValueError if proxy can not be retrieved from the pool (or autoloaded)
        """
        if app not in cls._proxies:
            if autoload:
                # try to load the proxy module from dalec_<app>.
                try:
                    import_module("dalec_%s.proxy" % app)
                except ImportError as e:
                    raise ValueError(
                        (
                            "No proxy registered for app {app} and "
                            "impossible to autoload dalec_{app}.proxy"
                        ).format(app=app)
                    ) from e
                else:
                    return cls.get(app, autoload=False)
            raise ValueError("No proxy registered for app {app}".format(app=app))
        return cls._proxies[app]

    @classmethod
    def get_registered_apps(cls) -> Tuple[str, ...]:
        return tuple(cls._proxies.keys())


class ProxyMeta(type):
    """
    Meta class to autoregister Proxy class when an app inherit from our Proxy abstact class.
    """

    def __new__(cls: Type[ProxyMeta], name: str, bases: tuple, attrs: dict) -> ProxyMeta:
        """
        Build the new Proxy and auto-register it in the pool
        Auto register
        """
        if not bases:
            return super().__new__(cls, name, bases, attrs)
        proxy_class = super().__new__(cls, name, bases, attrs)
        ProxyPool.register(proxy_class)  # type: ignore
        return proxy_class


class Proxy(metaclass=ProxyMeta):
    """
    Abstact Proxy Class that dalec's children must inherit to define a proxy class specific
    for an app.
    """

    app: Optional[str] = None

    @classproperty
    def content_model(cls) -> Type[ContentBase]:
        """
        class attribute to easely get the Content model
        """
        return apps.get_model(app_settings.CONTENT_MODEL)

    @classproperty
    def fetch_history_model(cls) -> Type[FetchHistoryBase]:
        """
        class attribute to easely get the FetchHistory model
        """
        return apps.get_model(app_settings.FETCH_HISTORY_MODEL)

    def refresh(
        self,
        content_type: str,
        channel: Optional[str] = None,
        channel_object: Optional[str] = None,
        force: Optional[bool] = False,
        dj_channel_obj: Optional[Model] = None,
    ) -> Union[Tuple[int, int, int], Tuple[Literal[False], Literal[False], Literal[False]]]:
        """
        Fetch updated contents from the source and update/create it into the DB.
        Then, if some contents has been created, delete oldests contents which are not anymore
        required
        returns number of created, updated and deleted objects or False if cache not yet expired
        """
        dalec_kwargs = {
            "content_type": content_type,
            "channel": channel,
            "channel_object": channel_object,
        }
        last_fetch = None if force else self.get_last_fetch(**dalec_kwargs)  # type: ignore
        if last_fetch:
            too_old = timezone.now() - timedelta(seconds=app_settings.TTL)
            if last_fetch.last_fetch_dt > too_old:
                # last request is still too recent: we do not spam the external app
                return False, False, False
        nb = app_settings.get_for("NB_CONTENTS_KEPT", self.app, content_type)
        contents = self._fetch(nb, **dalec_kwargs)  # type: ignore
        self.set_last_fetch(last_fetch=last_fetch, **dalec_kwargs)  # type: ignore
        if not contents:
            return 0, 0, 0

        nb_updated = 0
        to_update = self.get_contents_queryset(**dalec_kwargs).filter(  # type: ignore
            content_id__in=contents.keys()
        )
        for instance in to_update:
            new_content = contents.pop(instance.content_id)
            res = self.update_content(instance=instance, new_content=new_content)
            if res:
                nb_updated += 1

        nb_created = 0
        for new_content in contents.values():
            res = self.create_content(
                content=new_content,
                dj_channel_obj=dj_channel_obj,
                **dalec_kwargs,  # type: ignore
            )
            if res:
                nb_created += 1
        # exterminate the oldest ones if some new contents have been created
        nb_deleted = 0 if not nb_created else self.exterminate(**dalec_kwargs)  # type: ignore

        return nb_created, nb_updated, nb_deleted

    def create_content(
        self,
        content_type: str,
        channel: str,
        channel_object: str,
        content: dict,
        dj_channel_obj: Optional[Model] = None,
    ) -> ContentBase:
        """
        Create a new instance of content and return it
        """
        instance = self.content_model(
            creation_dt=content["creation_dt"],
            last_update_dt=content["last_update_dt"],
            app=self.app,
            content_type=content_type,
            channel=channel,
            channel_object=channel_object,
            dj_channel_obj=dj_channel_obj,
            content_id=content["id"],
            content_data=content,
        )
        instance.full_clean()
        instance.save()
        return instance

    def update_content(self, instance: ContentBase, new_content: dict) -> bool:
        """
        Update an existing instance of content and returns True if it really needed update
        """
        if instance.content_data == new_content:
            return False
        update_fields = ["content_data"]
        instance.content_data = new_content
        if instance.creation_dt != new_content["creation_dt"]:
            instance.creation_dt = new_content["creation_dt"]
            update_fields.append("creation_dt")
        if instance.last_update_dt != new_content["last_update_dt"]:
            instance.last_update_dt = new_content["last_update_dt"]
            update_fields.append("last_update_dt")
        instance.full_clean()
        instance.save(update_fields=update_fields)
        return True

    def _fetch(
        self, nb: int, content_type: str, channel: str, channel_object: str
    ) -> Dict[str, dict]:
        """
        Fetch updated contents from the source and return it as a dict of dict:
        main dict keys MUST be the app's content id, and value must be the content representation
        with at least three required attrs:

        - `id`: ID of the content inside the external app
        - `last_update_dt`: last update datetime inside the external app
        - `creation_dt`: creation datetime inside the external app
        """
        raise NotImplementedError(
            "You MUST implement your own _feth method depending your external source"
        )

    def get_contents_queryset(
        self, content_type: str, channel: str, channel_object: str
    ) -> QuerySet:
        return self.content_model.objects.filter(
            app=self.app,
            content_type=content_type,
            channel=channel,
            channel_object=channel_object,
        )

    def exterminate(self, content_type: str, channel: str, channel_object: str) -> int:
        """
        deletes oldests entries (depending on setting DALEC_NB_CONTENTS_KEPT)
        returns number of entries deleted
        """
        model_label = self.content_model._meta.label
        nb_to_keep = app_settings.get_for("NB_CONTENTS_KEPT", self.app, content_type)
        qs = self.get_contents_queryset(content_type, channel, channel_object)
        to_keep = qs.order_by("-last_update_dt").values_list("pk")[0:nb_to_keep]
        result = qs.exclude(pk__in=to_keep).delete()
        return result[1].get(model_label, 0)

    def set_last_fetch(
        self,
        content_type: str,
        channel: str,
        channel_object: str,
        last_fetch: Union[FetchHistoryBase, Literal[False], None] = False,
    ) -> FetchHistoryBase:
        """
        Uodate or create a FetchHistory instance to register the last fetch datetime
        and return this instance
        if last_fetch is False, we avoid to query it (because we alreay know it does not exists)
        if last_fetch is None, we will try to get it via get_last_fetch
        else, it must be the last_fetch instance.
        """
        if last_fetch is None:
            last_fetch = self.get_last_fetch(content_type, channel, channel_object)
        if not last_fetch:
            last_fetch = self.fetch_history_model(
                app=self.app,
                content_type=content_type,
                channel=channel,
                channel_object=channel_object,
            )
        last_fetch.last_fetch_dt = timezone.now()  # type: ignore
        last_fetch.full_clean()  # type: ignore
        last_fetch.save()  # type: ignore
        return last_fetch  # type: ignore

    def get_last_fetch(
        self, content_type: str, channel: str, channel_object: str
    ) -> Union[FetchHistoryBase, None]:
        """
        Retrieve from the DB the last instance of FetchHistory for the current
        app, content_type, channel, channel_object
        or None if it does not exist
        """
        qs = self.fetch_history_model.objects.filter(app=self.app)
        if content_type:
            qs = qs.filter(content_type=content_type)
        if channel:
            qs = qs.filter(channel=channel)
        if channel_object:
            qs = qs.filter(channel_object=channel_object)
        else:
            qs = qs.filter(channel_object__isnull=True)
        try:
            return qs.latest()
        except self.fetch_history_model.DoesNotExist:
            return None
