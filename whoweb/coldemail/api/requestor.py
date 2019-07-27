import logging

import requests
from django.conf import settings

logger = logging.getLogger("coldEmail")


class ColdEmailApiRequestor(object):
    base_url = "https://www.softwarelogin.com/api.php"

    def __init__(self, key=None, api_base=None):
        self.api_base = api_base or self.base_url
        self.api_key = key or settings.COLD_EMAIL_KEY

    def request(self, area, action, **kwarg_params):
        payload = {
            "apikey": self.api_key,
            "output": "json",
            "area": area,
            "action": action,
        }
        payload.update(kwarg_params)
        response = requests.post(url=self.base_url, data=payload)
        response.raise_for_status()
        return response.json(), self.api_key
