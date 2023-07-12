try:
    # Django imports
    from django.db.models import JSONField  # type: ignore
except ImportError:
    from django_jsonfield_backport.models import JSONField  # type: ignore

# Django imports
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

__all__ = ["FetchHistoryBase", "ContentBase"]


class FetchHistoryBase(models.Model):
    """
    Stores fetch queries history for a specific dalec's app [+ channel [+ channel obj]]
    """

    last_fetch_dt = models.DateTimeField(
        _("last fetch datetime"), auto_now=True, blank=False, null=False
    )
    app = models.CharField(_("dalec app"), max_length=50, null=False, blank=False)
    content_type = models.CharField(_("content type"), max_length=50, null=True, blank=True)
    channel = models.CharField(_("channel"), max_length=50, null=True, blank=True)
    channel_object = models.CharField(
        _("channel app object id"), max_length=255, null=True, blank=True
    )

    class Meta:
        verbose_name = _("Content fetch history line")
        verbose_name_plural = _("Content fetch history lines")
        ordering = ("-last_fetch_dt",)
        get_latest_by = "last_fetch_dt"
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
        db_index=True,
    )
    creation_dt = models.DateTimeField(
        _("created datetime (on external source)"),
        auto_now=False,
        auto_now_add=False,
        blank=False,
        null=False,
        db_index=True,
    )
    app = models.CharField(_("dalec app"), max_length=50, null=False, blank=False)
    content_type = models.CharField(_("content type"), max_length=50, null=True, blank=True)
    channel = models.CharField(_("channel"), max_length=50, null=True, blank=True)
    channel_object = models.CharField(
        _("channel app object id"), max_length=255, null=True, blank=True
    )
    dj_channel_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, blank=True, null=True, related_name="+"
    )
    dj_channel_id = models.PositiveIntegerField(
        verbose_name=_("related object"),
        blank=True,
        null=True,
        help_text=_(
            "The django's model's instance which is concerned."
            "(eg. could be an instance of model `Project` "
            "for app=gitlab, content_type=issue, channel=project)"
        ),
    )
    dj_channel_obj = GenericForeignKey(
        "dj_channel_content_type", "dj_channel_id", for_concrete_model=False
    )
    dj_content_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, blank=True, null=True, related_name="+"
    )
    dj_content_id = models.PositiveIntegerField(
        verbose_name=_("content"),
        blank=True,
        null=True,
        help_text=_(
            "The django's model's instance which is concerned "
            "(eg. could be an instance of model `Issue` for dalec-gitlab)"
        ),
    )
    dj_content_obj = GenericForeignKey(
        "dj_content_content_type", "dj_content_id", for_concrete_model=False
    )
    content_id = models.CharField(
        _("app's content id"),
        max_length=255,
        null=False,
        blank=False,
        help_text=_("ID of the content inside the external app."),
    )
    content_data = JSONField(encoder=DjangoJSONEncoder)

    class Meta:
        verbose_name = _("Content")
        verbose_name_plural = _("Contents")
        ordering = ("-last_update_dt",)
        get_latest_by = "last_update_dt"
        abstract = True
        index_together = (("app", "content_type", "channel", "channel_object"),)
