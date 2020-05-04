from unittest.mock import patch, MagicMock, Mock
from uuid import uuid4

import pytest
from celery.task import Task

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.coldemail.models import CampaignList
from whoweb.coldemail.tasks import check_for_list_publication, upload_list
from whoweb.coldemail.tests.factories import CampaignListFactory
from whoweb.search.tests.factories import SearchExportFactory

pytestmark = pytest.mark.django_db


@patch("whoweb.search.models.SearchExport.processing_signatures")
def test_publish_with_export(sigs_mock, query_contact_invites):
    sigs_mock.return_value = MagicMock(spec=Task).si()

    campaign_list = CampaignListFactory(
        export=SearchExportFactory(query=query_contact_invites)
    )

    sigs = campaign_list.publish(apply_tasks=False)
    sigs_mock.return_value.__or__.assert_called_once_with(
        upload_list.si(campaign_list.pk)
        | check_for_list_publication.si(campaign_list.pk)
    )
    assert sigs is not None


@patch("whoweb.search.models.SearchExport.processing_signatures")
def test_publish_with_query(sigs_mock, query_contact_invites):
    sigs_mock.return_value = MagicMock(spec=Task).si()
    seat = BillingAccountMemberFactory(seat_credits=15000000)
    campaign_list = CampaignListFactory(
        query=query_contact_invites, export=None, billing_seat=seat
    )
    assert campaign_list.export is None
    campaign_list.publish(apply_tasks=False)
    assert campaign_list.export is not None


@patch("whoweb.coldemail.api.resource.CampaignList.create_by_url")
def test_api_upload(create_mock, query_contact_invites):
    create_mock.return_value = Mock(CampaignList.api_class, id="A", status="Processing")

    uuid = uuid4()
    campaign_list = CampaignListFactory(
        export=SearchExportFactory(
            query=query_contact_invites,
            uploadable=True,
            csv__filename=f"{uuid.hex}__fetch.csv",
            uuid=uuid,
        )
    )

    campaign_list.api_upload()
    export = campaign_list.export.uuid.hex
    create_mock.assert_called_with(
        url=f"https://storage.googleapis.com/test/media/exports/{export}/download/{export}__fetch.csv"
    )
    assert campaign_list.status == CampaignList.STATUS.published
    assert campaign_list.coldemail_id == "A"
