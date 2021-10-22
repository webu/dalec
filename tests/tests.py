import time

from copy import copy
from django.apps import apps
from django.conf import settings
from django.template.loader import get_template
from django.test import Client
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now
from django.urls import reverse

from bs4 import BeautifulSoup

from dalec import settings as app_settings
from dalec.proxy import ProxyPool


class DalecTests(TestCase):
    @property
    def content_model(self):
        return apps.get_model(app_settings.CONTENT_MODEL)

    @property
    def fetch_history_model(self):
        return apps.get_model(app_settings.FETCH_HISTORY_MODEL)

    @override_settings(
        DALEC_EXEMPLE_NB_CONTENTS_KEPT=15,
        DALEC_EXEMPLE_FRENCH_EDUC_NB_CONTENTS_KEPT=20,
        DALEC_EXEMPLE_CONTENT_TYPE_NB_CONTENTS_KEPT=30,
    )
    def test_overrided_settings_app(self):
        """
        Test if settings overrided for a specific app is returned if set
        """
        self.assertEqual(app_settings.NB_CONTENTS_KEPT, 10)
        self.assertEqual(app_settings.get_for("NB_CONTENTS_KEPT", "exemple"), 15)
        self.assertEqual(
            app_settings.get_for("NB_CONTENTS_KEPT", "exemple", "quarter"), 15
        )
        self.assertEqual(
            app_settings.get_for("NB_CONTENTS_KEPT", "exemple", "french_educ"), 20
        )
        self.assertEqual(
            app_settings.get_for("NB_CONTENTS_KEPT", "exemple", "content-type"), 30
        )

    @override_settings(
        INSTALLED_APPS=[app for app in settings.INSTALLED_APPS if app != "dalec_prime"]
    )
    def test_missing_dalec_prime(self):
        with self.assertRaisesRegex(
            ValueError, "adding dalec_prime to your INSTALLED_APPS"
        ):
            app_settings.CONTENT_MODEL
        with self.assertRaisesRegex(
            ValueError, "adding dalec_prime to your INSTALLED_APPS"
        ):
            app_settings.FETCH_HISTORY_MODEL

    @override_settings(
        DALEC_CONTENT_MODEL="tests.Content",
        DALEC_FETCH_HISTORY_MODEL="tests.FetchHistory",
    )
    def test_specific_models(self):
        content_model = app_settings.CONTENT_MODEL
        self.assertEqual(content_model, "tests.Content")
        fetch_history_model = app_settings.FETCH_HISTORY_MODEL
        self.assertEqual(fetch_history_model, "tests.FetchHistory")

        content_model = apps.get_model(content_model)
        fetch_history_model = apps.get_model(fetch_history_model)

        self.assertEqual(content_model.objects.count(), 0)
        self.assertEqual(fetch_history_model.objects.count(), 0)

        proxy = ProxyPool.get("exemple")
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
        proxy = ProxyPool.get("exemple")
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

    def test_standard_template_tags(self):
        template = get_template("dalec_tests/test-quarter.html")
        url = reverse(
            "dalec_fetch_content",
            kwargs={"app": "exemple", "content_type": "hour", "channel": "quarter"},
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

        # Check there are still nothind (templatetags must not query the external apps)
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1)
        self.assertEqual(divs[0].string.strip(), "")

        # Let's query the external apps to fetch contents
        proxy = ProxyPool.get("exemple")
        created, updated, deleted = proxy.refresh("hour", "quarter")
        self.assertEqual(created, 10)
        output = template.render()
        soup = BeautifulSoup(output, "html.parser")
        divs = soup.find_all("div")
        self.assertEqual(len(divs), 1 + created)

        div_item = divs[1]
        self.assertEqual(div_item.attrs["class"], ["dalec-item"])
        self.assertEqual(div_item.attrs["data-app"], "exemple")
        self.assertEqual(div_item.attrs["data-content-type"], "hour")
        self.assertEqual(div_item.attrs["data-channel"], "quarter")
        self.assertNotIn("data-channel-object", div_item.attrs)
        last_quarter = self.content_model.objects.latest()
        self.assertEqual(div_item.string.strip(), last_quarter.content_data["id"])

    def test_proxy_fetch_with_channel_object(self):
        proxy = ProxyPool.get("exemple")
        created, updated, deleted = proxy.refresh("hour", "quarter")
        self.assertEqual(created, app_settings.NB_CONTENTS_KEPT)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)

        proxy = ProxyPool.get("exemple")
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
        proxy = ProxyPool.get("exemple")
        created, updated, deleted = proxy.refresh(
            "hour", "quarter", "1985-07-02 21:45:00Z"
        )
        first_ordered = self.content_model.objects.first()
        latest_chrono = self.content_model.objects.latest()
        self.assertEqual(first_ordered.pk, latest_chrono.pk)
        self.assertEqual(first_ordered.content_data["id"], "21h45")

    def test_proxy_extending_rules(self):
        from .proxies.empty_child import EmptyChildProxy

        with self.assertRaisesRegex(ValueError, "extends `dalec.proxy.Proxy`"):
            ProxyPool.register(EmptyChildProxy)

        with self.assertRaisesRegex(ValueError, "`app` attribute"):
            from .proxies.bad_wolf import BadWolfProxy

        from tests.proxies.adiposian import AdiposianProxy

        with self.assertRaisesRegex(ValueError, "already registered"):
            ProxyPool.register(AdiposianProxy)

        with self.assertRaises(NotImplementedError):
            AdiposianProxy().refresh("adipose")

    def test_proxy_pool_autoload(self):
        proxy = ProxyPool.get("exemple")
        from dalec_exemple.proxy import ExempleProxy

        self.assertTrue(isinstance(proxy, ExempleProxy))

        exemple_proxy = ProxyPool.unregister("exemple")
        self.assertEqual(exemple_proxy, proxy)

        with self.assertRaisesRegex(ValueError, "No proxy registered"):
            ProxyPool.get("exemple", autoload=False)

        with self.assertRaisesRegex(ValueError, "No proxy registered"):
            ProxyPool.get("exemple")

        ProxyPool.register(exemple_proxy)
        self.assertEqual(ProxyPool.get("exemple"), proxy)

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
        kwargs = {"app": "exemple", "content_type": "hour", "channel": "quarter"}
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
        kwargs = {"app": "exemple", "content_type": "hour", "channel": "quarter"}
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        response = client.get(url + "?template=faceof")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "face of Boe")

    def test_view_channel_object(self):
        kwargs = {
            "app": "exemple",
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

    def test_ze_final_test(self):
        print("\n\033[0;32mNothing destroyed… \033[0;33mAnormal for Daleks!\033[31;5m")
        print("+" + "-" * 61 + "+")
        print("| " + ("Daleks conquer and destroy!!! " * 2) + "|")
        print("+" + "-" * 61 + "+")
        print(
            """                    /\033[0m\033[0;33m
              ___
      D>=G==='   '.
            |======|
            |======|
        )--/]IIIIII]
           |_______|
           C O O O D
          C O  O  O D
         C  O  O  O  D
         C__O__O__O__D
snd     [_____________]\033[0m

Don't panick, \033[0;32mthis test is successfull\033[0m, Daleks remain Daleks ;)"""
        )


class DalecExempleTests(TestCase):
    @property
    def content_model(self):
        return apps.get_model(app_settings.CONTENT_MODEL)

    @property
    def fetch_history_model(self):
        return apps.get_model(app_settings.FETCH_HISTORY_MODEL)

    def test_proxy_no_channel(self):
        proxy = ProxyPool.get("exemple")
        created, updated, deleted = proxy.refresh("french_educ")
        self.assertEqual(created, 10)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)

    def test_proxy_channel_object(self):
        proxy = ProxyPool.get("exemple")
        created, updated, deleted = proxy.refresh("french_educ", "academy", "Grenoble")
        self.assertEqual(created, 10)
        self.assertEqual(updated, 0)
        self.assertEqual(deleted, 0)
        for c in self.content_model.objects.all():
            self.assertEqual(c.content_data["libelle_academie"], "Grenoble")

    def test_view_no_channel_object(self):
        kwargs = {"app": "exemple", "content_type": "french_educ"}
        url = reverse("dalec_fetch_content", kwargs=kwargs)
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.content_model.objects.count(), 10)

    def test_invalid_channel_or_ct(self):
        proxy = ProxyPool.get("exemple")
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
