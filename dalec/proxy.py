from django.utils.functional import classproperty
from dalec import settings as app_settings

class Proxy:
    app = None

    @classproperty
    def fetch_history_model(cls):
        return apps.get_model(app_settings.CONTENT_FETCH_HISTORY_MODEL)

    def __init__(self, content_type=None, channel=None, channel_object=None):
        if not self.app:
            # TODO : la récupérer automatiquement en fonction du path de la classe qui
            # hérite de celle-ci
            raise ValueError("app must be defined in your Proxy Class")
        # let this to None if same proxy can be used to retrieve all content_types
        self.content_type= content_type
        # let this to None if same proxy can be used to retrieve all channel
        self.channel= channel
        # let this to None if same proxy can be used to retrieve all channel_object
        self.channel_object= channel_object

    def refresh(self, content_type, channel, channel_object):
        """
        Fetch updated contents from the source and update/create it into the DB.
        Then, if some contents has been created, delete oldests contents which are not anymore
        required
        returns number of created, updated and deleted objects
        """
        if self.content_type and not content_type:
            content_type = self.content_type
        elif self.content_type and self.content_type != content_type:
            raise ValueError("content_type must be the same in proxy and refresh.")
        if self.channel and not channel:
            channel = self.channel
        elif self.channel and self.channel != channel:
            raise ValueError("channel must be the same in proxy and refresh.")
        if self.channel_object and not channel_object:
            channel_object = self.channel_object
        elif self.channel_object and self.channel_object != channel_object:
            raise ValueError("channel_object must be the same in proxy and refresh.")

        nb_created = 0
        nb_updated = 0
        nb_deleted = 0

        nb_created, nb_updated = self._fetch(content_type, channel, channel_object)

        if not nb_created:
            return nb_created, nb_updated, nb_deleted

        # TODO Delete

        return nb_created, nb_updated, nb_deleted

    def _fetch(content_type, channel, channel_object):
        """
        Fetch updated contents from the source and update/create it into the DB.
        returns number of created and updated objects
        """
        raise NotImplementedError(
            "You MUST implement your own _feth method depending your external source"
        )

    def exterminate(self, content_type, channel, channel_object):
        """
        deletes oldests entries (depending on setting DALEC_NB_CONTENTS_KEPT)
        returns number of entries deleted
        """
        # TODO

    def get_last_fetch(self, content_type, channel, channel_object):
        qs = self.fetch_history_model.objects.filter(app=self.app)

        if content_type:
            qs = qs.filter(content_type=content_type)

        if channel:
            qs = qs.filter(channel=channel)

        if channel_object:
            dj_channel_content_type = ContentType.objects.get_for_model(channel_object)
            qs = qs.filter(dj_channel_content_type__pk=channel_object_type.pk,
                           dj_channel_id=channel_object.pk)
        else:
            qs = qs.filter(dj_channel_id__isnull=True)
        return qs.latest()


def get_proxy(content_type=None, channel=None, channel_object=None):
    raise NotImplementedError("This is just an exemple. Please implement your own get_proxy function.")
    return Proxy(
        content_type=content_type,
        channel=channel,
        channel_object=channel_object
    )
