from unittest.mock import patch

import pytest

from whoweb.coldemail.tests.factories import CampaignListFactory
from .factories import CampaignRunnerWithMessagesFactory

pytestmark = pytest.mark.django_db


@patch("whoweb.campaigns.models.base.BaseCampaignRunner.set_reply_fields")
@patch("whoweb.campaigns.models.base.BaseCampaignRunner.create_campaign_list")
def test_create_campaign_from_runner(list_mock, reply_fields):
    campaign_list = CampaignListFactory()
    list_mock.return_value = campaign_list
    runner = CampaignRunnerWithMessagesFactory()
    campaign = runner.create_campaign()

    assert campaign.title == runner.title + " - m0"
    assert campaign.seat == runner.seat
    assert campaign.message, runner.messages.first()
    assert campaign.campaign_list, campaign_list
    assert campaign in runner.campaigns.all()
