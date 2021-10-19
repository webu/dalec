from django.urls import path

from dalec.views import FetchContent


class AppConverter:
    regex = '[a-z][a-z0-9_-]+'

    def to_python(self, value):
        return value.replace('-', '_')

    def to_url(self, value):
        return value.replace('_', '-')


register_converter(AppConverter, 'pyname')

urlpatterns = [
    path('<app:app>/<str:content_type>/(<channel>/<channel_object>/)?', FetchContent.as_view()),
]
