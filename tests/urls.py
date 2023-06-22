from django.urls import include, path

urlpatterns = [
    path("dalec/", include("dalec.urls")),
]
