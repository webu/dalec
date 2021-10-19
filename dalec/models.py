from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth import get_user_model


class FetchHistoryBase(models.Model):
    """
    Stores fetch queries history for a specific dalec's app [+ channel [+ channel obj]]
    """
    last_fetch_dt = models.DateTimeField(
        _("last fetch datetime"),
        auto_now=True,
        auto_now_add=True,
        blank=False,
        null=False,
    )
    app = models.CharField(
        _("dalec app"),
        max_length=50,
        null=False,
        blank=False,
    )
    content_type = models.CharField(
        _("content type"),
        max_length=50,
        null=True,
        blank=True,
    )
    channel = models.CharField(
        _("channel"),
        max_length=50,
        null=True,
        blank=True,
    )
    channel_object = models.CharField(
        _("channel app object id"),
        max_length=50,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Content fetch history line")
        verbose_name_plural = _("Content fetch history lines")
        order_by = ('-last_fetch_dt', )
        get_latest_by = 'last_fetch_dt'
        abstract = True


class ContentBase(models.Model):
    """
    Stores generic contents retrieved from an external source
    """
    last_update_dt = models.DateTimeField(
        _("last update datetime (on external source)"),
        auto_now=False,
        auto_now_add=False,
        blank=False,
        null=False,
        index=True,
    )
    creation_dt = models.DateTimeField(
        _("created datetime (on external source)"),
        auto_now=False,
        auto_now_add=False,
        blank=False,
        null=False,
        index=True,
    )
    app = models.CharField(
        _("dalec app"),
        max_length=50,
        null=False,
        blank=False,
    )
    content_type = models.CharField(
        _("content type"),
        max_length=50,
        null=True,
        blank=True,
    )
    channel = models.CharField(
        _("channel"),
        max_length=50,
        null=True,
        blank=True,
    )
    channel_object = models.CharField(
        _("channel app object id"),
        max_length=50,
        null=True,
        blank=True,
    )
    dj_channel_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    dj_channel_id = models.PositiveIntegerField()
    dj_channel_obj = GenericForeignKey(
        'dj_channel_content_type', 'dj_channel_id',
        for_concrete_model=False,
        verbose_name=_("related object"),
        blank=True,
        null=True,
        help_text=_("The django's model's instance which is concerned."
                    "(eg. could be an instance of model `Project` for dalec-gitlab)")
    )
    dj_content_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    dj_content_id = models.PositiveIntegerField()
    dj_content_obj = GenericForeignKey(
        'dj_content_content_type', 'dj_content_id',
        for_concrete_model=False,
        verbose_name=_("content"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=_("The django's model's instance which is concerned "
                    "(eg. could be an instance of model `Issue` for dalec-gitlab)")
    )
    content_id = models.CharField(
        _("app's content id"),
        max_length=255,
        null=False,
        blank=False,
        help_text=_("ID of the content inside the external app.")
    )
    content_data = models.JSONField(
        encoder="django.core.serializers.json.DjangoJSONEncoder"
    )

    class Meta:
        verbose_name = _("Content")
        verbose_name_plural = _("Contents")
        order_by = ('-last_update_dt', )
        get_latest_by = 'last_update_dt'
        abstract = True
        index_together = (
            ('app', 'content_type', 'channel'),
        )
