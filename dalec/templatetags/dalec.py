from django.template import Library
from django.template.loader import select_template
from ..views import FetchContentView


register = Library()


@register.simple_tag(takes_context=True)
def dalec(context, app, content_type, channel=None, channel_object=None, template=None):
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
        app=app,
        content_type=content_type,
        channel=channel,
        channel_object=channel_object,
        page=1,
    )
    dalec_view.object_list = dalec_view.get_queryset()
    context = dalec_view.get_context_data()
    template = select_template(dalec_view.get_template_names())
    return template.render(context)
