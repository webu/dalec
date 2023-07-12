# Future imports
from __future__ import annotations

# Standard libs
from copy import copy
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union, List, Type
    from dalec.models import ContentBase
    from django.http import HttpRequest
    from django.db.models.query import QuerySet

# Standard libs
import hashlib
import urllib.parse

# Django imports
from django.apps import apps
from django.http import HttpResponse
from django.template.loader import select_template
from django.urls import reverse

try:
    # Django imports
    from django.utils.decorators import classproperty  # type: ignore
except ImportError:
    from django.utils.functional import classproperty  # type: ignore

# Django imports
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

# DALEC imports
from dalec import settings as app_settings
from dalec.proxy import ProxyPool

__all__ = ["FetchContentView"]


@method_decorator(csrf_exempt, name="dispatch")
class FetchContentView(ListView):
    @classproperty
    def model(cls) -> Type[ContentBase]:
        return apps.get_model(app_settings.CONTENT_MODEL)

    @property
    def dalec_app(self) -> str:
        return self.kwargs["app"]

    @property
    def dalec_content_type(self) -> str:
        return self.kwargs["content_type"]

    @property
    def dalec_channel(self) -> Union[str, None]:
        return self.kwargs.get("channel", None)

    @property
    def ordered_by(self) -> Union[str, None]:
        return self.kwargs.get("ordered_by", None)

    @ordered_by.setter
    def ordered_by(self, ordered_by: Union[str, None]) -> None:
        self.kwargs["ordered_by"] = ordered_by

    @property
    def dalec_channel_objects(self) -> List[str]:
        return self.kwargs.get("channel_objects", [])

    @dalec_channel_objects.setter
    def dalec_channel_objects(self, channel_objects: List[str]) -> None:
        self.kwargs["channel_objects"] = channel_objects

    @cached_property
    def dalec_template(self) -> Union[str, None]:
        return (
            self._dalec_template
            if hasattr(self, "_dalec_template")
            else self.request.GET.get("template", None)
        )

    def get_paginate_by(self, queryset: QuerySet) -> int:
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return app_settings.get_for("NB_CONTENTS_KEPT", self.dalec_app, self.content_type)

    def post(self, request: HttpRequest, *args: tuple, **kwargs: dict) -> HttpResponse:
        if request.body:
            data = json.loads(self.request.body)
            self.dalec_channel_objects = data.get("channelObjects", None)
            self.ordered_by = data.get("orderedBy", None)
        return self.get(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args: tuple, **kwargs: dict) -> HttpResponse:
        """
        Return a TemplateResponse with HTML for the last X elements wanted
        or a 204 response if nothing need an update (cache used or still the same contents)
        """
        if self.kwargs.get("channel_object", None):
            self.dalec_channel_objects = [urllib.parse.unquote(self.kwargs["channel_object"])]
        refreshed = self.refresh_contents()
        if not refreshed:
            # nothing to refresh, our content is already the updated one
            # note this is not quite True, because TTL could have expired between the moment
            # we display contents and this request BUT in the same time, another
            # request refreshed the cache and set a new TTL:
            # when we process "our" request, a new TTL is valid, so refresh_content will
            # return False, BUT we still have content of the old cache.
            # It only doubles the TTL in the worst case.
            # IMHO, it's acceptable…
            # BUT, if we want to manage this edge case, we MUST send the datetime of the
            # fetchHistory we are using: if it's != from the used one, we MUST query the DB
            # and return new html contents.
            return HttpResponse(status=204)
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args: tuple, **kwargs: dict) -> QuerySet:
        """
        Return the queryset filtered by app + contentype and optionaly channel and channel object
        if it's given
        """
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(app=self.dalec_app, content_type=self.dalec_content_type)
        if not self.dalec_channel:
            qs = qs.filter(channel__isnull=True)
        else:
            qs = qs.filter(channel=self.dalec_channel)
            if self.dalec_channel_objects:
                qs = qs.filter(channel_object__in=self.dalec_channel_objects)
            else:
                qs = qs.filter(channel_object__isnull=True)

        if self.ordered_by:
            order = ""
            if self.ordered_by.startswith("-"):
                order = "-"
                ordered_by = self.ordered_by[1:]
            else:
                ordered_by = self.ordered_by
            qs = qs.order_by(f"{order}content_data__{ordered_by}")
        return qs

    def get_template_names(self, template_type: str = "list") -> List:
        """
        Return a list of valid templates names, ordered by priority.
        """
        kwargs = {
            "app": self.dalec_app,
            "content_type": self.dalec_content_type,
            "type": template_type,
        }
        tpl_names = []
        if self.dalec_channel:
            kwargs["channel"] = self.dalec_channel
            tpl_names.append("dalec/{app}/{content_type}-{channel}-{type}.html".format(**kwargs))
        tpl_names += [
            "dalec/{app}/{content_type}-{type}.html".format(**kwargs),
            "dalec/{app}/{type}.html".format(**kwargs),
            "dalec/default/{type}.html".format(**kwargs),
        ]
        css_framework = app_settings.CSS_FRAMEWORK
        if css_framework:
            for i, tpl_name in enumerate(copy(tpl_names)):
                parts = tpl_name.rsplit("/", 1)
                parts.insert(1, css_framework)
                tpl_names.insert(i, "/".join(parts))
        if self.dalec_template:
            tpl_names.insert(
                0,
                "dalec/{app}/{tpl}-{type}.html".format(**{**kwargs, "tpl": self.dalec_template}),
            )
        return tpl_names

    def get_item_template(self) -> str:
        """
        Return the template name to use to display an item in the list, depending the
        custom template, app, content_type, channel and css_framework if used.
        """
        tpl_names = self.get_template_names(template_type="item")
        template = select_template(tpl_names)
        return template.template.name

    def get_context_data(self, **kwargs: dict) -> dict:
        """Get the context for this view."""
        context = super().get_context_data(**kwargs)
        url_kwargs = {"app": self.dalec_app, "content_type": self.dalec_content_type}
        if self.dalec_channel:
            url_kwargs["channel"] = self.dalec_channel
        context.update(
            {
                "item_template": self.get_item_template(),
                "app": self.dalec_app,
                "content_type": self.dalec_content_type,
                "channel": self.dalec_channel,
                "channel_objects": self.dalec_channel_objects,
                "json_channel_objects": json.dumps(self.dalec_channel_objects),
                "ordered_by": self.ordered_by,
                "url": reverse("dalec_fetch_content", kwargs=url_kwargs),
                "ajax_refresh": app_settings.AJAX_REFRESH,
                "is_fetch": self.request
                and self.request.headers.get("content-type") == "application/json",
            }
        )
        temp_id = "{app}-{content_type}-{channel}-{json_channel_objects}".format(**context)
        context["id"] = hashlib.md5(temp_id.encode("utf-8")).hexdigest()
        if self.dalec_template:
            context["url"] += "?template=%s" % self.dalec_template
        return context

    def refresh_contents(self) -> bool:
        """
        Asks to the proxy to refresh content and returns True if something has been or False if
        there are no new created/updated/deleted content (in this case this view will return a 204)
        """
        proxy = ProxyPool.get(self.dalec_app)
        something_changed = False
        if self.dalec_channel_objects:
            for channel_object in self.dalec_channel_objects:
                created, updated, deleted = proxy.refresh(
                    self.dalec_content_type, self.dalec_channel, channel_object
                )
                something_changed = something_changed or bool(created or updated or deleted)
        else:
            created, updated, deleted = proxy.refresh(self.dalec_content_type, self.dalec_channel)
            something_changed = bool(created or updated or deleted)
        return something_changed
