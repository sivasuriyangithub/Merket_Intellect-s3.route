from django.db import models
from django.forms import model_to_dict

from whoweb.core.router import external_link
from whoweb.contrib.postgres.fields import EmbeddedModelField
from whoweb.search.models import FilteredSearchQuery, SearchExport
from .base import ColdemailBaseModel
from ..api import resource as api
from ..events import UPLOAD_CAMPAIGN_LIST_URL


class CampaignList(ColdemailBaseModel):
    EVENT_REVERSE_NAME = "campaign_list"

    api_class = api.CampaignList

    name = models.CharField(max_length=255)
    origin = models.PositiveSmallIntegerField(
        choices=[(1, "USER"), (2, "SYSTEM"), (3, "INTRO")], default=2
    )
    results_fetched = models.DateTimeField(null=True)
    query: FilteredSearchQuery = EmbeddedModelField(FilteredSearchQuery, null=True)
    export = models.ForeignKey(SearchExport, on_delete=models.SET_NULL, null=True)
    tags = JSONField(null=True)

    @property
    def profiles(self):
        if self.export:
            return self.export.specified_ids
        if self.query:
            return self.query.filters.profiles
        return []

    def convert_query_to_export(self, **kwargs):
        query = self.query.serialize()
        if self.profiles and not self.query.filters.limit:
            query["filters"]["limit"] = len(self.profiles)
            query["filters"]["skip"] = 0

        export = SearchExport.create_from_query(seat=self.seat, query=query, **kwargs)

        self.export = export
        self.save()
        return export

    def publish(self, apply_tasks=True, on_complete=None):
        from ..tasks import upload_list, check_for_list_publication

        if self.is_published:
            return

        export = self.export

        if not export and not self.query:
            raise AttributeError("List data source has neither query nor export.")
        elif not export:
            export = self.convert_query_to_export()

        self.status = self.STATUS.pending
        self.save()

        sigs = upload_list.si(self.pk) | check_for_list_publication.si(self.pk)
        if not export.status == export.STATUS.complete:
            sigs = export.processing_signatures(on_complete=on_complete) | sigs

        if apply_tasks:
            sigs.apply_async()
        else:
            return sigs

    def api_upload(self, task_context=None):
        if self.is_published:
            return
        self.log_event(UPLOAD_CAMPAIGN_LIST_URL, task=task_context)
        url = external_link(self.export.get_named_fetch_url())
        created = self.api_class.create_by_url(url=url)
        self.coldemail_id = created.id
        self.status = self.STATUS.published
        self.save()

    @property
    def is_locked(self):
        if super(CampaignList, self).is_locked:
            return True
        return self.is_removed

    def get_recipient_emails(self):
        return (row.email for row in self.export.get_profiles() if row.email)
