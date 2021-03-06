from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils.timezone import utc

from whoweb.search.tests.factories import SearchExportFactory, SearchExportPageFactory
from whoweb.search.models import SearchExport
from whoweb.coldemail.models import CampaignList
from whoweb.coldemail.tests.factories import CampaignListFactory, ColdCampaignFactory
from .factories import (
    CampaignRunnerWithMessagesFactory,
    CampaignRunnerWithDripsFactory,
    SendingRuleFactory,
    DripRecordFactory,
)
from ..models.base import BaseCampaignRunner, SendingRule

pytestmark = pytest.mark.django_db


def test_task_timing_args():
    send = datetime(2020, 3, 1, hour=9, minute=15, second=0, tzinfo=utc)
    rule: SendingRule = SendingRuleFactory(
        trigger=SendingRule.SendingRuleTriggerOptions.DATETIME, send_datetime=send
    )
    assert rule.task_timing_args() == {"eta": send - timedelta(seconds=600)}

    rule: SendingRule = SendingRuleFactory(
        trigger=SendingRule.SendingRuleTriggerOptions.TIMEDELTA, send_delta=180000
    )
    assert rule.task_timing_args() == {"countdown": 180000 - 600}

    assert rule.task_timing_args(timedelta_from=send) == {
        "eta": send + timedelta(seconds=180000)
    }

    rule: SendingRule = SendingRuleFactory(
        trigger=SendingRule.SendingRuleTriggerOptions.DELAY
    )
    assert rule.task_timing_args() == {"countdown": 300}


def test_create_campaignlist_from_runner(query_contact_invites_defer_validation):
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory(
        query=query_contact_invites_defer_validation
    )
    campaign_list = runner.create_campaign_list()
    assert campaign_list.query == runner.query
    assert campaign_list.billing_seat == runner.billing_seat
    assert campaign_list.origin == campaign_list.OriginOptions.SYSTEM


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.set_reply_fields")
@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_campaign_list")
def test_create_campaign_from_runner(list_mock, reply_fields):
    campaign_list = CampaignListFactory()
    list_mock.return_value = campaign_list
    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory()
    campaign = runner.create_campaign()

    assert campaign.title == runner.title + " - m0"
    assert campaign.billing_seat == runner.billing_seat
    assert campaign.message, runner.messages.first()
    assert campaign.campaign_list, campaign_list
    assert campaign in runner.campaigns.all()


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.remove_reply_rows")
def test_create_next_drip_list(remove_reply_mock):
    SendingRuleFactory.reset_sequence()
    DripRecordFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithDripsFactory()
    assert (
        CampaignList.objects.count() == 5
    )  # should be 3, but post_gen replaces root twice.
    assert SearchExport.available_objects.count() == 5
    runner.create_next_drip_list(runner.drips.first(), runner.drips.first())
    assert CampaignList.available_objects.count() == 6
    assert SearchExport.available_objects.count() == 6


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.set_reply_fields")
@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_next_drip_list")
def test_create_next_drip_campaign(list_mock, reply_fields_mock):
    list_mock.side_effect = lambda **x: CampaignListFactory(__sequence=0)
    reply_fields_mock.side_effect = lambda x: x

    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory(__sequence=0)
    # first drip
    root = ColdCampaignFactory(message=runner.messages.first())
    runner.campaigns.add(root)
    drip = runner.create_next_drip_campaign(root_campaign=root, following=root)
    assert runner.drips.count() == 1
    assert runner.drips.first() == drip
    record = runner.drip_records.first()
    assert record.drip == drip
    assert record.root == root
    assert record.order == 1

    # second drip
    drip_two = runner.create_next_drip_campaign(root_campaign=root, following=drip)
    assert runner.drips.count() == 2
    assert runner.drips.all()[1] == drip_two
    record = runner.drip_records[1]
    assert record.drip == drip_two
    assert record.root == root
    assert record.order == 2


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_campaign")
def test_get_next_sending_rule(create_campaign_mock):
    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory()
    rules = runner.sending_rules

    ct = 0

    def create_campaign():
        nonlocal ct
        campaign = ColdCampaignFactory(message=runner.messages.all()[ct])
        runner.campaigns.add(campaign)
        ct += 1
        return campaign

    create_campaign_mock.side_effect = create_campaign

    campaign0 = runner.create_campaign()
    assert campaign0.message == rules[0].message
    assert runner.get_next_rule(following=campaign0) == rules[1]

    campaign1 = runner.create_campaign()
    assert campaign1.message == rules[1].message
    assert runner.get_next_rule(following=campaign1) == rules[2]


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.set_reply_fields")
@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_campaign_list")
def test_publish(list_mock, reply_fields):
    campaign_list = CampaignListFactory()
    list_mock.return_value = campaign_list
    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory()
    sigs, campaign = runner.publish(apply_tasks=False)
    assert sigs
    assert campaign
    assert runner.status == runner.CampaignRunnerStatusOptions.PENDING


def test_generate_icebreakers(raw_derived):
    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory()
    export: SearchExport = SearchExportFactory()
    SearchExportPageFactory.create_batch(
        1, export=export, count=50, data=raw_derived[:50]
    )
    runner.generate_icebreakers(0, export.pk)
    profiles = list(export.get_profiles())
    assert (
        profiles[0].icebreaker == "ID: wp:4XJFtuYgV6ZU756WQH9n96K75EUZdZhbQ3Z5iDK7Wz97"
    )
    assert (
        profiles[1].icebreaker == "ID: wp:J8ccNBtnoJx35dznq6VunSi1zKiHX9xB2chdQ1tHuSa7"
    )
