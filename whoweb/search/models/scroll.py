import logging
import time
import uuid
from copy import deepcopy

import requests
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.timezone import now
from model_utils.models import TimeStampedModel

from whoweb.contrib.postgres.fields import EmbeddedModelField
from whoweb.core.router import router
from .embedded import FilteredSearchQuery

logger = logging.getLogger(__name__)
User = get_user_model()


class ScrollKey(TimeStampedModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    def is_valid(self):
        return self.created and (now() - self.created).total_seconds() < 60 * 14


class ScrollSearchManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related("pages")


class ScrollSearch(TimeStampedModel):
    MAX_PAGE_SIZE = 300

    scroll_key = models.ForeignKey(ScrollKey, on_delete=models.SET_NULL, null=True)
    page_size = models.IntegerField(default=MAX_PAGE_SIZE)
    query_hash = models.CharField(max_length=255)
    total = models.IntegerField(null=True)
    query = EmbeddedModelField(
        FilteredSearchQuery, blank=False, default=FilteredSearchQuery
    )
    objects = ScrollSearchManager()

    def scroll_id(self):
        return str(self.scroll_key.pk.hex)

    def refresh_scroll_key(self):
        self.scroll_key.save()

    def page_from_cache(self, page):
        try:
            return self.pages.get(page_number=page).results
        except ScrollSearchPage.DoesNotExist:
            return None

    def send_scroll_search(self):
        filters = deepcopy(self.query.filters)
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

        self.refresh_scroll_key()
        return [result["profile_id"] for result in results.get("results", [])]

    def set_web_ids(self, ids, page):
        ScrollSearchPage.objects.update_or_create(
            scroll=self,
            page_number=page,
            defaults={"results": ids, "key_used": self.scroll_id()},
        )

    def scroll_and_set_cache(self, page):
        ids = self.send_scroll_search()
        self.set_web_ids(ids=ids, page=page)
        return ids

    def page_active(self, page):
        return self.pages.filter(page_number=page, key_used=self.scroll_id()).exists()

    def get_ids_for_page(self, page=0):
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

    def get_page(self, page=0, ids_only=True):
        ids = self.get_ids_for_page(page=page)
        if ids_only:
            return ids
        else:
            full_profiles = self.convert_to_profiles(ids)
            return full_profiles

    def convert_to_profiles(self, ids):
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
        return results


class ScrollSearchPage(TimeStampedModel):
    class Meta:
        ordering = ["page_number"]
        unique_together = (["scroll", "page_number"],)

    scroll = models.ForeignKey(
        ScrollSearch, on_delete=models.CASCADE, related_name="pages"
    )
    page_number = models.IntegerField()
    key_used = models.CharField(max_length=64)
    results = ArrayField(models.CharField(max_length=255, null=True), default=list)
