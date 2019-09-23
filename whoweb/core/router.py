from __future__ import unicode_literals

import json
from datetime import timedelta

import requests
from bson import json_util
from django.conf import settings
from requests_cache import CachedSession


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

    @classmethod
    def with_cache(cls, method="GET", cache_expires=None, *args, **kwargs):
        if cache_expires is None:
            cache_expires = timedelta(hours=1).total_seconds()
        elif isinstance(cache_expires, timedelta):
            cache_expires = cache_expires.total_seconds()
        s = CachedSession(expire_after=cache_expires)
        if method == "GET":
            return cls._act(s.get, *args, **kwargs)
        elif method == "POST":
            return cls._act(s.post, *args, **kwargs)


class Router(object):
    @staticmethod
    def xperdata(path):
        return "{}/{}".format(settings.ANALYTICS_SERVICE, path)

    @staticmethod
    def xperweb(path):
        return "{}/{}".format(settings.XPERWEB_URI, path)

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

    def make_exportable_invite_key(self, **kwargs):
        return Requestor.with_cache(
            self.xperweb("api/v1/invite/keys"),
            method="POST",
            cache_expires=timedelta(days=1),
            json=kwargs,
        )


router = Router()


def external_link(uri):
    return f"{settings.PUBLIC_ORIGIN}/api/v2/{uri}"
