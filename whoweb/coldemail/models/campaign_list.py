from django.db import models
from django.forms import model_to_dict

from whoweb.contrib.postgres.fields import EmbeddedModelField
from .base import ColdemailBaseModel
from ..api import resource as api


class ProfileDataSource(models.Model):
    query = EmbeddedModelField("FilteredSearchQuery")
    export = models.ForeignKey("ListUploadableSearchExport")

    @property
    def profiles(self):
        if self.query:
            return self.query.filters.profiles
        elif self.export:
            return self.export.fetch().specified_ids
        return []

    def convert_query_to_export(self, user="", **kwargs):
        query = model_to_dict(self.query)
        if self.profiles and not self.query.filters.limit:
            query["filters"]["limit"] = len(self.profiles)
            query["filters"]["skip"] = 0

        export = ListUploadableSearchExport.create_from_query(
            user_id=str(user), query=query, **kwargs
        )

        self.export = export
        self.save()
        return export


class CampaignList(ColdemailBaseModel):
    meta = {"collection": "campaignList"}

    api_class = api.CampaignList

    name = models.CharField(max_length=255)
    origin = models.PositiveSmallIntegerField(
        choices=[(1, "USER"), (2, "SYSTEM"), (3, "INTRO")]
    )
    results_fetched = models.DateTimeField()
    data_source = models.ForeignKey(ProfileDataSource, on_delete=models.SET_NULL)

    @property
    def count(self):
        return len(self.profiles)

    @property
    def profiles(self):
        return self.data_source.profiles

    @property
    def with_invites(self):
        return self.data_source.query.with_invites

    @property
    def export(self):
        return self.data_source.export

    @export.setter
    def export(self, value):
        self.data_source.export = value
        self.save()

    def publish(self, apply_tasks=True, on_complete=None):
        from ..tasks import upload_list, check_for_list_publication

        if self.is_published:
            return

        if not self.data_source.export and not self.data_source.query:
            raise AttributeError("List data source has neither query nor export.")
        elif not self.data_source.export:
            self.data_source.convert_query_to_export()

        self.set_pending()

        sigs = upload_list.si(self.pk) | check_for_list_publication.si(self.pk)
        if not self.export.complete:
            sigs = self.export.processing_signatures(on_complete=on_complete) | sigs

        if apply_tasks:
            sigs.apply_async()
        else:
            return sigs

    @sync_return
    @coroutine
    def api_upload(self, is_sync=False, task_context=None):
        self.log_event(UPLOAD_CAMPAIGN_LIST_URL, task=task_context)
        if self.is_published:
            return
        if is_sync:
            created = self.api_class.create_by_url(
                url=self.export.generate_upload_url(), is_sync=True
            )
        else:
            created = yield self.api_class.create_by_url(
                url=self.export.generate_upload_url()
            )
        self.coldemail_id = created.get("listid", created.get("id"))
        self.set_published()
        self.save()
        self.export.log_event(message=COLDLIST_PENDING, data={"list": self.pk})

    def archive(self):
        self.archived = True
        self.archived_at = datetime.utcnow()
        self.save()

    @property
    def is_locked(self):
        if super(CampaignList, self).is_locked:
            return True
        return self.archived

    def get_recipient_emails(self):
        return (
            row["derived_contact"]["email"]
            for row in self.export.get_raw()
            if row.get("derived_contact", {}).get("email")
        )

    def should_refetch_results(self):
        if not self.results_fetched:
            return True
        return self.results_fetched < (datetime.utcnow() - timedelta(hours=3))

    @coroutine
    def fetch_results(self):
        if not self.published:
            return
        api = yield self.api_retrieve()
        cold_objs = yield api.details()
        for cold_obj in cold_objs:
            record = cold_obj.get("record")
            if record and record.get("email"):
                ListResult.objects(email=record.get("email"), list=self).upsert_one(
                    email=record.get("email"),
                    list=self,
                    clicks=len(record.get("clickts", {})),
                    views=len(record.get("viewts", {})),
                    status=record.get("status"),
                )
        self.modify(results_fetched=datetime.utcnow())

    @coroutine
    def get_results(self):
        if self.should_refetch_results():
            yield self.fetch_results()
        raise Return(ListResult.objects(list=self))

    def log_event(self, message, timestamp=None, task=None, **kwargs):
        entry = super(CampaignList, self).log_event(
            message, timestamp=None, task=None, **kwargs
        )
        Campaign.objects(campaign_list=self).update(push__events=entry)
        return entry
