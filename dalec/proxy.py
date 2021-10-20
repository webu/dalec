from datetime import timedelta
from typing import Any, Union, Dict

from django.apps import apps
from django.db.models import Model
from django.utils import timezone
from django.utils.decorators import classproperty
from django.utils.module_loading import import_string

from dalec import settings as app_settings


class ProxyPool:
    _proxies = {}

    @classmethod
    def register(cls, proxy_class):
        if not issubclass(proxy_class, Proxy):
            raise ValueError(
                "Your proxyClass must extends dalec.proxy.Proxy"
            )
        if not proxy_class.app:
            raise ValueError(
                "Your proxyClass must set it's app name in its `app` attribute"
            )
        if proxy_class.app in cls._proxies and cls._proxies[proxy_class.app] != proxy_class:
            raise ValueError(
                "A proxy is already registered for app \"{app}\"".format(proxy_class.app)
            )
        cls._proxies[proxy_class.app] = proxy_class

    @classmethod
    def get(cls, app, autoload=True):
        if app not in cls._proxies:
            if autoload:
                # try to load the proxy module from dalec_<app>.
                try:
                    import_string('dalec_%(app)s.proxy' % app)
                except ImportError:
                    raise ValueError((
                        "No proxy registered for app {app} and "
                        "impossible to autoload dalec_{app}.proxy"
                    ).format(app=app))
                else:
                    return cls.get(app, autoload=False)
            raise ValueError("No proxy registered for app {app}".format(app=app))
        return cls._proxies[app]


class ProxyMeta(type):
    """
    Meta class to autoregister Proxy class when an app inherit from our Proxy abstact class.
    """

    def __new__(cls, name, bases, attrs):
        if not bases:
            return super().__new__(cls, name, bases, attrs)
        if not attrs.get('app'):
            raise ValueError("your proxyClass must set it's app name in its `app` attribute")
        proxy_class = super().__new__(cls, name, bases, attrs)
        ProxyPool.register(proxy_class)
        return proxy_class


class Proxy:
    """
    Abstact Proxy Class that dalec's children must inherit to define a proxy class specific
    for an app.
    """
    app = None

    @classproperty
    def content_model(cls) -> Model:
        """
        class attribute to easely get the Content model
        """
        return apps.get_model(app_settings.CONTENT_MODEL)

    @classproperty
    def fetch_history_model(cls) -> Model:
        """
        class attribute to easely get the FetchHistory model
        """
        return apps.get_model(app_settings.FETCH_HISTORY_MODEL)

    def refresh(
            self, content_type:str, channel:str, channel_object:str, force:bool=False,
            dj_channel_obj:Any=None
        ) -> Union(tuple(int, int, int), bool):
        """
        Fetch updated contents from the source and update/create it into the DB.
        Then, if some contents has been created, delete oldests contents which are not anymore
        required
        returns number of created, updated and deleted objects or False if cache not yet expired
        """
        dalec_kwargs = {
            'content_type': content_type, 'channel': channel, 'channel_object': channel_object
        }
        last_fetch = None if force else self.get_last_fetch(**dalec_kwargs)
        if last_fetch:
            too_old = timezone.now() - timedelta(seconds=app_settings.TTL)
            if last_fetch.last_fetch_dt > too_old :
                # last request is still too recent: we do not spam the external app
                return False

        contents = self._fetch(
            app_settings.get_for("NB_CONTENTS_KEPT", self.app, content_type),
            **dalec_kwargs
        )
        if not contents:
            return 0, 0, 0

        nb_updated = 0
        to_update = self.get_contents_queryset(**dalec_kwargs).filter(content_id__in=contents.keys())
        for instance in to_update:
            new_content = contents.pop(instance.content_id)
            res = self.update_content(instance=instance, new_content=new_content)
            if res:
                nb_updated += 1

        nb_created = 0
        for new_content in contents.values():
            self.create_content(content=new_content, dj_channel_obj=dj_channel_obj,
                                **dalec_kwargs)
            if res:
                nb_created += 1

        # exterminate the oldest ones if some new contents have been created
        nb_deleted = (0 if not nb_created
                      else self.exterminate(**dalec_kwargs))

        return nb_created, nb_updated, nb_deleted

    def create_content(
        self, content_type:str, channel:str, channel_object:str, content:dict,
        dj_channel_obj:Any=None
    ) -> bool:
        """
        Create a new instance of content and returns True if it has beend created
        """
        instance = self.content_model(
            creation_dt=content['creation_dt'],
            last_update_dt=content['last_update_dt'],
            app=self.app,
            content_type=content_type,
            channel=channel,
            channel_object=channel_object,
            dj_channel_obj=dj_channel_obj,
            content_id=content['id'],
            content_data=content,
        )
        instance.save()
        return True

    def update_content(self, instance:Model, new_content:dict) -> bool:
        """
        Update an existing instance of content and returns True if it really need update
        """
        if instance.content_data == new_content:
            return False
        update_fields = ["content_data"]
        instance.content_data = new_content
        if instance.creation_dt != new_content['creation_dt']:
            instance.creation_dt = new_content['creation_dt']
            update_fields.append("creation_dt")
        if instance.last_update_dt != new_content['last_update_dt']:
            instance.last_update_dt = new_content['last_update_dt']
            update_fields.append("last_update_dt")
        instance.save(update_fields=update_fields)
        return True

    def _fetch(self, nb:int, content_type:str, channel:str, channel_object:str) -> Dict[str, dict]:
        """
        Fetch updated contents from the source and return it as a dict of dict:
        main dict keys MUST be the app's content id, and value must be the content representation
        with at least three required attrs:
            id: ID of the content inside the external app
            last_update_dt: last update datetime inside the external app
            creation_dt: creation datetime inside the external app
        """
        raise NotImplementedError(
            "You MUST implement your own _feth method depending your external source"
        )

    def get_contents_queryset(self, content_type:str, channel:str, channel_object:str):
        return self.content_model.objects.filter(
            app=self.app,
            content_type=content_type,
            channel=channel,
            channel_object=channel_object
        )

    def exterminate(self, content_type:str, channel:str, channel_object:str) -> int:
        """
        deletes oldests entries (depending on setting DALEC_NB_CONTENTS_KEPT)
        returns number of entries deleted
        """
        model_label = self.content_model._meta.label
        nb_to_keep = app_settings.get_for("NB_CONTENTS_KEPT", self.app, content_type)
        qs = self.get_contents_queryset(content_type, channel, channel_object)
        to_keep = qs.order_by('-last_update_dt').values_list("pk")[0:nb_to_keep]
        result = qs.exclude(pk__in=to_keep).delete()
        return result[1].get(model_label, 0)

    def set_last_fetch(self, content_type:str, channel:str, channel_object:str, last_fetch=False):
        if last_fetch is None:
            last_fetch = self.get_last_fetch(content_type, channel, channel_object)
        elif not last_fetch:
            last_fetch = self.fetch_history_model(
                content_type=content_type,
                channel=channel,
                channel_object=channel_object,
            )
        last_fetch.last_fetch_dt = timezone.now()
        last_fetch.save()

    def get_last_fetch(self, content_type:str, channel:str, channel_object:str):
        qs = self.fetch_history_model.objects.filter(app=self.app)
        if content_type:
            qs = qs.filter(content_type=content_type)
        if channel:
            qs = qs.filter(channel=channel)
        if channel_object:
            qs = qs.filter(channel_object=channel_object)
        else:
            qs = qs.filter(channel_object__isnull=True)
        return qs.latest()
