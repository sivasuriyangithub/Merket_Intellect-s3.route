import logging
import time
from calendar import timegm

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.timezone import now

from whoweb.core.router import router
from .reply import ReplyTo
from .base import ColdemailBaseModel
from .campaign_list import CampaignList
from .campaign_message import CampaignMessage
from ..api import resource as api
from ..api.error import ColdEmailError
from ..events import UPLOAD_CAMPAIGN, PUBLICATION_SIGNATURES

logger = logging.getLogger()


class ColdCampaign(ColdemailBaseModel):
    api_class = api.Campaign
    EVENT_REVERSE_NAME = "campaign"

    message = models.ForeignKey(CampaignMessage, on_delete=models.SET_NULL, null=True)
    campaign_list = models.ForeignKey(
        CampaignList, on_delete=models.SET_NULL, null=True
    )
    title = models.CharField(max_length=255)
    from_name = models.CharField(max_length=255)
    from_address = models.CharField(max_length=255)
    send_time = models.DateTimeField(null=True)
    reply_routes = GenericRelation(ReplyTo, related_query_name="campaign")

    # stats
    stats_fetched = models.DateTimeField(null=True)
    sent = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    unique_clicks = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    optouts = models.PositiveIntegerField(default=0)
    good = models.PositiveIntegerField(default=0)
    start_time = models.CharField(max_length=255)
    end_time = models.CharField(max_length=255)

    click_log = JSONField(null=True, blank=True)
    open_log = JSONField(null=True, blank=True)
    good_log = JSONField(null=True, blank=True)
    reply_log = JSONField(null=True, blank=True)

    def api_upload(self, task_context=None):
        self.log_event(UPLOAD_CAMPAIGN, task=task_context)
        if self.is_published:
            return
        date = (
            timegm(self.send_time.utctimetuple())
            if self.send_time
            else int(time.time() + 300)
        )
        create_args = dict(
            title=self.title,
            listid=self.campaign_list.coldemail_id,  # refresh
            subject=self.message.subject.encode("utf-8"),
            messageid=self.message.coldemail_id,
            date=date,
            whoisid=settings.COLD_EMAIL_WHOIS,
            profileid=settings.COLD_EMAIL_PROFILEID,
            fromaddress=self.from_address,
            fromname=self.from_name,
            suppressionid=settings.COLD_EMAIL_SUPRESSIONLIST,
            dklim=1,
            viewaswebpage=0,
            debug=1,
        )
        cold_campaign = self.api_create(**create_args)
        self.coldemail_id = cold_campaign.id
        self.status = self.STATUS.published
        self.save()

    def publish(self, apply_tasks=True, on_complete=None):
        from whoweb.coldemail.tasks import update_validation

        if self.is_locked:
            return

        self.status = self.STATUS.pending
        self.save()

        message_sig = self.message.publish(apply_tasks=False)

        export_kwargs = {}
        if reply_route := self.reply_routes.first():
            export_kwargs["extra_columns"] = {
                "route_id": reply_route.coldemail_route_id
            }

        list_sigs = self.campaign_list.publish(
            apply_tasks=False, on_complete=on_complete, export_kwargs=export_kwargs
        )

        post_send_sigs = update_validation.si(self.pk, should_orphan=True)

        if message_sig and list_sigs:
            publish_sigs = message_sig | list_sigs | post_send_sigs
        elif list_sigs:
            publish_sigs = list_sigs | post_send_sigs
        elif message_sig:
            publish_sigs = message_sig | post_send_sigs
        else:
            publish_sigs = post_send_sigs

        self.log_event(PUBLICATION_SIGNATURES, data={"sigs": repr(publish_sigs)})
        if publish_sigs and apply_tasks:
            publish_sigs.apply_async()
        return publish_sigs

    def pause(self):
        if self.status == self.STATUS.published:
            try:
                cold = self.api_retrieve()
                success = cold.pause()
            except ColdEmailError:
                success = False
            if success:
                self.status = self.STATUS.paused
                self.save()
                return True
        return self.status == self.STATUS.paused

    def resume(self):
        if self.status == self.STATUS.paused:
            cold = self.api_retrieve()
            success = cold.resume()
            if success:
                self.status = self.STATUS.published
                self.save()
                return True
        return self.status != self.STATUS.paused

    def delete(self, using=None, pause_first=True, *args, **kwargs):
        if pause_first:
            self.pause()
        return super().delete(using=using, *args, **kwargs)

    def update_validation(self):
        campaign_list = self.campaign_list.api_retrieve()
        if campaign_list:
            good_emails = campaign_list.good_log(is_sync=True) or {}
            good_log = self._annotate_web_ids(good_emails).get("log", [])
            bad_emails = campaign_list.bad_log(is_sync=True) or {}
            bad_log = self._annotate_web_ids(bad_emails).get("log", [])
        else:
            good_log = []
            bad_log = []
        validations = []
        for entry in good_log:
            if not ("email" in entry and "web_id" in entry):
                continue
            validations.append(
                {"email": entry["email"], "profile_id": entry["web_id"], "grade": "A+"}
            )
        for entry in bad_log:
            if not ("email" in entry and "web_id" in entry):
                continue
            validations.append(
                {"email": entry["email"], "profile_id": entry["web_id"], "grade": "F-"}
            )

        # return to cache
        upload_limit = 250
        for i in range(0, len(validations), upload_limit):
            try:
                router.update_validations(
                    json={"bulk_validations": validations[i : i + upload_limit]},
                    timeout=90,
                )
            except Exception as e:
                logger.exception("Error setting validation cache: %s " % e)
                continue
        return len(good_log), len(bad_log)

    def fetch_stats(self):
        campaign = self.api_retrieve()
        if not campaign:
            return
        if hasattr(campaign, "error"):
            logger.error(campaign.error)
            return

        if not self.email_lookups.exists():
            self.populate_webprofile_id_lookup()
            self.refresh_from_db()

        click_log = campaign.click_log(is_sync=True) or {}
        open_log = campaign.open_log(is_sync=True) or {}

        click_log = self._annotate_web_ids(click_log)
        open_log = self._annotate_web_ids(open_log)

        campaign_list: api.CampaignList = self.campaign_list.api_retrieve()
        if campaign_list:
            good_emails = campaign_list.good_log() or {}
            good_log = self._annotate_web_ids(good_emails)
        else:
            good_log = {}

        unique_clicks = int(click_log.uniquerecords or 0)
        unique_views = int(open_log.uniquerecords or 0)

        self.stats_fetched = now()
        self.sent = int(campaign.sent)
        self.clicks = int(campaign.clicks)
        self.views = int(campaign.views)
        self.optouts = int(campaign.optouts)
        self.good = int(campaign.good)
        self.start_time = str(campaign.starttime)
        self.end_time = str(campaign.endtime)
        self.unique_clicks = unique_clicks
        self.unique_views = unique_views
        self.click_log = click_log
        self.open_log = open_log
        self.good_log = good_log
        self.save()

    def populate_webprofile_id_lookup(self):
        CampaignEmailLookup.objects.bulk_create(
            [
                CampaignEmailLookup(campaign=self, email=email, web_id=web_id)
                for (
                    email,
                    web_id,
                ) in self.campaign_list.export.generate_email_id_pairs()
            ]
        )

    def _annotate_web_ids(self, cold_log):
        log = cold_log.log
        lookup = {el.email: el.web_id for el in self.email_lookups.all()}
        for entry in log:
            try:
                entry["web_id"] = lookup[entry["email"]]
            except KeyError:
                continue

        cold_log.log = log
        return cold_log

    def log_reply(self, email):
        lookup = self.email_lookups.get(email=email)
        entry = dict(email=email, web_id=lookup.web_id)
        self.reply_log.append(entry)
        self.save()


class CampaignEmailLookup(models.Model):
    class Meta:
        indexes = (models.Index(fields=("campaign",)),)

    campaign = models.ForeignKey(
        ColdCampaign, on_delete=models.CASCADE, related_name="email_lookups"
    )
    email = models.EmailField()
    web_id = models.CharField(max_length=160)
