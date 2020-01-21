# from uuid import uuid4
#
# import pytest
# from celery import Task
# from unittest.mock import patch, MagicMock, Mock
#
# from tests.cases import MongoEnabledAsyncTestCase
# from xperweb.cold_email.models import CampaignList, ProfileDataSource
# from xperweb.cold_email.tasks import upload_list, check_for_list_publication
# from xperweb.exports.models import ListUploadableSearchExport
# from xperweb.search.models import FilteredSearchQuery
#
# pytestmark = pytest.mark.django_db
#
#
# class TestCampaignList(MongoEnabledAsyncTestCase):
#     def setUp(self):
#         super(TestCampaignList, self).setUp()
#         self.export = ListUploadableSearchExport.objects.create(user_id="1")
#         self.query = FilteredSearchQuery(
#             **{
#                 "filters": {
#                     "required": [
#                         {"field": "first_name", "value": "Zaphod", "truth": True}
#                     ],
#                     "desired": [],
#                     "profiles": [],
#                 },
#                 "defer": [u"company_counts", u"degree_levels"],
#                 "with_invites": True,
#                 "source": None,
#                 "user_id": None,
#             }
#         )
#         self.campaign_list = CampaignList.objects.create(
#             data_source=ProfileDataSource(query=self.query)
#         )
#
#     @patch("xperweb.exports.models.ListUploadableSearchExport.processing_signatures")
#     def test_publish_with_export(self, sigs_mock):
#         sigs_mock.return_value = MagicMock(spec=Task).si()
#
#         self.campaign_list.data_source.export = self.export
#         self.campaign_list.save()
#
#         sigs = self.campaign_list.publish(apply_tasks=False)
#         sigs_mock.return_value.__or__.assert_called_once_with(
#             upload_list.si(self.campaign_list.pk)
#             | check_for_list_publication.si(self.campaign_list.pk)
#         )
#         self.assertIsNotNone(sigs)
#
#     @patch("xperweb.data_access.router.Router.create_export")
#     @patch("xperweb.exports.models.ListUploadableSearchExport.processing_signatures")
#     def test_publish_with_query(self, sigs_mock, create_mock):
#         create_mock.return_value = {"uuid": uuid4()}
#         sigs_mock.return_value = MagicMock(spec=Task).si()
#
#         self.campaign_list.data_source.query = self.query
#         self.campaign_list.save()
#
#         self.assertIsNone(self.campaign_list.data_source.export)
#         self.campaign_list.publish(apply_tasks=False)
#         self.assertIsNotNone(self.campaign_list.data_source.export)
#
#     @patch("xperweb.exports.models.ListUploadableSearchExport.generate_upload_url")
#     @patch("xperweb.cold_email.api.resource.List.create_by_url")
#     def test_api_upload(self, create_mock, url_mock):
#         url_mock.return_value = "http://url"
#         create_mock.return_value = Mock(
#             CampaignList.api_class, id="A", status="Processing"
#         )
#
#         self.campaign_list.data_source.export = self.export
#         self.campaign_list.save()
#
#         self.campaign_list.api_upload(is_sync=True)
#         create_mock.assert_called_with(url="http://url", is_sync=True)
#         self.assertEqual(CampaignList.PUBLISHED, self.campaign_list.status)
#         self.assertEqual("A", self.campaign_list.coldemail_id)
