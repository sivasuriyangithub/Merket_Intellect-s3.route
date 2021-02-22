import uuid
from datetime import timedelta
from typing import List

from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.utils.timezone import now
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import SoftDeletableModel, TimeStampedModel
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from tagulous.models import TagField

from whoweb.accounting.models import Transaction, MatchType
from whoweb.campaigns.events import (
    PUBLISH_DRIP_CAMPAIGN,
    PUBLISH_CAMPAIGN,
    CAMPAIGN_SIGNATURES,
    PAUSE_CAMPAIGN,
    RESUME_CAMPAIGN,
)
from whoweb.coldemail.models import (
    ReplyTo,
    ColdEmailTagModel,
    ColdCampaign,
    CampaignList,
    CampaignMessage,
    CampaignMessageTemplate,
)
from whoweb.contrib.fields import ObscureIdMixin
from whoweb.contrib.polymorphic.managers import PolymorphicSoftDeletableManager
from whoweb.contrib.postgres.fields import EmbeddedModelField
from whoweb.core.models import EventLoggingModel
from whoweb.payments.models import BillingAccountMember
from whoweb.search.models import FilteredSearchQuery, ScrollSearch
from whoweb.users.models import Seat

PAUSE_HEX = uuid.UUID(int=0)


class DripTooSoonError(Exception):
    def __init__(self, countdown=3600):
        self.countdown = countdown


class SendingRule(models.Model):
    class Meta:
        unique_together = ("runner", "index")
        ordering = ("runner", "index")

    TRIGGER = Choices(
        (0, "datetime", "At a specified time"),
        (1, "timedelta", "Seconds after previous"),
        (2, "delay", "A short delay after creation"),
    )
    runner = models.ForeignKey("BaseCampaignRunner", on_delete=models.CASCADE)
    message_template = models.ForeignKey(
        CampaignMessageTemplate,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
    )
    message = models.ForeignKey(CampaignMessage, on_delete=models.CASCADE)
    index = (
        models.PositiveIntegerField()
    )  # index 0 must be DELAY or DATETIME, see method `send_time_for_rule`
    trigger = models.PositiveSmallIntegerField(choices=TRIGGER, default=TRIGGER.delay)

    send_datetime = models.DateTimeField(null=True, blank=True)
    send_delta = models.PositiveIntegerField(null=True, blank=True)
    include_previous = models.BooleanField(default=False, blank=True)

    def task_timing_args(self):
        if self.trigger == SendingRule.TRIGGER.datetime:
            return {"eta": self.send_datetime - timedelta(seconds=600)}
        elif self.trigger == SendingRule.TRIGGER.timedelta:
            return {"countdown": self.send_delta - 600}
        elif self.trigger == SendingRule.TRIGGER.delay:
            return {"countdown": 300}
        return {}

    def get_next_by_index(self):
        return SendingRule.objects.filter(
            runner=self.runner, index__gt=self.index
        ).first()


class DripRecord(models.Model):
    class Meta:
        unique_together = ("runner", "root", "order")
        ordering = ("runner", "root", "order")

    runner = models.ForeignKey("BaseCampaignRunner", on_delete=models.CASCADE)
    root = models.ForeignKey(
        ColdCampaign, on_delete=models.CASCADE, related_name="in_drip_roots"
    )
    drip = models.ForeignKey(
        ColdCampaign, on_delete=models.CASCADE, related_name="in_drip_drips"
    )
    order = models.PositiveSmallIntegerField(default=0)

    @property
    def sending_rule(self):
        return SendingRule.objects.get(runner=self.runner, index=self.order)


