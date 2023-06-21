# Django imports
from django.urls import re_path

# Third Party
from dalec.views import FetchContentView

urlpatterns = [
    re_path(
        (
            "(?P<app>[a-z][a-z0-9_-]+)/(?P<content_type>[a-z][a-z0-9_-]+)"  # required part
            "(?:/(?P<channel>[a-zA-Z][a-zA-Z0-9_-]+)(?:/(?P<channel_object>[^/]+)?))?"  # opt part
        ),
        FetchContentView.as_view(),
        name="dalec_fetch_content",
    )
]
