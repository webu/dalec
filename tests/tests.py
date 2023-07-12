import time
from copy import copy
from importlib import reload

from bs4 import BeautifulSoup
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.template.loader import get_template
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now

from dalec import settings as app_settings
from dalec.proxy import ProxyPool
from dalec.tests_utils import DalecTestCaseMixin
from dalec.views import FetchContentView

__all__ = ["DalecTests"]


class DalecTests(DalecTestCaseMixin, TestCase):
    @override_settings(
        DALEC_EXAMPLE_NB_CONTENTS_KEPT=15,
        DALEC_EXAMPLE_FRENCH_EDUC_NB_CONTENTS_KEPT=20,
        DALEC_EXAMPLE_CONTENT_TYPE_NB_CONTENTS_KEPT=30,
    )
    def test_overrided_settings_app(self):
        """
        Test if settings overrided for a specific app is returned if set
        """
        reload(app_settings)
        self.assertEqual(app_settings.NB_CONTENTS_KEPT, 10)
        self.assertEqual(app_settings.get_for("NB_CONTENTS_KEPT", "example"), 15)
        self.assertEqual(app_settings.get_for("NB_CONTENTS_KEPT", "example", "quarter"), 15)
        self.assertEqual(app_settings.get_for("NB_CONTENTS_KEPT", "example", "french_educ"), 20)
        self.assertEqual(app_settings.get_for("NB_CONTENTS_KEPT", "example", "content-type"), 30)

    @override_settings(
        INSTALLED_APPS=[app for app in settings.INSTALLED_APPS if app != "dalec_prime"]
    )
    def test_missing_dalec_prime_content_model(self):
        with self.assertRaisesRegex(ValueError, "You must define a DALEC_CONTENT_MODEL"):
            reload(app_settings)

    @override_settings(
        INSTALLED_APPS=[app for app in settings.INSTALLED_APPS if app != "dalec_prime"],
        DALEC_CONTENT_MODEL="tests.Content",
    )
    def test_missing_dalec_prime_history_model(self):
        with self.assertRaisesRegex(ValueError, "You must define a DALEC_FETCH_HISTORY_MODEL"):
            reload(app_settings)

    @override_settings(
        DALEC_CONTENT_MODEL="tests.Content",
        DALEC_FETCH_HISTORY_MODEL="tests.FetchHistory",
    )
    def test_specific_models(self):
        reload(app_settings)
        content_model = app_settings.CONTENT_MODEL
        self.assertEqual(content_model, "tests.Content")
        fetch_history_model = app_settings.FETCH_HISTORY_MODEL
        self.assertEqual(fetch_history_model, "tests.FetchHistory")

        content_model = apps.get_model(content_model)
        fetch_history_model = apps.get_model(fetch_history_model)

        self.assertEqual(content_model.objects.count(), 0)
        self.assertEqual(fetch_history_model.objects.count(), 0)

        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("hour", "quarter")

        self.assertEqual(content_model.objects.count(), 10)
        self.assertEqual(fetch_history_model.objects.count(), 1)

    def test_setting_not_set(self):
        """
        Test behaviours for a not set settings : without default value, with default value,
        and with a raise if not set.
        """
        self.assertIsNone(app_settings.get_setting("UNDEFINED"))
        self.assertIs(app_settings.get_setting("UNDEFINED", False), False)
        with self.assertRaises(ValueError):
            app_settings.get_setting("UNDEFINED", False, raise_if_not_set=True)

    @override_settings(DALEC_TTL=1)
    def test_proxy_fetch_and_ttl(self):
        reload(app_settings)
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("hour", "quarter")
        self.assertEqual(created, app_settings.NB_CONTENTS_KEPT)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)

        # still alive
        created, updated, deleted = proxy.refresh("hour", "quarter")
        self.assertEqual(created, False)
        self.assertEqual(updated, False)
        self.assertEqual(deleted, False)

        time.sleep(1)
        # Expired
        created, updated, deleted = proxy.refresh("hour", "quarter")
        # if we change of current quarter, we could create at most ONE new quarter
        self.assertLessEqual(created, 1)
        self.assertEqual(updated, app_settings.NB_CONTENTS_KEPT - created)
        self.assertEqual(deleted, created)

    def test_standard_template_tags_dalec(self):
        template = get_template("dalec_tests/test-quarter.html")
        url = reverse(
            "dalec_fetch_content",
            kwargs={"app": "example", "content_type": "hour", "channel": "quarter"},
        )
        # Check there is nothing returned because nothing has been retrieved yet
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1)
        self.assertEqual(divs[0].string.strip(), "")
        self.assertIn("dalec-", divs[0].attrs["id"])
        self.assertEqual(len(divs[0].attrs["id"]), len("dalec-") + 32)  # md5
        self.assertEqual(divs[0].attrs["class"], ["dalec-list"])
        self.assertEqual(divs[0].attrs["data-url"], url)

        # Check there are still nothing (dalec templatetags must not query the external apps)
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1)
        self.assertEqual(divs[0].string.strip(), "")

        # Let's query the external apps to fetch contents
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("hour", "quarter")
        self.assertEqual(created, 10)
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1 + created)

        div_item = divs[1]
        self.assertEqual(div_item.attrs["class"], ["dalec-item"])
        self.assertEqual(div_item.attrs["data-app"], "example")
        self.assertEqual(div_item.attrs["data-content-type"], "hour")
        self.assertEqual(div_item.attrs["data-channel"], "quarter")
        self.assertNotIn("data-channel-object", div_item.attrs)
        last_quarter = self.content_model.objects.latest()
        self.assertEqual(div_item.string.strip(), last_quarter.content_data["id"])

    def test_standard_template_tags_to_datetime(self):
        c = Context(
            {
                "str_now": str(now()).replace(" ", "T"),
                "none": None,
                "empty": "",
                "format": "%d du mois %m année %Y",
                "invalid_date": "EX⋅TER⋅MI⋅NA⋅TE!",
                "invalid_format": "EX⋅TER⋅MI⋅NA⋅TE!",
            }
        )

        t = Template("""{% load dalec %}{{ none|to_datetime }}""")
        with self.assertRaisesRegex(ValueError, "No value"):
            output = t.render(c)

        t = Template("""{% load dalec %}{{ empty|to_datetime }}""")
        with self.assertRaisesRegex(ValueError, "No value"):
            output = t.render(c)

        t = Template("""{% load dalec %}{{ str_now|to_datetime }}""")
        output = t.render(c)

        t = Template(
            """{% load dalec %}{{ "24 du mois 12 année 2021"|to_datetime:format|date:"d/m/Y" }}"""
        )
        output = t.render(c)
        self.assertEqual(output, "24/12/2021")

        t = Template("""{% load dalec %}{{ invalid_date|to_datetime }}""")
        with self.assertRaisesRegex(ValueError, "No given format matching"):
            output = t.render(c)

        t = Template("""{% load dalec %}{{ str_now|to_datetime:format }}""")
        with self.assertRaisesRegex(ValueError, "No given format matching"):
            output = t.render(c)

    def test_proxy_fetch_with_channel_object(self):
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("hour", "quarter")
        self.assertEqual(created, app_settings.NB_CONTENTS_KEPT)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)

        proxy = ProxyPool.get("example")
        channel_object = "1985-07-02 21:45:00Z"
        created, updated, deleted = proxy.refresh("hour", "quarter", channel_object)
        self.assertEqual(created, app_settings.NB_CONTENTS_KEPT)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)

        all_contents = self.content_model.objects.all()
        self.assertEqual(all_contents.count(), 20)
        self.assertEqual(all_contents.filter(channel_object=None).count(), 10)
        self.assertEqual(all_contents.filter(channel_object=channel_object).count(), 10)

    def test_ordering_and_latest(self):
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("hour", "quarter", "1985-07-02 21:45:00Z")
        first_ordered = self.content_model.objects.first()
        latest_chrono = self.content_model.objects.latest()
        self.assertEqual(first_ordered.pk, latest_chrono.pk)
        self.assertEqual(first_ordered.content_data["id"], "21h45")

    def test_proxy_extending_rules(self):
        from .proxies.empty_child import EmptyChildProxy

        with self.assertRaisesRegex(ValueError, "extends `dalec.proxy.Proxy`"):
            ProxyPool.register(EmptyChildProxy)

        with self.assertRaisesRegex(ValueError, "`app` attribute"):
            from .proxies.bad_wolf import BadWolfProxy  # NOQA

        from tests.proxies.adiposian import AdiposianProxy

        with self.assertRaisesRegex(ValueError, "already registered"):
            ProxyPool.register(AdiposianProxy)

        with self.assertRaises(NotImplementedError):
            AdiposianProxy().refresh("adipose")

    def test_proxy_pool_autoload(self):
        proxy = ProxyPool.get("example")
        from dalec_example.proxy import ExampleProxy

        self.assertTrue(isinstance(proxy, ExampleProxy))

        example_proxy = ProxyPool.unregister("example")
        self.assertEqual(example_proxy, proxy)

        with self.assertRaisesRegex(ValueError, "No proxy registered"):
            ProxyPool.get("example", autoload=False)

        with self.assertRaisesRegex(ValueError, "No proxy registered"):
            ProxyPool.get("example")

        ProxyPool.register(example_proxy)
        self.assertEqual(ProxyPool.get("example"), proxy)

        with self.assertRaisesRegex(ValueError, "impossible to autoload"):
            proxy = ProxyPool.get("weeping_angel")

    def test_proxy_special_case(self):
        from .proxies.nice_dalek import NiceDalek

        proxy = NiceDalek()

        qs = self.fetch_history_model.objects.filter(app="nice_dalek")
        self.assertEqual(qs.count(), 0)
        created, updated, deleted = proxy.refresh(None)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)
        self.assertEqual(qs.count(), 1)

        fake_content = {
            "id": 0,
            "creation_dt": str(now()),
            "last_update_dt": str(now()),
            "nice": False,
        }
        fake_content_instance = self.content_model(content_data=copy(fake_content))
        res = proxy.update_content(fake_content_instance, fake_content)
        self.assertFalse(res)

    def test_view_response_code(self):
        kwargs = {"app": "example", "content_type": "hour", "channel": "quarter"}
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        qs = self.content_model.objects.filter(**kwargs)
        self.assertEqual(qs.count(), 0)

        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(qs.count(), 10)

        response = client.get(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(qs.count(), 10)

    def test_view_custom_template(self):
        kwargs = {"app": "example", "content_type": "hour", "channel": "quarter"}
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        response = client.get(url + "?template=faceof")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "face of Boe")

    def test_view_channel_object(self):
        kwargs = {
            "app": "example",
            "content_type": "hour",
            "channel": "quarter",
            "channel_object": "1985-07-02 23:45:00Z",
        }
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "23h45")
        latest = self.content_model.objects.filter(**kwargs).latest()
        earliest = self.content_model.objects.filter(**kwargs).earliest()
        self.assertEqual(latest.content_data["id"], "23h45")
        self.assertEqual(earliest.content_data["id"], "21h30")

    def test_channel_object_too_long(self):
        kwargs = {
            "app": "example",
            "content_type": "hour",
            "channel": "quarter",
            "channel_object": "{:256s}".format("2021-12-24 12:00"),
        }
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        with self.assertRaisesRegex(ValidationError, "channel_object"):
            client.get(url)

    def test_multiple_channel_objects_request(self):
        kwargs = {"app": "example", "content_type": "hour", "channel": "quarter"}
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        response = client.post(
            url,
            '{"channelObjects": ["2021-12-25 00:00", "2021-12-24 00:00"]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        qs = self.content_model.objects.filter(
            app="example", content_type="hour", channel="quarter"
        )
        self.assertEqual(qs.filter(channel_object="2021-12-24 00:00").count(), 10)
        self.assertEqual(qs.filter(channel_object="2021-12-25 00:00").count(), 10)

    def test_multiple_channel_objects_dalec_templatetags(self):
        template = get_template("dalec_tests/test-multiple-hours.html")
        # Check there is nothing returned because nothing has been retrieved yet
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1)
        self.assertEqual(divs[0].string.strip(), "")

        # Let's query the external apps to fetch contents
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh(
            "hour", "half", channel_object="2021-12-24 00:00"
        )
        self.assertEqual(created, 10)
        created, updated, deleted = proxy.refresh(
            "hour", "half", channel_object="2021-12-25 00:00"
        )
        self.assertEqual(created, 10)
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1 + created)

    def test_invalid_dalec_templatetags_call(self):
        t = Template(
            """{% load dalec %}
        {% dalec "example" "hour" channel="quarter" channel_object="A" channel_objects='["B"]' %}
        """
        )
        with self.assertRaisesRegexp(ValueError, "channel_objects"):
            t.render(Context({}))

    def test_simple_dalec_templatetags_call(self):
        t = Template(
            """{% load dalec %}
        {% dalec "example" "hour" channel="quarter" channel_object="2021-12-24" %}
        """
        )
        output = t.render(Context({}))
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(divs[0].attrs["data-channel-objects"], '["2021-12-24"]')
        html = (
            "{% load dalec %}"
            "{% dalec 'example' 'hour' "
            "channel='quarter' channel_objects='[\"2021-12-24\", \"2021-12-25\"]' %}"
        )
        output = Template(html).render(Context({}))
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(divs[0].attrs["data-channel-objects"], '["2021-12-24", "2021-12-25"]')

    def test_ordered_by_dalec_templatetags(self):
        # Let's query the external apps to fetch contents
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh(
            "hour", "half", channel_object="2021-12-24 12:00"
        )

        # Ascending order by ID
        html = (
            "{% load dalec %}"
            "{% dalec 'example' 'hour' channel='half' channel_object='2021-12-24 12:00' "
            "ordered_by='id' %}"
        )
        t_asc = Template(html)
        output = t_asc.render(Context({}))
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all(class_="dalec-item")
        self.assertIn("07h30", divs[0].string)
        self.assertIn("12h00", divs[-1].string)

        # Descending order by ID
        html = (
            "{% load dalec %}"
            "{% dalec 'example' 'hour' channel='half' channel_object='2021-12-24 12:00' "
            "ordered_by='-id' %}"
        )
        t_desc = Template(html)
        output = t_desc.render(Context({}))
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all(class_="dalec-item")
        self.assertIn("12h00", divs[0].string)
        self.assertIn("07h30", divs[-1].string)

    def test_missing_get_for(self):
        with self.assertRaisesRegexp(AttributeError, "MISSING_SETTING"):
            app_settings.get_for("MISSING_SETTING", "example", raise_if_not_set=True)

    @override_settings(
        INSTALLED_APPS=[app for app in settings.INSTALLED_APPS if app != "dalec_prime"]
    )
    def test_missing_history_model_and_dalec_prime(self):
        with self.assertRaisesRegexp(ValueError, "adding dalec_prime to your INSTALLED_APPS"):
            reload(app_settings)

    @override_settings(DALEC_CSS_FRAMEWORK="bootstrap")
    def test_css_framework_template_names(self):
        reload(app_settings)
        dalec_view = FetchContentView(_dalec_template=None)
        dalec_view.setup(None, app="app", content_type="content_type", channel="channel", page=1)
        template_names = dalec_view.get_template_names()
        expected = [
            "dalec/app/bootstrap/content_type-channel-list.html",
            "dalec/app/bootstrap/content_type-list.html",
            "dalec/app/bootstrap/list.html",
            "dalec/default/bootstrap/list.html",
            "dalec/app/content_type-channel-list.html",
            "dalec/app/content_type-list.html",
            "dalec/app/list.html",
            "dalec/default/list.html",
        ]
        self.assertEqual(template_names, expected)


