# "Standard libs"
from __future__ import annotations
import json
from typing import TYPE_CHECKING
import datetime

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
    channel_objects: Optional[str] = None,
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

    Retrieves recent gitlab issues for multiple projects:
    {% dalec "gitlab" "issue" channel="project" channel_objects='["cybermen", "weeping-angel"]' %}
    """
    if channel_object and channel_objects:
        raise ValueError(
            "You can not use channel_object AND channel_objects at the same time"
        )
    dalec_view = FetchContentView(_dalec_template=template)
    if channel_objects:
        list_channel_objects = json.loads(channel_objects)
    elif channel_object:
        list_channel_objects = [channel_object]
    else:
        list_channel_objects = None
    dalec_view.setup(
        context.get("request", None),
        app=app,
        content_type=content_type,
        channel=channel,
        channel_objects=list_channel_objects,
        page=1,
    )
    dalec_view.object_list = dalec_view.get_queryset()
    context = dalec_view.get_context_data()
    template_obj = select_template(dalec_view.get_template_names())
    return template_obj.render(context)


@register.filter(expects_localtime=True, is_safe=False)
def to_datetime(value: str, api_date_format: Optional[str] = None) -> datetime.datetime:
    """
    API string to datetime object

    Different API retourne date with different format (timezone aware, date, datetime,
    etc). This filter try to guess the most appropriate one and return a datetime object.

    Params
    ------

    api_date_format : str
        Date format of the value. Default '%Y-%m-%dT%H:%M:%S.%f%z',
        i.e. 2019-08-30T08:22:32.245-0700

    Returns
    -------

    datetime.datetime object
    """
    if value in (None, ""):
        raise ValueError("No value for the date conversion")

    if api_date_format is None:
        api_date_format = "%Y-%m-%dT%H:%M:%S.%f%z"

    return datetime.datetime.strptime(value, api_date_format)
