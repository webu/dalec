# "Standard libs"
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional

from django.template import Library
from django.template.loader import select_template
from ..views import FetchContentView


register = Library()


@register.simple_tag(takes_context=True)
def dalec(
    context: dict,
    app: str,
    content_type: str,
    channel: Optional[str] = None,
    channel_object: Optional[str] = None,
    template: Optional[str] = None,
) -> str:
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
    template_obj = select_template(dalec_view.get_template_names())
    return template_obj.render(context)
