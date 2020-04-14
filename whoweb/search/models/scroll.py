import hashlib
import json
import logging
import time
import uuid

import requests
import typing
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.timezone import now
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel
from pydantic import parse_obj_as

from whoweb.contrib.postgres.fields import EmbeddedModelField
from whoweb.core.router import router
from .profile import ResultProfile
from .embedded import FilteredSearchQuery

logger = logging.getLogger(__name__)
User = get_user_model()


class ScrollSearchManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related("pages")


class ScrollSearch(TimeStampedModel):
    MAX_PAGE_SIZE = 300

    class Meta:
        verbose_name_plural = "Scrolling searches"

    scroll_key = models.UUIDField(default=uuid.uuid4)
    scroll_key_modified = MonitorField(monitor="scroll_key")
    page_size = models.IntegerField(default=MAX_PAGE_SIZE)
    query_hash = models.CharField(max_length=255)
    total = models.IntegerField(null=True, default=None)
    query = EmbeddedModelField(
        FilteredSearchQuery, blank=False, default=FilteredSearchQuery
    )
    objects = ScrollSearchManager()

    def scroll_id(self):
        return str(self.scroll_key.hex)

    @staticmethod
    def get_query_hash(user_id, query) -> str:
        unique_query = f"{query.pk}_{user_id}"
        hash_id = hashlib.sha224(unique_query.encode("utf-8")).hexdigest()
        logger.debug("Hash for query: %s, %s", hash_id, unique_query)
        return hash_id

    @classmethod
    def get_or_create(cls, user_id, query):
        hash = cls.get_query_hash(user_id, query)
        return cls.objects.get_or_create(query_hash=hash, defaults=dict(query=query))

    def touch_scroll_key(self):
        self.scroll_key_modified = now()
        self.save()

    def scroll_key_is_valid(self):
        return (now() - self.scroll_key_modified).total_seconds() < 60 * 14

    def ensure_live(self, force=False):
        if not self.scroll_key_is_valid() or force:
            self.scroll_key = uuid.uuid4()
            self.save()
        return self

    def page_from_cache(self, page: int) -> typing.Optional[typing.List[str]]:
        try:
            return self.pages.get(page_number=page).results
        except ScrollSearchPage.DoesNotExist:
            return None

    def population(self) -> typing.Optional[int]:
        if self.total is None:
            query = self.query.serialize()
            query["ids_only"] = True
            query["filters"]["skip"] = 0
            query["filters"]["limit"] = 1
            results = router.unified_search(json=query, timeout=30)
            self.total = results.get("total_results", 0)
            self.save()
        return self.total

    def send_simple_search(
        self, limit=None, skip=None, ids_only=True
    ) -> typing.Union[typing.List[str], typing.List[ResultProfile]]:
        query = self.query.serialize()
        query["ids_only"] = ids_only
        if limit:
            query["filters"]["limit"] = limit
        if skip:
            query["filters"]["skip"] = skip
        results = router.unified_search(json=query, timeout=120).get("results", [])
        if ids_only:
            return [result["profile_id"] for result in results]
        else:
            return [ResultProfile(**profile) for profile in results]

    def send_scroll_search(self) -> typing.List[str]:
        filters = self.query.serialize()["filters"]
        filters.pop("skip", None)
        filters["scroll"] = self.scroll_id()
        filters["sorted"] = True
        filters["limit"] = self.page_size
        filters["searcher_id"] = self.query.user_id

        query = {"filters": filters, "ids_only": True, "defer": self.query.defer}

        i = 0
        while i < 3:
            try:
                i += 1
                results = router.unified_search(json=query, timeout=120)
            except requests.HTTPError as err:
                if err.response.status_code != 409:
                    raise err
                logger.error(
                    "HTTPError(409) using <ScrollKey %s>. Trying again in 5s.",
                    self.scroll_id(),
                )
                time.sleep(5)
            except requests.Timeout:
                logger.error(
                    "Timeout using <ScrollKey %s>. Trying again in 5s.",
                    self.scroll_id(),
                )
                time.sleep(5)
            else:
                break
        else:
            raise

        self.touch_scroll_key()
        return [result["profile_id"] for result in results.get("results", [])]

    def set_web_ids(self, ids, page):
        ScrollSearchPage.objects.update_or_create(
            scroll=self,
            page_number=page,
            defaults={"results": ids, "key_used": self.scroll_id()},
        )

    def scroll_and_set_cache(self, page) -> typing.List[str]:
        ids = self.send_scroll_search()
        self.set_web_ids(ids=ids, page=page)
        return ids

    def page_active(self, page):
        return self.pages.filter(page_number=page, key_used=self.scroll_id()).exists()

    def get_ids_for_page(self, page=0) -> typing.List[str]:
        if self.page_from_cache(page) is not None:
            return self.page_from_cache(page)

        for p in range(page):
            if (
                self.page_from_cache(p) == []
            ):  # short circuit if search is known exhausted.
                return []

        for most_recent_active_page in range(page, -2, -1):
            if self.page_active(most_recent_active_page):
                break

        for p in range(most_recent_active_page + 1, page + 1):
            ids = self.scroll_and_set_cache(p)
            if not ids:
                break

        return self.page_from_cache(page) or []

    def get_profiles_for_page(self, page=0) -> typing.List[ResultProfile]:
        ids = self.get_ids_for_page(page=page)
        return self.convert_to_profiles(ids)

    def convert_to_profiles(self, ids: typing.List[str]) -> typing.List[ResultProfile]:
        results = []
        for block in [ids[x : x + 100] for x in range(0, len(ids), 100)]:
            id_query = {
                "filters": {
                    "required": [{"field": "_id", "value": block, "truth": True}],
                    "skip": 0,
                    "limit": len(block),
                },
                "defer": ["degree_levels", "company_counts"],
            }
            result = router.unified_search(json=id_query, timeout=90)
            results.extend(result.get("results", []))
        return parse_obj_as(typing.List[ResultProfile], results)


class ScrollSearchPage(TimeStampedModel):
    class Meta:
        ordering = ["scroll", "page_number"]
        unique_together = (["scroll", "page_number"],)

    scroll = models.ForeignKey(
        ScrollSearch, on_delete=models.CASCADE, related_name="pages"
    )
    page_number = models.IntegerField()
    key_used = models.CharField(max_length=64)
    results = ArrayField(models.CharField(max_length=255, null=True), default=list)
