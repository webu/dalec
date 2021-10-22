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

    app = "exemple"

    def _fetch(
        self, nb: int, content_type: str, channel: str, channel_object: str
    ) -> Dict[str, dict]:
        if content_type == "hour":
            if not channel or channel not in ("quarter", "half"):
                raise ValueError(
                    "%s requires a channel ('quarter' or 'half')" % content_type
                )
            return self._fetch_hour(nb, channel, channel_object)
        if content_type == "french_educ":
            return self._fetch_french_educ(nb, channel, channel_object)
        raise ValueError("Invalid content_type %s" % content_type)

    def _fetch_hour(self, nb, channel, channel_object):
        i = 0
        contents = {}
        if channel_object:
            last_dt = parse_datetime(channel_object)
        else:
            last_dt = now()
        minutes = 15 if channel == "quarter" else 30
        last_dt = last_dt - timedelta(minutes=last_dt.minute % minutes)
        last_dt.replace(second=0, microsecond=0)

        while i < nb:
            new_dt = last_dt - timedelta(minutes=(minutes * i))
            i += 1
            hh_mm = "%02dh%02d" % (new_dt.hour, new_dt.minute)
            contents[hh_mm] = {
                # required attributes
                "id": hh_mm,
                "last_update_dt": new_dt,
                "creation_dt": new_dt,
                # some other data
                "full_representation": str(new_dt),
                "night": new_dt.hour < 6 or new_dt.hour > 22,
            }
        return contents

    def _fetch_french_educ(self, nb, channel=None, channel_object=None):
        params = {"order_by": "date_maj_ligne desc", "limit": nb, "offset": 0}
        if channel:
            if channel != "academy":
                raise ValueError("Invalid channel %s" % channel)
            channel_object = channel_object.strip()
            if not channel_object:
                raise ValueError("Invalid channel object")
            params["where"] = 'libelle_academie ="%s"' % channel_object
        resp = requests.get(
            "https://data.education.gouv.fr/api/v2/catalog/datasets/fr-en-annuaire-education/records",
            params=params,
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
                "last_update_dt": parse_datetime(
                    "%s 00:00:00Z" % record["date_maj_ligne"]
                ),
                "creation_dt": parse_datetime(
                    "%s 00:00:00Z" % record["date_ouverture"]
                ),
            }
        return contents
