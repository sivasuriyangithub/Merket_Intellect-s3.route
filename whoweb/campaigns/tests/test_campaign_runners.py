from unittest.mock import patch

import pytest

from whoweb.search.models import SearchExport
from whoweb.coldemail.models import CampaignList
from whoweb.coldemail.tests.factories import CampaignListFactory, ColdCampaignFactory
from .factories import (
    CampaignRunnerWithMessagesFactory,
    CampaignRunnerWithDripsFactory,
    SendingRuleFactory,
    DripRecordFactory,
)
from ..models.base import BaseCampaignRunner

pytestmark = pytest.mark.django_db


def test_create_campaignlist_from_runner(query_contact_invites_defer_validation):
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory(
        query=query_contact_invites_defer_validation
    )
    campaign_list = runner.create_campaign_list()
    assert campaign_list.query == runner.query
    assert campaign_list.seat == runner.seat
    assert campaign_list.origin == campaign_list.ORIGIN.system


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.set_reply_fields")
@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_campaign_list")
def test_create_campaign_from_runner(list_mock, reply_fields):
    campaign_list = CampaignListFactory()
    list_mock.return_value = campaign_list
    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory()
    campaign = runner.create_campaign()

    assert campaign.title == runner.title + " - m0"
    assert campaign.seat == runner.seat
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
    assert SearchExport.objects.count() == 5
    runner.create_next_drip_list(runner.drips.first(), runner.drips.first())
    assert CampaignList.objects.count() == 6
    assert SearchExport.objects.count() == 6


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
    record = runner.drip_records().first()
    assert record.drip == drip
    assert record.root == root
    assert record.order == 1

    # second drip
    drip_two = runner.create_next_drip_campaign(root_campaign=root, following=drip)
    assert runner.drips.count() == 2
    assert runner.drips.all()[1] == drip_two
    record = runner.drip_records()[1]
    assert record.drip == drip_two
    assert record.root == root
    assert record.order == 2


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_campaign")
def test_get_next_sending_rule(create_campaign_mock):
    SendingRuleFactory.reset_sequence()
    runner: "BaseCampaignRunner" = CampaignRunnerWithMessagesFactory()
    rules = runner.sending_rules()

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
