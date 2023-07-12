import os
import django

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
SECRET_KEY = "EX-TER-MI-NA-TE"

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True
TIME_ZONE = "Europe/Paris"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "tests",
    "dalec_example",
    "dalec_prime",
    "dalec",
]

if django.VERSION < (3, 2):
    INSTALLED_APPS.append("django_jsonfield_backport")

ROOT_URLCONF = "tests.urls"

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_PATH, "tests.sqlite3"),
    }
}
