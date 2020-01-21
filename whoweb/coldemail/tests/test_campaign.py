from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock

import pytest
from celery.exceptions import Retry
from celery.task import Task
from django.utils.timezone import now

from whoweb.coldemail.api.tests.fixtures import campaign_detail
from whoweb.coldemail.api.tests.test_campaign import mock_return
from whoweb.coldemail.models import ColdCampaign, CampaignList
from whoweb.coldemail.tasks import check_for_list_publication

pytestmark = pytest.mark.django_db


@patch("whoweb.coldemail.models.ColdCampaign.pause")
def test_archive(pause_mock, cold_campaign):
    cold_campaign.delete()
    assert pause_mock.call_count == 1


@patch("whoweb.coldemail.models.CampaignList.publish")
@patch("whoweb.coldemail.models.CampaignMessage.publish")
def test_publish(msg_mock, list_mock, cold_campaign):
    msg_mock.return_value = MagicMock(spec=Task).si()
    list_mock.return_value = MagicMock(spec=Task).si() | MagicMock(spec=Task).si()
    cold_campaign.send_time = now()
    cold_campaign.save()
    sigs = cold_campaign.publish()
    assert sigs
    msg_mock.assert_called_once_with(apply_tasks=False)
    list_mock.assert_called_once_with(apply_tasks=False, on_complete=None)
    assert cold_campaign.is_locked == True


@patch("whoweb.coldemail.models.ColdCampaign.api_create")
def test_api_upload(api_create_mock, cold_campaign):
    api_create_mock.return_value.id = "123ABC"
    cold_campaign.status = ColdCampaign.STATUS.pending
    cold_campaign.send_time = datetime.utcfromtimestamp(1547591866)
    cold_campaign.save()
    cold_campaign.api_upload()

    assert cold_campaign.status == ColdCampaign.STATUS.published

    assert cold_campaign.coldemail_id == "123ABC"
    api_create_mock.assert_called_with(
        title="",
        listid="",
        subject=b"",
        messageid="",
        date=1547591866,
        whoisid="123",
        profileid="456",
        fromaddress="",
        fromname="",
        suppressionid="1",
        dklim=1,
        viewaswebpage=0,
        debug=1,
    )


@patch("whoweb.coldemail.tasks.check_for_list_publication.retry")
@patch("whoweb.coldemail.models.ColdCampaign.api_upload")
@patch("whoweb.coldemail.models.CampaignList.api_retrieve")
def test_check_list_publication_failure(api_retrieve, api_upload, retry, cold_campaign):
    # Set a side effect on the patched methods
    # so that they raise the errors we want.

    api_retrieve.return_value = Mock(CampaignList.api_class, total=None)
    retry.side_effect = Retry()
    with pytest.raises(Retry):
        check_for_list_publication(cold_campaign.campaign_list.pk)
    assert api_upload.call_count == 0


@patch("whoweb.coldemail.models.ColdCampaign.api_upload")
@patch("whoweb.coldemail.models.CampaignList.api_retrieve")
def test_check_list_publication_success(api_retrieve, api_upload, cold_campaign):
    api_retrieve.return_value = Mock(CampaignList.api_class, total=1)
    cold_campaign.status = cold_campaign.STATUS.pending
    cold_campaign.save()
    check_for_list_publication(cold_campaign.campaign_list.pk)
    assert api_retrieve.call_count == 1
    assert api_upload.call_count == 1


@patch("whoweb.coldemail.models.CampaignList.api_retrieve")
@patch("whoweb.coldemail.models.ColdCampaign._annotate_web_ids")
@patch("whoweb.coldemail.api.resource.Campaign.open_log")
@patch("whoweb.coldemail.api.resource.Campaign.click_log")
@patch("whoweb.coldemail.models.ColdCampaign.populate_webprofile_id_lookup")
@patch("whoweb.coldemail.api.requestor.ColdEmailApiRequestor.request")
def test_fetch_stats(
    request_mock,
    web_id_mock,
    click_mock,
    open_mock,
    annotate_mock,
    list_mock,
    cold_campaign,
):
    request_mock.return_value = mock_return(campaign_detail)
    list_mock.side_effect = [False]

    class Log(dict):
        def __init__(self, records=1):
            self.uniquerecords = records
            super(Log, self).__init__()

    annotate_mock.side_effect = [Log(5), Log(50)]
    cold_campaign.coldemail_id = "2070703"
    cold_campaign.send_time = now() - timedelta(days=2)
    cold_campaign.save()

    cold_campaign.fetch_stats()
    web_id_mock.assert_called_once_with()
    click_mock.assert_called_once_with(is_sync=True)
    open_mock.assert_called_once_with(is_sync=True)
    cold_campaign.refresh_from_db()
    assert cold_campaign.unique_clicks == 5
    assert cold_campaign.unique_views == 50


@patch("whoweb.coldemail.api.requestor.ColdEmailApiRequestor.request")
def test_fetch_stats_error(request_mock, cold_campaign):
    request_mock.return_value = mock_return(
        '{"error":"You do not have permission to mock this value."}'
    )

    cold_campaign.coldemail_id = "2070703"
    cold_campaign.send_time = now() - timedelta(days=2)
    cold_campaign.save()

    assert cold_campaign.fetch_stats() is None