class BaseCampaignRunner(
    ObscureIdMixin,
    EventLoggingModel,
    TimeStampedModel,
    SoftDeletableModel,
    PolymorphicModel,
):
    MIN_DRIP_DELAY = timedelta(days=1)
    STATUS = Choices(
        (0, "draft", "Draft"),
        (2, "pending", "Pending"),
        (4, "paused", "Paused"),
        (8, "published", "Published"),
        (16, "running", "Running"),
        (32, "sending", "Sending"),
        (128, "complete", "Complete"),
    )

    should_charge = True
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, null=True, blank=True)
    billing_seat = models.ForeignKey(
        BillingAccountMember, on_delete=models.CASCADE, null=True, blank=True
    )

    messages = models.ManyToManyField(CampaignMessage, through=SendingRule)
    drips = models.ManyToManyField(
        ColdCampaign,
        related_name="+",
        through=DripRecord,
        through_fields=("runner", "drip"),
    )

    campaigns = models.ManyToManyField(ColdCampaign)
    title = models.CharField(max_length=255)
    query = EmbeddedModelField(
        FilteredSearchQuery, blank=False, default=FilteredSearchQuery
    )
    scroll = models.ForeignKey(ScrollSearch, on_delete=models.SET_NULL, null=True)

    budget = models.PositiveIntegerField()

    status = models.IntegerField(
        "status", db_index=True, choices=STATUS, blank=True, default=STATUS.draft
    )
    status_changed = MonitorField("status changed", monitor="status")
    is_removed_changed = MonitorField("deleted at", monitor="is_removed")
    published = MonitorField(
        monitor="status", when=[STATUS.published], null=True, default=None, blank=True
    )

    tracking_params = JSONField(default=dict, null=True, blank=True)
    tags = TagField(to=ColdEmailTagModel, blank=True)

    from_name = models.CharField(max_length=255, default="", blank=True)

    # Enforce only 1 active signature chain in celery,
    # enabling republishing via .resume(), even with a pending canvas.
    run_id = models.UUIDField(null=True, blank=True)

    objects = PolymorphicSoftDeletableManager()
    all_objects = PolymorphicManager()

    def __str__(self):
        return f"{self.__class__.__name__} {self.pk} ({self.get_status_display()})"

    def sending_rules(self):
        return SendingRule.objects.filter(runner=self)

    def drip_records(self):
        return DripRecord.objects.filter(runner=self)

    @property
    def transactions(self):
        exports = [
            campaign.campaign_list.export
            for campaign in self.campaigns.all().select_related("campaign_list__export")
        ]
        return Transaction.objects.filter_by_related_objects(
            exports, match_type=MatchType.ANY
        )

    def get_next_rule(self, following: ColdCampaign):
        return (
            self.sending_rules()
            .filter(message=following.message)
            .first()
            .get_next_by_index()
        )

    def create_next_drip_list(self, root_campaign, following):
        export = following.campaign_list.export
        export.pk = None
        export.save()
        self.remove_reply_rows(export=export, root_campaign=root_campaign)
        return CampaignList.objects.create(export=export, origin=2, seat=self.seat)

    # TODO: lock
    def create_next_drip_campaign(
        self,
        root_campaign: ColdCampaign,
        following: ColdCampaign,
        campaign_kwargs=None,
        *args,
        **kwargs,
    ):
        rule = self.get_next_rule(following=following)
        if not rule:
            return
        if self.drip_records().filter(root=root_campaign).count() >= rule.index:
            return

        # If intended send time is absolute,
        # and the CURRENT time is not after the last campaign send time plus a minimum buffer,
        # fail the list/export creation
        if rule.trigger == SendingRule.TRIGGER.datetime:
            delta = now() - following.send_time
            if delta < self.MIN_DRIP_DELAY:
                remaining = self.MIN_DRIP_DELAY - max(timedelta(0), delta)
                raise DripTooSoonError(countdown=int(remaining.total_seconds()))

        campaign_list = self.create_next_drip_list(
            root_campaign=root_campaign, following=following
        )
        if not campaign_list:
            return

        if campaign_kwargs is None:
            campaign_kwargs = {}

        if self.billing_seat:
            campaign_kwargs.setdefault("billing_seat", self.billing_seat)
        title = campaign_kwargs.setdefault("title", self.title)
        campaign_kwargs.update(
            message=rule.message,
            send_time=now() + timedelta(seconds=300),
            campaign_list=campaign_list,
            title="{} - m{}".format(title, rule.index),
        )
        cold_campaign = ColdCampaign.objects.create(**campaign_kwargs)
        cold_campaign = self.set_reply_fields(cold_campaign)
        DripRecord.objects.create(
            runner=self, root=root_campaign, drip=cold_campaign, order=rule.index
        )
        return cold_campaign

    def publish_drip(
        self,
        root_campaign: ColdCampaign,
        following: ColdCampaign,
        task_context=None,
        *args,
        **kwargs,
    ):

        drip_campaign = self.create_next_drip_campaign(
            root_campaign=root_campaign, following=following, *args, **kwargs
        )
        if drip_campaign:
            publish_sigs = drip_campaign.publish(apply_tasks=False)
        else:
            publish_sigs = None
        if publish_sigs:
            drip_sigs = self.drip_tasks(
                root_campaign=root_campaign, following=drip_campaign
            )
            if drip_sigs:
                publish_sigs |= drip_sigs
        self.log_event(
            PUBLISH_DRIP_CAMPAIGN, task=task_context, data={"sigs": repr(publish_sigs)}
        )
        if publish_sigs:
            transaction.on_commit(publish_sigs.apply_async)

    def drip_tasks(
        self,
        root_campaign: ColdCampaign,
        following: ColdCampaign,
        campaign_kwargs=None,
        run_id=None,
        *args,
        **kwargs,
    ):
        """
        :rtype: celery.canvas.Signature
        """
        from whoweb.campaigns.tasks import publish_drip, ensure_stats

        rule = self.get_next_rule(following=following)
        if not rule:
            return

        sigs = ensure_stats.signature(
            args=(self.pk,), immutable=True, **rule.task_timing_args(),
        ) | publish_drip.si(
            self.pk,
            root_pk=root_campaign.pk,
            following_pk=following.pk,
            campaign_kwargs=campaign_kwargs,
            run_id=run_id,
            *args,
            **kwargs,
        )
        return sigs

    def remove_reply_rows(self, export, root_campaign: ColdCampaign):
        responders = self.get_responders(root_campaign=root_campaign)
        for page in export.pages.filter(data__isnull=False).iterator(chunk_size=1):
            profiles = self.get_profiles(raw=page.data)
            page.data = [
                profile.dict() for profile in profiles if profile.id not in responders
            ]
            page.count = len(page.data)
            page.id = None
            page.export = export
            page.save()
        return export

    def get_responders(self, root_campaign: ColdCampaign):
        responders = set()
        campaigns: List[ColdCampaign] = [
            record.drip
            for record in DripRecord.objects.filter(
                runner=self,
                root=root_campaign,
                drip__status__gte=ColdCampaign.STATUS.published,
                drip__stats_fetched__isnull=False,
            ).prefetch_related("drip")
        ]
        campaigns.append(root_campaign)

        for campaign in campaigns:
            for log_entry in campaign.click_log.get("log", []):
                if "web_id" in log_entry:
                    responders.add(log_entry["web_id"])
            replies = campaign.reply_log or []
            for log_entry in replies:
                if "web_id" in log_entry:
                    responders.add(log_entry["web_id"])
        return responders

    def ensure_search_interface(self, force=False):
        if self.scroll is None:
            search, created = ScrollSearch.get_or_create(
                query=self.query, user_id=self.seat_id
            )
            self.scroll = search
            self.save()
        return self.scroll.ensure_live(force=force)

    def set_reply_fields(self, campaign):
        if self.from_name:
            defaults = {"from_name": self.from_name}
        else:
            defaults = {}
        instance, created = ReplyTo.get_or_create_with_api(
            replyable_object=campaign, defaults=defaults
        )
        campaign.from_address = instance.from_address
        campaign.from_name = instance.from_name
        campaign.save()
        return campaign

    def send_times(self):
        for campaign in self.campaigns.all():
            if campaign.status == ColdCampaign.STATUS.pending:
                yield campaign.modified
            elif campaign.status == ColdCampaign.STATUS.published:
                yield campaign.published
            continue

    @property
    def last_sent_campaign(self):
        return (
            self.campaigns.filter(status__gte=ColdCampaign.STATUS.published)
            .order_by("-send_time")
            .first()
        )

    @property
    def last_sent_export(self):
        if most_recent := self.last_sent_campaign:
            return most_recent.campaign_list.export

    def create_campaign_list(self, *args, **kwargs):
        return CampaignList.objects.create(
            query=self.query, origin=2, billing_seat=self.billing_seat
        )

    def create_campaign(self, **campaign_kwargs):
        first_message_rule = self.sending_rules().first()

        if self.billing_seat:
            campaign_kwargs.setdefault("billing_seat", self.billing_seat)
        title = campaign_kwargs.setdefault("title", self.title)
        campaign_kwargs.update(
            message=first_message_rule.message,
            send_time=first_message_rule.send_datetime,
            campaign_list=self.create_campaign_list(),
            title="{} - m{}".format(title, first_message_rule.index),
        )
        cold_campaign = ColdCampaign.objects.create(**campaign_kwargs)
        self.set_reply_fields(cold_campaign)
        self.campaigns.add(cold_campaign)
        return cold_campaign

    # @staticmethod
    # def save_all_inbox_messages(campaign_list, source, message_id):
    #     for email in campaign_list.get_recipient_emails():
    #         inbox = Inbox.find(email=email)
    #         try:
    #             Inbox.objects.get(pk=inbox.pk,
    #                               messages__match={'source': source, 'campaign_message': message_id})
    #         except mongoengine.DoesNotExist:
    #             inbox.modify(
    #                 add_to_set__messages=InboxMessage(id=ObjectId(), campaign_message=message_id, source=source))

    def publish(
        self,
        apply_tasks=True,
        on_complete=None,
        task_context=None,
        with_campaign=None,
        *args,
        **kwargs,
    ):
        """
        :rtype: (celery.canvas.Signature | celery.result.AsyncResult | None,  Campaign | None)
        """
        from whoweb.campaigns.tasks import set_published, ensure_stats

        self.log_event(PUBLISH_CAMPAIGN, task=task_context)
        if with_campaign:
            campaign = with_campaign
        else:
            campaign = self.create_campaign()
        if not campaign:
            return None, None
        if publish_sigs := campaign.publish(apply_tasks=False, on_complete=on_complete):
            if self.run_id is None:
                self.run_id = uuid.uuid4()
                self.status = self.STATUS.pending
                self.save()

            publish_sigs |= set_published.si(pk=self.pk, run_id=self.run_id)
            if drip_sigs := self.drip_tasks(
                root_campaign=campaign, following=campaign, run_id=self.run_id
            ):
                publish_sigs |= drip_sigs
            else:
                publish_sigs |= ensure_stats.signature(
                    args=(self.pk,),
                    immutable=True,
                    eta=campaign.send_time + timedelta(hours=12),
                ) | ensure_stats.signature(
                    args=(self.pk,),
                    immutable=True,
                    eta=campaign.send_time + timedelta(days=1),
                )
            # Also get updated stats periodically as more respondent interactions occur.
            publish_sigs |= (
                ensure_stats.signature(
                    args=(self.pk,),
                    immutable=True,
                    eta=campaign.send_time + timedelta(days=2),
                )
                | ensure_stats.signature(
                    args=(self.pk,),
                    immutable=True,
                    eta=campaign.send_time + timedelta(days=3),
                )
                | ensure_stats.signature(
                    args=(self.pk,),
                    immutable=True,
                    eta=campaign.send_time + timedelta(days=6),
                )
            )

            if apply_tasks:
                self.log_event(
                    CAMPAIGN_SIGNATURES,
                    task=task_context,
                    data={"sigs": repr(publish_sigs)},
                )
                return publish_sigs.apply_async(), campaign
            else:
                return publish_sigs, campaign
        return None, None

    def pause(self):
        self.log_event(PAUSE_CAMPAIGN)
        assert (
            self.status == BaseCampaignRunner.STATUS.published
        ), "Campaign must be in PUBLISHED condition."
        self.status = BaseCampaignRunner.STATUS.paused
        self.run_id = PAUSE_HEX
        self.save()

    # TODO: lock
    def resume_drip_tasks(
        self, root_campaign: ColdCampaign, noop_after: timedelta = None
    ):
        # Detect where in drips we are, and start from there.
        drips = DripRecord.objects.filter(runner=self, root=root_campaign)
        if self.run_id == PAUSE_HEX:
            return
        if self.sending_rules().count() == 1:  # No drips required
            return
        if drips.count() == self.sending_rules().count() - 1:  # All drips done
            return
        if drips.count() == 0:  # Drips haven't started
            if noop_after is not None:
                if now() > root_campaign.send_time + noop_after:
                    return
            return self.drip_tasks(
                root_campaign=root_campaign,
                following=root_campaign,
                run_id=self.run_id,
            )
        # Looks like we're in the middle of drips.
        following = drips.last().drip
        if noop_after is not None:
            if now() > following.send_time + noop_after:
                return
        return self.drip_tasks(
            root_campaign=root_campaign, following=following, run_id=self.run_id,
        )

    def resume(self):
        assert (
            self.status == ColdCampaign.STATUS.paused
        ), "Campaign must be in PAUSED condition."
        self.log_event(RESUME_CAMPAIGN)
        self.status = ColdCampaign.STATUS.published
        self.run_id = uuid.uuid4()
        self.save()
        for campaign in self.campaigns.all():
            if drip_tasks := self.resume_drip_tasks(root_campaign=campaign):
                drip_tasks.apply_async()
        self.publish()

    def delete(self, *args, **kwargs):
        for campaign in self.campaigns.all():
            campaign.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)
