# Django imports
from django.urls import re_path

# DALEC imports
# Third Party
from dalec.views import FetchContentView

fetch_content_view = FetchContentView.as_view()
urlpatterns = [
    re_path(
        (
            "(?P<app>[a-z][a-z0-9_-]+)/(?P<content_type>[a-z][a-z0-9_-]+)"  # required part
            "/(?P<channel>[a-zA-Z][a-zA-Z0-9_-]+)"
            "/(?P<channel_object>[^/]+)"
            "/(?P<ordered_by>[^/]+)"
        ),
        fetch_content_view,
        name="dalec_fetch_content",
    ),
    re_path(
        (
            "(?P<app>[a-z][a-z0-9_-]+)/(?P<content_type>[a-z][a-z0-9_-]+)"  # required part
            "/(?P<channel>[a-zA-Z][a-zA-Z0-9_-]+)"
            "/(?P<channel_object>[^/]+)"
        ),
        fetch_content_view,
        name="dalec_fetch_content",
    ),
    re_path(
        (
            "(?P<app>[a-z][a-z0-9_-]+)/(?P<content_type>[a-z][a-z0-9_-]+)"  # required part
            "/(?P<channel>[a-zA-Z][a-zA-Z0-9_-]+)"
        ),
        fetch_content_view,
        name="dalec_fetch_content",
    ),
    re_path(
        "(?P<app>[a-z][a-z0-9_-]+)/(?P<content_type>[a-z][a-z0-9_-]+)",  # required part
        fetch_content_view,
        name="dalec_fetch_content",
    ),
]
