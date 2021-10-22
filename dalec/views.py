import hashlib

from django.apps import apps
from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import select_template
from django.utils.decorators import classproperty
from django.utils.functional import cached_property
from django.views.generic import ListView

from dalec import settings as app_settings
from dalec.proxy import ProxyPool


class FetchContentView(ListView):

    @classproperty
    def model(cls):
        return apps.get_model(app_settings.CONTENT_MODEL)

    @property
    def dalec_app(self):
        return self.kwargs["app"]

    @property
    def dalec_content_type(self):
        return self.kwargs["content_type"]

    @property
    def dalec_channel(self):
        return self.kwargs.get("channel", None)

    @property
    def dalec_channel_object(self):
        return self.kwargs.get("channel_object", None)

    @cached_property
    def dalec_template(self):
        return (
            self._dalec_template if hasattr(self, '_dalec_template')
            else self.request.GET.get("template", None)
        )

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return app_settings.get_for('NB_CONTENTS_KEPT', self.dalec_app, self.content_type)

    def get(self, request, *args, **kwargs):
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

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(app=self.dalec_app, content_type=self.dalec_content_type)
        if not self.dalec_channel:
            qs = qs.filter(channel__isnull=True)
        else:
            qs = qs.filter(channel=self.dalec_channel, channel_object=self.dalec_channel_object, )
        return qs

    def get_template_names(self, template_type="list"):
        """
        Returns list of valid templates names, ordered by priority.
        """
        kwargs = {
            "app": self.dalec_app,
            "content_type": self.dalec_content_type,
            "type": template_type
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
            for i, tpl_name in enumerate(tpl_names):
                parts = tpl_name.rsplit("/", 1)
                parts.insert(1, css_framework)
                tpl_names.insert(i, "/".join(parts))
        if self.dalec_template:
            tpl_names.insert(
                0,
                "dalec/{app}/{tpl}-{type}.html".format(**{**kwargs, "tpl": self.dalec_template})
            )
        return tpl_names

    def get_item_template(self):
        tpl_names = self.get_template_names(template_type="item")
        template = select_template(tpl_names)
        return template.template.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_kwargs = {
            "app": self.dalec_app,
            "content_type": self.dalec_content_type,
        }
        if self.dalec_channel:
            url_kwargs["channel"] =  self.dalec_channel
            if self.dalec_channel_object:
                url_kwargs["channel_object"] = self.dalec_channel_object
        context.update({
            "item_template": self.get_item_template(),
            "app": self.dalec_app,
            "content_type": self.dalec_content_type,
            "channel": self.dalec_channel,
            "channel_object": self.dalec_channel_object,
            "url": reverse("dalec_fetch_content", kwargs=url_kwargs),
            "ajax_refresh": app_settings.AJAX_REFRESH,
        })
        temp_id = "{app}-{content_type}-{channel}-{channel_object}".format(**context)
        context["id"] = hashlib.md5(temp_id.encode('utf-8')).hexdigest()
        if self.dalec_template:
            context["url"] += "?template=%s" % self.dalec_template
        return context

    def refresh_contents(self):
        proxy = ProxyPool.get(self.dalec_app)
        created, updated, deleted = proxy.refresh(
            self.dalec_content_type,
            self.dalec_channel,
            self.dalec_channel_object
        )
        return bool(created or updated or deleted)
