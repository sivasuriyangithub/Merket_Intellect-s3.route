import json
from unittest.mock import patch

from django.test import SimpleTestCase

from whoweb.coldemail.api.resource import Message
from . import fixtures


def mock_return(data):
    return json.loads(data), None


@patch("whoweb.coldemail.api.requestor.ColdEmailApiRequestor.request")
class TestColdMessage(SimpleTestCase):
    def test_create(self, request_mock):
        request_mock.return_value = mock_return(fixtures.create_message)
        msg_record = Message.create(title="Test")
        self.assertEqual("182193", msg_record.id)
        self.assertIsInstance(msg_record, Message)

    def test_fetch(self, request_mock):
        request_mock.return_value = mock_return(fixtures.message_detail)
        msg_record = Message.retrieve("182193")
        request_mock.assert_called_once_with("email", "getmessagedetail", id="182193")
        self.assertIsInstance(msg_record, Message)
        self.assertEqual("182193", msg_record.id)
        self.assertEqual("test", msg_record.title)

    def test_list(self, request_mock):
        request_mock.return_value = mock_return(fixtures.messages)
        msg_records = Message.list()
        self.assertIsInstance(msg_records, list)
        self.assertIsInstance(msg_records[0], Message)
        self.assertEqual("182129", sorted(msg_records, key=lambda c: c.id)[0].id)
        self.assertEqual(
            "WK_VIP_CitizensCapital_20190717",
            sorted(msg_records, key=lambda c: c.id)[0].title,
        )
