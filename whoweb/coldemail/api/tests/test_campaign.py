import json
from unittest.mock import patch

from django.test import SimpleTestCase

from whoweb.coldemail.api.resource import Campaign
from . import fixtures


def mock_return(data):
    return json.loads(data), None


@patch("whoweb.coldemail.api.requestor.ColdEmailApiRequestor.request")
class TestCampaign(SimpleTestCase):
    def test_create(self, request_mock):
        request_mock.return_value = mock_return(fixtures.create_campaign)
        campaign_record = Campaign.create(title="Test")
        self.assertEqual(campaign_record.id, "2070703")
        self.assertIsInstance(campaign_record, Campaign)

    def test_fetch(self, request_mock):
        request_mock.return_value = mock_return(fixtures.campaign_detail)
        campaign_record = Campaign.retrieve("2070703")
        request_mock.assert_called_once_with("email", "getcampaigndetail", id="2070703")
        self.assertIsInstance(campaign_record, Campaign)
        self.assertEqual(campaign_record.id, "2070703")
        self.assertEqual(
            campaign_record.title, "WKVIP_Chairman Mom - Employees6 Letter 2"
        )
        self.assertEqual(campaign_record.starttime, "July 23, 2019, 03:06:49 pm")
        self.assertEqual(campaign_record.messageid, "181798")

    def test_list(self, request_mock):
        request_mock.return_value = mock_return(fixtures.campaigns)
        campaign_records = Campaign.list()
        self.assertIsInstance(campaign_records, list)
        self.assertIsInstance(campaign_records[0], Campaign)
        self.assertEqual(sorted(campaign_records, key=lambda c: c.id)[0].id, "2070437")

    def test_click_log(self, request_mock):
        request_mock.return_value = mock_return(fixtures.campaign_clicklog)
        campaign = Campaign("0")
        log = campaign.click_log()
        request_mock.assert_called_once_with("email", "getclicklog", id="0", limit=1000)
        self.assertEqual(log.uniquerecords, "4")
        self.assertEqual(len(log.log), 10)

    def test_empty_click_log(self, request_mock):
        request_mock.return_value = mock_return(fixtures.campaign_clicklog_empty)
        campaign = Campaign("0")
        log = campaign.click_log()
        request_mock.assert_called_once_with("email", "getclicklog", id="0", limit=1000)
        self.assertEqual(log.uniquerecords, "0")
        self.assertEqual(len(log.log), 0)

    def test_open_log(self, request_mock):
        request_mock.return_value = mock_return(fixtures.campaign_openlog)
        campaign = Campaign("0")
        log = campaign.open_log()
        request_mock.assert_called_once_with("email", "getopenlog", id="0", limit=1000)
        self.assertEqual(log.uniquerecords, "4")
        self.assertEqual(len(log.log), 10)

    def test_empty_open_log(self, request_mock):
        request_mock.return_value = mock_return(fixtures.campaign_openlog_empty)
        campaign = Campaign("0")
        log = campaign.open_log()
        request_mock.assert_called_once_with("email", "getopenlog", id="0", limit=1000)
        self.assertEqual(log.uniquerecords, "0")
        self.assertEqual(len(log.log), 0)
