from django.template import Library, Context
from django.template.loader import select_template
from ..views import FetchContentView


register = Library()

@register.simple_tag(takes_context=True)
def dalec(context, app, content_type, template=None, channel=None, channel_object=None):
    """
    Show last N contents for a specific app+content_type (and optionnaly channel+channel_object)
    Usage exemple:

    {% load dalec %}

    Retrieves last gitlab issues for a specific user:
    {% dalec "gitlab" "issue" channel="user" channel_object="doctor-who" %}

    Retrieves recent gitlab activity for a group:
    {% dalec "gitlab" "activity" channel="group" channel_object='companions' %}

    Retrieves recent gitlab activity for a project:
    {% dalec "gitlab" "activity" channel="project" channel_object='tardis' %}

    Retrieves recent gitlab issues for a project:
    {% dalec "gitlab" "issue" channel="project" channel_object='tardis' %}
    """
    dalec_view = FetchContentView(_dalec_template=template)
    dalec_view.setup(
        context.get("request", None),
        dalec_app=app,
        dalec_content_type=content_type,
        dalec_channel=channel,
        dalec_channel_object=channel_object,
    )
    context = dalec_view.get_context_data()
    template = select_template(dalec_view.get_template_names())
    return template.render(Context(context))
