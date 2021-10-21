from django.conf.urls import url
from django.urls import register_converter
from dalec.views import FetchContentView


# class AppConverter:
#     regex = '[a-z][a-z0-9_-]+'

#     def to_python(self, value):
#         return value.replace('-', '_')

#     def to_url(self, value):
#         return value.replace('_', '-')


# register_converter(AppConverter, 'app')

urlpatterns = [
    url('(?P<app>[a-z][a-z0-9_-]+)/(?P<content_type>[a-z][a-z0-9_-]+)(?:/(?P<channel>[a-z][a-z0-9_-]+)/(?P<channel_object>[a-z][a-z0-9_-]+))?',
         FetchContentView.as_view(),
         name="dalec_fetch_content"
    ),
]
