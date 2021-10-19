from django.apps import apps
from django.utils.functional import classproperty
from django.utils.module_loading import import_string
from django.template.loader import select_template
from django.views.generic import TemplateView
from dalec import settings as app_settings
from dalec.proxy import ProxyPool


class FetchContent(ListView):

    @classproperty
    def model(cls):
        return apps.get_model(app_settings.CONTENT_MODEL)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(self, *args, **kwargs)
        qs.filter(app=self.dalec_app, content_type=self.dalec_content_types)
        if not self.dalec_channel:
            qs = qs.filter(channel__isnull=True)
        else:
            qs = qs.filter(channel=self.dalec_channel, channel_object=self.dalec_channel_object, )
        return qs

    def get_template_names(self):
        kwargs = {"app": self.dalec_app, "content_type": self.dalec_content_type}
        tpl_names = []
        tpl = self.request.GET.get('template')
        if tpl:
            tpl_names.append("dalec/%(app)s/%(tpl)s-list.html" % {**kwargs, "tpl": tpl}, )
        if self.dalec_channel:
            kwargs["channel"] = self.dalec_channel
            tpl_names.append("dalec/%(app)s/%(content_type)s-%(channel)s-list.html" % kwargs)
        tpl_names += [
            "dalec/%(app)s/%(content_type)s-list.html" % kwargs,
            "dalec/%(app)s/list.html" % kwargs,
            "dalec/default/list.html",
        ]
        return tpl_names

    def get_item_template(self):
        kwargs = {"app": self.dalec_app, "content_type": self.dalec_content_type}
        tpl_names = []
        tpl = self.request.GET.get('template')
        if tpl:
            tpl_names.append("dalec/%(app)s/%(tpl)s-item.html" % {**kwargs, "tpl": tpl}, )
        if self.dalec_channel:
            kwargs["channel"] = self.dalec_channel
            tpl_names.append("dalec/%(app)s/%(content_type)s-%(channel)s-item.html" % kwargs)
        tpl_names += [
            "dalec/%(app)s/%(content_type)s-item.html" % kwargs,
            "dalec/%(app)s/item.html" % kwargs,
            "dalec/default/item.html",
        ]
        template = select_template(tpl_names)
        return template.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "item_template": self.get_item_template(),
            "app": self.dalec_app,
            "channel": self.dalec_channel,
            "content_type": self.dalec_content_type,
            "ajax_kwargs": json.dumps({
                "app": self.dalec_app,
                "channel": self.dalec_channel,
                "content_type": self.dalec_content_type,
                "channel_object": self.dalec_channel_object,
            })
        })
        self.refresh_content()
        return context

    def refresh_content(self):
        proxy = ProxyPool.get(self.app)
        return proxy.refresh(
            self.dalec_content_type,
            self.dalec_channel,
            self.dalec_channel_object
        )
