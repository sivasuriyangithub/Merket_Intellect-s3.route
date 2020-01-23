from datetime import timedelta

from django.contrib.postgres.fields import JSONField
from django.db import models
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import SoftDeletableModel, TimeStampedModel

from whoweb.coldemail.models import (
    ColdCampaign,
    CampaignMessage,
    CampaignMessageTemplate,
)
from whoweb.contrib.postgres.fields import EmbeddedModelField
from whoweb.core.models import EventLoggingModel
from whoweb.search.models import FilteredSearchQuery, ScrollSearch


class AbstractBaseSendingRule(models.Model):
    class Meta:
        unique_together = ("index", "manager")
        abstract = True

    TRIGGER = Choices(
        (0, "datetime", "At a specified time"),
        (1, "timedelta", "Seconds after previous"),
        (2, "delay", "A short delay after creation"),
    )

    message_template = models.ForeignKey(
        CampaignMessageTemplate, null=True, on_delete=models.SET_NULL, related_name="+",
    )
    message = models.ForeignKey(CampaignMessage, on_delete=models.CASCADE)
    index = (
        models.PositiveIntegerField()
    )  # index 0 must be DELAY or DATETIME, see method `send_time_for_rule`
    trigger = models.PositiveSmallIntegerField(choices=TRIGGER, default=TRIGGER.delay)

    send_datetime = models.DateTimeField(null=True)
    send_delta = models.PositiveIntegerField(null=True)
    include_previous = models.BooleanField(default=False)


class AbstractBaseDripRecord(models.Model):
    root = models.ForeignKey(
        ColdCampaign, on_delete=models.CASCADE, related_name="in_drip_roots"
    )
    drip = models.ForeignKey(
        ColdCampaign, on_delete=models.CASCADE, related_name="in_drip_drips"
    )
    order = models.PositiveSmallIntegerField(default=0)


