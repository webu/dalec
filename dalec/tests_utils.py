# Standard libs
from importlib import reload

# Django imports
from django.apps import apps

# DALEC imports
from dalec import settings as app_settings
from dalec.proxy import ProxyPool


class DalecTestCaseMixin:
    def tearDown(self) -> None:
        """
        reload settings after a test which could have overrided settings
        """
        reload(app_settings)

    @property
    def content_model(self) -> app_settings.CONTENT_MODEL:
        return apps.get_model(app_settings.CONTENT_MODEL)

    @property
    def fetch_history_model(self) -> app_settings.FETCH_HISTORY_MODEL:
        return apps.get_model(app_settings.FETCH_HISTORY_MODEL)

    def test_invalid_fetch(self) -> None:
        apps = ProxyPool.get_registered_apps()
        for app in apps:
            proxy = ProxyPool.get(app)
            with self.assertRaises(ValueError):  # type: ignore
                proxy.refresh(content_type="dr_who_name")

    def test_ze_final_test(self) -> None:
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
