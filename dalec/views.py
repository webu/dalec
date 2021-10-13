from django.apps import apps
from django.utils.functional import classproperty
from django.utils.module_loading import import_string
from django.template.loader import select_template
from django.views.generic import TemplateView
from dalec import settings as app_settings


class FetchContent(ListView):

    @classproperty
    def model(cls):
        return apps.get_model(app_settings.CONTENT_MODEL)

    def get_template_names(self):
        kwargs = {"app": self.dalec_app, "content_type": self.dalec_content_type}
        tpl_names = [
            "dalec/%(app)s/%(content_type)s-list.html" % kwargs,
            "dalec/%(app)s/list.html" % kwargs,
            "dalec/default/list.html",
        ]
        if self.channel:
            kwargs["channel"] = self.dalec_channel
            tpl_names.insert(0, "dalec/%(app)s/%(content_type)s-%(channel)s-list.html" % kwargs)
        return tpl_names

    def get_item_template(self):
        tpl_names = [
            "dalec/%(app)s/%(content_type)s-item.html" % kwargs,
            "dalec/%(app)s/item.html" % kwargs,
            "dalec/default/item.html",
        ]
        if self.channel:
            kwargs["channel"] = self.dalec_channel
            tpl_names.insert(0, "dalec/%(app)s/%(content_type)s-%(channel)s-item.html" % kwargs)
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
                "channel_object": (
                    None if not self.channel_object
                    else ("%s.%s" % (self.channel_object._meta.model_nameapp_label,
                                     self.channel_object._meta.model_name),
                          self.channel_object.pk)
            })
        })
        self.refresh_content()
        return context

    def refresh_content(self):
        get_client = import_string('dalec_%(app)s.proxy.get_proxy' % app)
        proxy = self.get_proxy(
            self.dalec_content_type,
            self.dalec_channel,
            self.dalec_channel_object
        )
        return proxy.refresh(
            self.dalec_content_type,
            self.dalec_channel,
            self.dalec_channel_object
        )
