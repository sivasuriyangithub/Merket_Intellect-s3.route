from enum import Enum, IntEnum

from django.db import models

from whoweb.contrib.postgres.fields import EmbeddedModelField
from whoweb.search.models import FilteredSearchQuery, SearchExport
from .base import ColdemailBaseModel
from ..api import resource as api
from ..events import UPLOAD_CAMPAIGN_LIST_URL


class CampaignList(ColdemailBaseModel):
    EVENT_REVERSE_NAME = "campaign_list"

    api_class = api.CampaignList

    class OriginOptions(IntEnum):
        USER = 1
        SYSTEM = 2
        INTRO = 3

    name = models.CharField(max_length=255)
    origin = models.PositiveSmallIntegerField(
        choices=[(o.value, o.name) for o in OriginOptions], default=OriginOptions.SYSTEM
    )
    results_fetched = models.DateTimeField(null=True)
    query: FilteredSearchQuery = EmbeddedModelField(FilteredSearchQuery, null=True)
    export = models.ForeignKey(SearchExport, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True, default="")

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

        export = SearchExport.create_from_query(
            billing_seat=self.billing_seat,
            query=query,
            uploadable=True,
            charge=True,
            **kwargs
        )

        self.export = export
        self.save()
        return export

    def publish(self, apply_tasks=True, on_complete=None, export_kwargs=None):
        from whoweb.coldemail.tasks import upload_list, check_for_list_publication

        if self.is_published:
            return

        export = self.export

        if not export and not self.query:
            raise AttributeError("List data source has neither query nor export.")
        elif not export:
            if export_kwargs is None:
                export_kwargs = {}
            export = self.convert_query_to_export(**export_kwargs)

        self.status = self.CampaignObjectStatusOptions.PENDING
        self.save()

        sigs = upload_list.si(self.pk) | check_for_list_publication.si(self.pk)
        if not export.status == export.ExportStatusOptions.COMPLETE:
            sigs = export.processing_signatures(on_complete=on_complete) | sigs

        if apply_tasks:
            sigs.apply_async()
        else:
            return sigs

    def api_upload(self, task_context=None):
        if self.is_published:
            return
        self.log_event(UPLOAD_CAMPAIGN_LIST_URL, task=task_context)
        created = self.api_class.create_by_url(url=self.export.csv.url)
        self.coldemail_id = created.id
        self.status = self.CampaignObjectStatusOptions.PUBLISHED
        self.save()

    @property
    def is_locked(self):
        if super(CampaignList, self).is_locked:
            return True
        return self.is_removed

    def get_recipient_emails(self):
        return (row.email for row in self.export.get_profiles() if row.email)
