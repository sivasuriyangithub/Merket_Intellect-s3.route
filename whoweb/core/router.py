from __future__ import unicode_literals

import json

import requests
from bson import json_util
from django.conf import settings


class Requestor(object):
    @classmethod
    def _act(cls, method, route, *args, **kwargs):
        kwargs.setdefault("timeout", 30)
        encoder = kwargs.pop("encoder", json_util.default)
        if "json" in kwargs and not "data" in kwargs:
            kwargs["data"] = json.dumps(kwargs.pop("json"), default=encoder)
        r = method(route, *args, **kwargs)
        r.raise_for_status()
        return r.json(object_hook=json_util.object_hook)

    @classmethod
    def get(cls, *args, **kwargs):
        return cls._act(requests.get, *args, **kwargs)

    @classmethod
    def post(cls, *args, **kwargs):
        return cls._act(requests.post, *args, **kwargs)


class Router(object):
    @staticmethod
    def xperdata(path):
        return "{}/{}".format(settings.ANALYTICS_SERVICE, path)

    @staticmethod
    def derive_service(path):
        return "{}/{}".format(settings.DERIVE_SERVICE, path)

    def unified_search(self, **kwargs):
        return Requestor.post(self.xperdata("unified_search"), **kwargs)

    def profile_lookup(self, **kwargs):
        return Requestor.post(self.xperdata("2017-09-29/unified_profile"), **kwargs)

    def derive_email(self, **kwargs):
        return Requestor.get(self.derive_service("contact"), **kwargs)

    def update_validations(self, **kwargs):
        return Requestor.post(self.derive_service("validation"), **kwargs)


router = Router()
