from django.apps import apps
from django.utils.functional import classproperty
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.template.loader import select_template
from django.views.generic import TemplateView
from dalec import settings as app_settings
from dalec.proxy import ProxyPool


class FetchContent(ListView):

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
        return self.request.GET.get("template", None)

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        if self.paginate_by is not None:
            return self.paginate_by
        return app_settings.get_for('NB_CONTENTS_KEPT', self.app, self.content_type)

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
        qs = super().get_queryset(self, *args, **kwargs)
        qs.filter(app=self.dalec_app, content_type=self.dalec_content_types)
        if not self.dalec_channel:
            qs = qs.filter(channel__isnull=True)
        else:
            qs = qs.filter(channel=self.dalec_channel, channel_object=self.dalec_channel_object, )
        return qs

    def get_template_names(self, tpl_type="list"):
        kwargs = {"app": self.dalec_app,
                  "content_type": self.dalec_content_type,
                  "type": tpl_type}
        tpl_names = []
        if self.dalec_channel:
            kwargs["channel"] = self.dalec_channel
            tpl_names.append("dalec/{app}/{content_type}-{channel}-{type}.html".format(kwargs))
        tpl_names += [
            "dalec/{app}/{content_type}-{type}.html" % kwargs,
            "dalec/{app}/{type}.html" % kwargs,
            "dalec/default/{type}.html",
        ]
        css_framework = app_settings.CSS_FRAMEWORK
        if css_framework:
            for i in range(0, len(tpl_names)):
                parts = tpl.rsplit("/", 1)
                parts.insert(1, css_framework)
                tpl_names.insert(i, "/".join(parts))

        if self.dalec_template:
            tpl_names.insert(
                0,
                "dalec/{app}/%(tpl)s-{type}.html" % {**kwargs, "tpl": self.dalec_template}
            )
        return tpl_names

    def get_item_template(self):
        tpl_names = self.get_template_names(tpl_type="item")
        template = select_template(tpl_names)
        return template.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_kwargs = {
            "app": self.dalec_app,
            "content_type": self.dalec_content_type,
        }
        if self.dalec_channel:
            url_kwargs["channel"] =  self.dalec_channel
            url_kwargs["channel_object"] = self.dalec_channel_object
        context.update({
            "item_template": self.get_item_template(),
            "app": self.dalec_app,
            "channel": self.dalec_channel,
            "content_type": self.dalec_content_type,
            "url": reverse("dalec_fetch_content", kwargs=url_kwargs)
        })
        if self.dalec_template:
            context["url"] += "?template=%s" % self.dalec_template
        return context

    def refresh_content(self):
        proxy = ProxyPool.get(self.app)
        return proxy.refresh(
            self.dalec_content_type,
            self.dalec_channel,
            self.dalec_channel_object
        )
