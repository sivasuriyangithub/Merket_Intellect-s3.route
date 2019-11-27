from __future__ import unicode_literals

import json
import uuid
from datetime import timedelta

import requests
from bson import json_util
from django.conf import settings
from requests_cache import CachedSession

GET = requests.get
POST = requests.post


class Requestor(object):
    @classmethod
    def _request(cls, requestfunc, url, params=None, **kwargs):
        kwargs.setdefault("timeout", 30)
        encoder = kwargs.pop("encoder", json_util.default)
        if "json" in kwargs and not "data" in kwargs:
            kwargs["data"] = json.dumps(kwargs.pop("json"), default=encoder)
        r = requestfunc(url, params=params, **kwargs)
        r.raise_for_status()
        return r.json(object_hook=json_util.object_hook)

    @classmethod
    def request(cls, method, url, params=None, cache=False, **kwargs):
        kwargs.setdefault("headers", {})
        kwargs["headers"]["X-Request-Id"] = kwargs.pop("request_id", str(uuid.uuid4()))
        producer = kwargs.pop("request_producer", None)
        if producer:
            kwargs["headers"]["X-Request-Producer"] = producer

        if cache:
            return cls.with_cache(method, url, params=params, **kwargs)
        else:
            return cls._request(method, url, params=params, **kwargs)

    @classmethod
    def with_cache(cls, method, url, cache_expires=None, **kwargs):
        if cache_expires is None:
            cache_expires = timedelta(hours=1).total_seconds()
        elif isinstance(cache_expires, timedelta):
            cache_expires = cache_expires.total_seconds()
        s = CachedSession(expire_after=cache_expires)
        if method == GET:
            return cls._request(s.get, url, **kwargs)
        elif method == POST:
            return cls._request(s.post, url, **kwargs)


class Router(object):
    @staticmethod
    def xperdata(path, method, **kwargs):
        return Requestor.request(
            method=method,
            url="{}/{}".format(settings.ANALYTICS_SERVICE, path),
            **kwargs,
        )

    @staticmethod
    def xperweb(path, method, **kwargs):
        return Requestor.request(
            method=method, url="{}/{}".format(settings.XPERWEB_URI, path), **kwargs
        )

    @staticmethod
    def derive_service(path, method, **kwargs):
        return Requestor.request(
            method=method, url="{}/{}".format(settings.DERIVE_SERVICE, path), **kwargs
        )

    # xperdata routes
    def unified_search(self, **kwargs):
        return self.xperdata("unified_search", POST, **kwargs)

    def profile_lookup(self, **kwargs):
        return self.xperdata("2017-09-29/unified_profile", POST, **kwargs)

    # derive routes
    def derive_email(self, **kwargs):
        return self.derive_service("contact", GET, **kwargs)

    def update_validations(self, **kwargs):
        return self.derive_service("validation", POST, **kwargs)

    # xperweb routes
    def make_exportable_invite_key(self, **kwargs):
        return self.xperweb(
            "internal/invite/keys",
            method=POST,
            cache=True,
            cache_expires=timedelta(days=1),
            json=kwargs,
        )

    def alert_xperweb_export_completion(self, idempotency_key, amount, **kwargs):
        return self.xperweb(
            "internal/export/settleup",
            method=POST,
            json=dict(idempotency_key=idempotency_key, amount=amount),
            **kwargs,
        )


router = Router()


def external_link(uri):
    return f"{settings.PUBLIC_ORIGIN}{uri}"