class AbstractBaseCampaignRunner(
    EventLoggingModel, TimeStampedModel, SoftDeletableModel
):
    class Meta:
        abstract = True

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

    campaigns = models.ManyToManyField(ColdCampaign, related_name="+")
    title = models.CharField(max_length=255)
    query = EmbeddedModelField(
        FilteredSearchQuery, blank=False, default=FilteredSearchQuery
    )
    scroll = models.ForeignKey(ScrollSearch, on_delete=models.SET_NULL, null=True)

    budget = models.PositiveIntegerField()

    published = models.DateTimeField(null=True)
    status = models.IntegerField(
        "status", db_index=True, choices=STATUS, blank=True, default=STATUS.draft
    )
    status_changed = MonitorField("status changed", monitor="status")

    tracking_params = JSONField(null=True)

    # Enforce only 1 active signature chain in celery,
    # enabling republishing via .resume(), even with a pending canvas.
    # run_id = mongoengine.ObjectIdField(null=True)

    @property
    def sorted_sending_rules(self):
        return sorted(
            self.sending_rules,
            key=lambda ms: ms.index if ms.index is not None else ms.send_datetime,
        )

    @property
    def flattened_drips(self):
        drips = [
            str(getattr(drip, "pk", drip))
            for drip_map in self.drips.values()
            for drip in (drip_map.values() if hasattr(drip_map, "values") else drip_map)
        ]
        return Campaign.objects(pk__in=drips)

    @property
    def stats(self):
        return [
            campaign.stats
            for campaign in Campaign.objects(pk__in=[c.id for c in self.campaigns])
        ]

    def annotate_drips_with_sending_rules(self):
        sorted_rules = self.sorted_sending_rules
        rule_lookup = {str(rule.index): rule for rule in sorted_rules}

        fetched_drips = list(self.flattened_drips())  # avoid the internal n + 1 problem
        lookup = {}
        for root_pk, dripmap in self.drips.items():
            for rule_index, drip_ref in dripmap.items():
                lookup[str(drip_ref.pk)] = (rule_lookup[str(rule_index)], root_pk)
        for drip in fetched_drips:
            rule_used, root_campaign_pk = lookup.get(str(drip.pk), (None, None))
            drip.sending_rule_used = rule_used
            drip.root_campaign = root_campaign_pk
        return fetched_drips

    @staticmethod
    def export_from_campaign(campaign):
        return campaign.campaign_list.fetch().data_source.export

    def get_next_rule(self, last_campaign=None):
        latest_message = last_campaign.message
        found = False
        for rule in self.sorted_sending_rules:
            if found:
                return rule
            if rule.message.pk == latest_message.pk:
                found = True
        return None

    def create_next_drip_list(self, root_campaign, last_campaign):
        last_export = self.export_from_campaign(last_campaign)

        export = last_export.fetch()
        export.id = None
        export = export.save(force_insert=True)
        export = self.remove_reply_rows(export=export, root_campaign=root_campaign)

        return CampaignList.objects.create(
            data_source=ProfileDataSource(export=export),
            origin=2,
            user=self.user.pk if self.user else None,
        )

    def create_next_drip_cold_campaign(
        self, root_campaign, last_campaign, campaign_kwargs=None, *args, **kwargs
    ):

        rule = self.get_next_rule(last_campaign=last_campaign)
        if not rule:
            return
        if len(self.drips.get(str(root_campaign.pk), [])) >= rule.index:
            return

        # If intended send time is absolute,
        # and the CURRENT time is not after the last campaign send time plus a minimum buffer,
        # fail the list/export creation
        if rule.trigger == SendingRule.DATETIME:
            delta = datetime.utcnow() - max(
                last_campaign.send_time or last_campaign.published,
                last_campaign.published,
            )
            if delta < self.MIN_DRIP_DELAY:
                remaining = self.MIN_DRIP_DELAY - max(timedelta(0), delta)
                raise DripTooSoonError(countdown=int(remaining.total_seconds()))

        campaign_list = self.create_next_drip_list(
            root_campaign=root_campaign, last_campaign=last_campaign
        )
        if not campaign_list:
            return

        if campaign_kwargs is None:
            campaign_kwargs = {}

        if self.user:
            campaign_kwargs.setdefault("user", self.user.pk)
        title = campaign_kwargs.setdefault("title", self.title)
        campaign_kwargs.update(
            message=rule.message,
            send_time=datetime.utcnow() + timedelta(seconds=300),
            campaign_list=campaign_list,
            title="{} - m{}".format(title, rule.index),
        )
        cold_campaign = Campaign.objects.create(**campaign_kwargs)
        cold_campaign = self.set_reply_fields(cold_campaign)
        self.modify(
            **{
                "set__drips__"
                + str(root_campaign.pk)
                + "__"
                + str(rule.index): cold_campaign
            }
        )
        return cold_campaign

    def create_next_drip_campaign(
        self, root_campaign, last_campaign, campaign_kwargs=None, *args, **kwargs
    ):
        """
        :param root_campaign: Initial campaign for which we have follow-up drips.
        :type root_campaign: Campaign | str
        :param last_campaign: Last sent campaign in the drip branch.
        :type last_campaign: Campaign | str
        :param campaign_kwargs: Arguments used to create the campaign.
        :type campaign_kwargs: Dict
        :return:
        """
        lock = MongoLock()
        lock_key = str(root_campaign.pk) + "__subcampaign"
        with lock(lock_key, owner=self.pk, timeout=20, expire=60 * 60 * 6):
            return self.create_next_drip_cold_campaign(
                root_campaign=root_campaign,
                last_campaign=last_campaign,
                campaign_kwargs=campaign_kwargs,
                *args,
                **kwargs,
            )

    def publish_drip(
        self, root_campaign, last_campaign, task_context=None, *args, **kwargs
    ):
        if not isinstance(root_campaign, Campaign):
            root_campaign = Campaign.objects.with_id(root_campaign)
        if not isinstance(last_campaign, Campaign):
            last_campaign = Campaign.objects.with_id(last_campaign)

        campaign = self.create_next_drip_campaign(
            root_campaign=root_campaign, last_campaign=last_campaign, *args, **kwargs
        )
        if campaign:
            publish_sigs = campaign.publish(apply_tasks=False)
        else:
            publish_sigs = None
        if publish_sigs:
            drip_sigs = self.drip_tasks(
                root_campaign=root_campaign, last_campaign=campaign
            )
            if drip_sigs:
                publish_sigs |= drip_sigs
        if publish_sigs:
            publish_sigs.apply_async()
        self.log_event(
            PUBLISH_DRIP_CAMPAIGN, task=task_context, data={"sigs": repr(publish_sigs)}
        )

    @staticmethod
    def task_timing_args_for_rule(rule):
        if rule.trigger == SendingRule.DATETIME:
            return {"eta": rule.send_datetime - timedelta(seconds=600)}
        elif rule.trigger == SendingRule.TIMEDELTA:
            return {"countdown": rule.send_delta - 600}
        elif rule.trigger == SendingRule.DELAY:
            return {"countdown": 300}
        return {}

    def drip_tasks(
        self,
        root_campaign,
        last_campaign,
        campaign_kwargs=None,
        run_id=None,
        *args,
        **kwargs,
    ):
        """
        :rtype: celery.canvas.Signature
        """
        from xperweb.campaign.tasks import publish_drip, ensure_stats

        rule = self.get_next_rule(last_campaign=last_campaign)
        if not rule:
            return

        sigs = ensure_stats.signature(
            args=(self.__class__.__name__, str(self.pk)),
            immutable=True,
            **self.task_timing_args_for_rule(rule),
        ) | publish_drip.si(
            self.__class__.__name__,
            str(self.pk),
            *args,
            root_campaign=str(root_campaign.pk),
            last_campaign=str(last_campaign.pk),
            campaign_kwargs=campaign_kwargs,
            run_id=run_id,
            **kwargs,
        )
        return sigs

    def remove_reply_rows(self, export, root_campaign):
        responders = self.get_responders(root_campaign=root_campaign)
        pages = []
        for page in export.pages:
            page = page.fetch()
            page.set_data(
                [
                    row
                    for row in page.get_data()
                    if ResultProfile.from_mongo(row).id not in responders
                ]
            )
            page.id = None
            page.export = export
            page.save()
            pages.append(page)
        export.modify(pages=pages)
        return export

    def get_responders(self, root_campaign):
        responders = set()
        for campaign in set([root_campaign] + self.drips.get(root_campaign.pk, [])):
            if not campaign or not campaign.published or not campaign.stats:
                continue
            for log_entry in campaign.stats.click_log.get("log", []):
                if "web_id" in log_entry:
                    responders.add(log_entry["web_id"])
            for log_entry in campaign.stats.reply_log:
                if "web_id" in log_entry:
                    responders.add(log_entry["web_id"])
        return responders

    @property
    def created(self):
        return self.pk.generation_time

    def query_to_dict(self):
        return self.query.to_mongo().to_dict()

    def scroll_interface(self, force=False):
        if self.scroll:
            search = self.scroll.fetch()
            search.ensure_live_scroll_id(force=force)
        else:
            search = ScrollSearch.create(
                user_id=str(self.user.pk) if self.user else "",
                query=self.query.to_mongo().to_dict(),
            )
            self.modify(scroll=search)
        return self.scroll.fetch()

    def set_reply_fields(self, campaign):
        from_address, from_name = ReplyTo.get_or_create(campaign)
        campaign.modify(from_address=from_address, from_name=from_name)
        return campaign

    def send_times(self):
        for campaign in Campaign.objects(pk__in=[c.id for c in self.campaigns]):
            if campaign.status == Campaign.PENDING:
                yield campaign.modified
            elif campaign.status == Campaign.PUBLISHED:
                yield campaign.published
            continue

    @property
    def last_sent_campaign(self):
        return (
            Campaign.objects(pk__in=self.campaigns, status=Campaign.PUBLISHED)
            .order_by("-published")
            .first()
        )

    @property
    def last_sent_export(self):
        if self.last_sent_campaign:
            return self.last_sent_campaign.campaign_list.data_source.export

    def create_campaign_list(self, *args, **kwargs):
        if self.user:
            customer = Customer.get_or_create(subscriber=self.user)[0]
        else:
            customer = None
        export = ListUploadableSearchExport.passthrough(
            query=self.query_to_dict(), customer=customer
        )
        return CampaignList.objects.create(
            data_source=ProfileDataSource(export=export), origin=2, user=self.user
        )

    def create_cold_campaign(self, campaign_kwargs=None, *args, **kwargs):
        """
        :rtype: Campaign
        """
        first_message_rule = self.sorted_sending_rules[0]

        if campaign_kwargs is None:
            campaign_kwargs = {}

        if self.user:
            campaign_kwargs.setdefault("user", self.user.pk)
        title = campaign_kwargs.setdefault("title", self.title)
        campaign_kwargs.update(
            message=first_message_rule.message,
            send_time=first_message_rule.send_datetime,
            campaign_list=self.create_campaign_list(),
            title="{} - m{}".format(title, first_message_rule.index),
        )
        cold_campaign = Campaign.objects.create(**campaign_kwargs)
        cold_campaign = self.set_reply_fields(cold_campaign)
        self.modify(add_to_set__campaigns=cold_campaign)
        return cold_campaign

    def create_campaign(self, *args, **kwargs):
        lock = MongoLock()
        lock_key = str(self.pk) + "__subcampaign"
        with lock(lock_key, owner=self.pk, timeout=20, expire=60 * 60 * 6):
            campaign = self.create_cold_campaign(*args, **kwargs)
        return campaign

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
        self, apply_tasks=True, on_complete=None, task_context=None, *args, **kwargs
    ):
        """
        :rtype: (celery.canvas.Signature | celery.result.AsyncResult | None,  Campaign | None)
        """
        from xperweb.campaign.tasks import set_published

        self.log_event(PUBLISH_CAMPAIGN, task=task_context)
        hold = None
        if self.user and self.should_charge:
            hold, target = self.user.fetch().credit_hold(self.budget)
            assert target > 0, "Not enough credits to complete this export."

        initial_status = str(self.status)
        initial_run_id = ObjectId(
            self.run_id
        )  # drips may be running on this ID, even if no more campaigns should run.
        self.modify(
            query={"run_id__exists": False},
            run_id=ObjectId(),
            status=CampaignStatus.PENDING,
            modified=datetime.utcnow(),
        )
        self.reload()
        try:
            campaign = self.create_campaign()
            if not campaign:
                self.modify(
                    status=initial_status,
                    run_id=initial_run_id,
                    modified=datetime.utcnow(),
                )
                return None, None
            publish_sigs = campaign.publish(apply_tasks=False, on_complete=on_complete)
            if publish_sigs:
                publish_sigs |= set_published.si(
                    module=self.__class__.__module__,
                    clsname=self.__class__.__name__,
                    pk=self.pk,
                    run_id=self.run_id,
                )
                drip_sigs = self.drip_tasks(
                    root_campaign=campaign, last_campaign=campaign, run_id=self.run_id
                )
                if drip_sigs:
                    publish_sigs |= drip_sigs

                self.log_event(
                    CAMPAIGN_SIGNATURES,
                    task=task_context,
                    data={"sigs": repr(publish_sigs)},
                )

                if apply_tasks:
                    return publish_sigs.apply_async(), campaign
                else:
                    return publish_sigs, campaign
            self.modify(
                status=initial_status, run_id=initial_run_id, modified=datetime.utcnow()
            )
            return None, None
        except:
            if self.user and hold:
                self.user.fetch().reverse_hold(hold)
            self.modify(
                status=initial_status, run_id=initial_run_id, modified=datetime.utcnow()
            )
            raise

    def pause(self):
        self.log_event(PAUSE_CAMPAIGN)
        assert self.modify(
            query={"status": CampaignStatus.PUBLISHED},
            status=CampaignStatus.PAUSED,
            run_id=ObjectId("0" * 24),
        ), "Campaign must be in PUBLISHED condition."

    def resume_drip_tasks(self, root_campaign):
        lock = MongoLock()
        lock_key = str(root_campaign.pk) + "__subcampaign"  # drip lock
        with lock(lock_key, owner=self.pk, timeout=60, expire=60 * 60):
            # Detect where in drips we are, and start from there.
            drips = self.drips.get(str(root_campaign.pk), {}).values()
            if self.run_id == ObjectId("0" * 24):
                return
            if len(self.sending_rules) == 1:  # No drips required
                return
            if len(drips) == len(self.sending_rules) - 1:  # All drips done
                return
            if not drips:  # Drips haven't started
                return self.drip_tasks(
                    root_campaign=root_campaign,
                    last_campaign=root_campaign,
                    run_id=self.run_id,
                )
            # Looks like we're in the middle of drips.
            if len(drips) == 1:  # No sorting needed
                return self.drip_tasks(
                    root_campaign=root_campaign,
                    last_campaign=drips[0],
                    run_id=self.run_id,
                )
            last_drip = Campaign.objects(pk__in=drips).order_by("-send_time").first()
            return self.drip_tasks(
                root_campaign=root_campaign, last_campaign=last_drip, run_id=self.run_id
            )

    def resume(self):
        self.log_event(RESUME_CAMPAIGN)
        assert self.modify(
            query={"status": CampaignStatus.PAUSED},
            status=CampaignStatus.PUBLISHED,
            run_id=ObjectId(),
        ), "Campaign must be in PAUSED condition."
        self.reload()
        for campaign in self.campaigns:
            drip_tasks = self.resume_drip_tasks(root_campaign=campaign)
            if drip_tasks:
                drip_tasks.apply_async()
        self.publish()

    def archive(self):
        self.modify(archived=True, archived_at=datetime.utcnow())
        for campaign in self.campaigns:
            yield campaign.archive()

    def log_event(self, message, timestamp=None, task=None, **kwargs):
        if isinstance(message, six.string_types):
            message = (0, message)
        if timestamp is None:
            timestamp = datetime.utcnow()
        if task is not None:
            kwargs["task_id"] = task.id
        kwargs.setdefault("data", {}).update(
            ref={"_cls": self._get_collection_name(), "_id": self.pk}
        )
        entry = CampaignProcessingEvent(
            code=message[0],
            message=message[1],
            created=datetime.utcnow(),
            timestamp=timestamp,
            **kwargs,
        )
        self.modify(push__events=entry)
        return entry
