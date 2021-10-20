from datetime import timedelta
from typing import Dict
import requests

from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from dalec.proxy import Proxy


class ExempleProxy(Proxy):
    """
    Just a proxy exemple wich just fetch the last :
    * quarter: quarters of an hour from "now" (no channel available)
    * french_educ: last updated establishments of french national education. Available channels:
        * academy: retrieve for a specific academy name (eg: « Amiens »)
    """

    def _fetch(slef, nb:int, content_type:str, channel:str, channel_object:str) -> Dict[str, dict]:
        if content_type == "quarter":
            if channel or channel_object:
                raise ValueError("quarter does not support channels")
            return self._fetch_quarter(nb)
        if content_type == "french_educ":
            return self._fetch_french_educ(nb, channel, channel_object)
        raise ValueError("Invalid content_type %s" % content_type)

    def _fetch_quarter(self, nb):
        i = 0
        contents = {}
        last_quarter = now()
        if last_quarter.minute > 45:
            last_quarter.minute = 45
        elif last_quarter.minute > 30:
            last_quarter.minute = 30
        elif last_quarter.minute > 15:
            last_quarter.minute = 15
        else:
            last_quarter.minute = 0

        while i < nb:
            quarter = last_quarter - timedelta(seconds=(900 * i))
            i += 1
            hh_mm = "%02dh%02d" % (quarter.hour, quarter.minute, )
            contents[hh_mm] = {
                # required attributes
                "id": quarter,
                "last_update_dt": quarter,
                "creation_dt": quarter,
                # some other data
                "full_representation": str(quarter),
                "night": quarter.hour < 6 or quarter.hour > 22,
            }
        return contents

    def _fetch_quarter(self, nb, channel=None, channel_object=None):
        params = {
            "order_by": "date_maj_ligne desc",
            "limit": nb,
            "offset": 0,
        }
        if channel:
            if channel != "academy":
                raise ValueError("Invalid channel %s" % channel)
            channel_object = channel_object.strip()
            if not channel_object:
                raise ValueError("Invalid channel object")
            params["where"] = "libelle_academie =\"%s\"" % channel_object
        resp = requests.get(
            "https://data.education.gouv.fr/api/v2/catalog/datasets/fr-en-annuaire-education/records",
            params=params
        )
        resp.raise_for_status()
        contents = {}
        records = resp.json().get("records", [])
        for record in records:
            record = record["record"]["fields"]
            id = record["identifiant_de_l_etablissement"]
            contents[id] = {
                # set all fields
                **record,
                # and add our own required fields
                "id": id,
                "last_update_dt": parse_datetime('%s 00:00:00Z' % record["date_maj_ligne"]),
                "creation_dt": parse_datetime('%s 00:00:00Z' % record["date_ouverture"]),
            }
        return contents