class DalecExampleTests(TestCase):
    @property
    def content_model(self):
        return apps.get_model(app_settings.CONTENT_MODEL)

    @property
    def fetch_history_model(self):
        return apps.get_model(app_settings.FETCH_HISTORY_MODEL)

    def test_proxy_no_channel(self):
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("french_educ")
        self.assertEqual(created, 10)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)

    def test_proxy_channel_object(self):
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("french_educ", "academy", "Grenoble")
        self.assertEqual(created, 10)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)
        for c in self.content_model.objects.all():
            self.assertEqual(c.content_data["libelle_academie"], "Grenoble")

    def test_proxy_channel_object_quoted(self):
        proxy = ProxyPool.get("example")
        created, updated, deleted = proxy.refresh("hour", "quarter", "24/12/2021 12:00")
        self.assertEqual(created, 10)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)
        for c in self.content_model.objects.all():
            self.assertTrue("/" in c.channel_object)

    def test_view_no_channel_object(self):
        kwargs = {"app": "example", "content_type": "french_educ"}
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.content_model.objects.count(), 10)

    def test_invalid_channel_or_ct(self):
        proxy = ProxyPool.get("example")
        with self.assertRaisesRegexp(ValueError, "requires a channel"):
            created, updated, deleted = proxy.refresh("hour")
        with self.assertRaisesRegexp(ValueError, "requires a channel"):
            created, updated, deleted = proxy.refresh("hour", "yolo")
        with self.assertRaisesRegexp(ValueError, "Invalid content_type"):
            created, updated, deleted = proxy.refresh("yolo")
        with self.assertRaisesRegexp(ValueError, "Invalid channel"):
            created, updated, deleted = proxy.refresh("french_educ", "yolo")
        with self.assertRaisesRegexp(ValueError, "Invalid channel object"):
            created, updated, deleted = proxy.refresh("french_educ", "academy", " ")
