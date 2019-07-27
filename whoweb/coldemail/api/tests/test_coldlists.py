import json
from unittest.mock import patch

from django.test import SimpleTestCase

from whoweb.coldemail.api.resource import CampaignList, ColdEmailObject
from . import fixtures


def mock_return(data):
    return json.loads(data), None


@patch("whoweb.coldemail.api.requestor.ColdEmailApiRequestor.request")
class TestColdlist(SimpleTestCase):
    def test_create(self, request_mock):
        request_mock.return_value = mock_return(fixtures.create_coldlist)
        list_record = CampaignList.create(title="Test")
        self.assertEqual("431142", list_record.id)
        self.assertIsInstance(list_record, CampaignList)

    def test_create_by_url(self, request_mock):
        request_mock.return_value = mock_return(fixtures.create_coldlist_by_url)
        list_record = CampaignList.create_by_url(url="internet.com/list.csv")
        request_mock.assert_called_once_with(
            "email", "uploadlistbyurl", url="internet.com/list.csv"
        )
        self.assertEqual("431168", list_record.id)
        self.assertIsInstance(list_record, CampaignList)

    def test_fetch(self, request_mock):
        request_mock.return_value = mock_return(fixtures.coldlist)
        list_record = CampaignList.retrieve("431142")
        request_mock.assert_called_once_with(
            "email", "getlists", id="431142"
        )  # not getdetails
        self.assertIsInstance(list_record, CampaignList)
        self.assertEqual("431142", list_record.id)
        self.assertEqual("Chairman Mom Employees 20190723", list_record.title)

    def test_list(self, request_mock):
        request_mock.return_value = mock_return(fixtures.coldlists)
        list_records = CampaignList.list()
        self.assertIsInstance(list_records, list)
        self.assertIsInstance(list_records[0], CampaignList)
        self.assertEqual("406876", sorted(list_records, key=lambda c: c.id)[0].id)
        self.assertEqual("OMFM", sorted(list_records, key=lambda c: c.id)[0].title)

    def test_good_log(self, request_mock):
        request_mock.return_value = mock_return(fixtures.coldlist_records)
        list_record = CampaignList("0")
        good_log = list_record.good_log()
        request_mock.assert_called_once_with(
            "email", "getlistdetail", filter="active", limit=100000, id="0"
        )

        self.assertIsInstance(good_log.log[0], ColdEmailObject)
        self.assertEqual(3, len(good_log.log))

        # Assert cached
        self.assertEqual(1, request_mock.call_count)
        list_record.good_log()
        self.assertEqual(1, request_mock.call_count)
