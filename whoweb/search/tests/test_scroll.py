import uuid
from unittest.mock import patch

from django.test import TestCase

from whoweb.search.models import ScrollSearch

scroll_effect = [
    ["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"],
    ["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"],
    ["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"],
    ["wp:16", "wp:17", "wp:18", "wp:19"],
    [],
]


class TestScrollSearch(TestCase):
    def setUp(self):
        super(TestScrollSearch, self).setUp()
        self.search = ScrollSearch.objects.create(page_size=5)

    def test_cache(self):
        self.assertEqual(None, self.search.page_from_cache(0))
        self.search.set_web_ids(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], page=0)
        self.assertListEqual(
            ["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], self.search.page_from_cache(0)
        )

    def test_active(self):
        self.assertEqual(False, self.search.page_active(0))
        self.search.set_web_ids(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], page=0)
        self.assertEqual(True, self.search.page_active(0))

    def test_active_after_key_change(self):
        self.assertEqual(False, self.search.page_active(0))
        self.search.set_web_ids(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], page=0)
        self.assertEqual(True, self.search.page_active(0))

        self.search.scroll_key = uuid.uuid4()  # New key.
        self.search.save()
        self.assertEqual(False, self.search.page_active(0))

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_sequential_page_requests(self, send_mock):
        # First page, 0.
        ids = self.search.get_ids_for_page(0)
        send_mock.assert_called_once_with()
        self.assertListEqual(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], ids)
        self.assertListEqual(
            ["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], self.search.page_from_cache(0)
        )

        # Next page.
        ids = self.search.get_ids_for_page(1)
        self.assertEqual(2, send_mock.call_count)
        self.assertListEqual(["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"], ids)

        # Next page.
        ids = self.search.get_ids_for_page(2)
        self.assertEqual(3, send_mock.call_count)
        self.assertListEqual(["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"], ids)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_duplicate_page_requests_use_cache(self, send_mock):
        # First page, 0.
        ids = self.search.get_ids_for_page(0)
        send_mock.assert_called_once_with()
        self.assertListEqual(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], ids)
        self.assertListEqual(
            ["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], self.search.page_from_cache(0)
        )

        # Next page.
        ids = self.search.get_ids_for_page(1)
        self.assertEqual(2, send_mock.call_count)
        self.assertListEqual(["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"], ids)

        # Same page.
        ids = self.search.get_ids_for_page(1)
        self.assertEqual(2, send_mock.call_count)
        self.assertListEqual(["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"], ids)

        # Next page.
        ids = self.search.get_ids_for_page(2)
        self.assertEqual(3, send_mock.call_count)
        self.assertListEqual(["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"], ids)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_non_zero_first_page(self, send_mock):
        ids = self.search.get_ids_for_page(2)
        self.assertEqual(3, send_mock.call_count)
        self.assertListEqual(["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"], ids)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_non_zero_first_page_fills_cache(self, send_mock):
        ids = self.search.get_ids_for_page(2)
        self.assertEqual(3, send_mock.call_count)
        self.assertListEqual(["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"], ids)

        ids = self.search.get_ids_for_page(1)
        self.assertEqual(3, send_mock.call_count)  # no extra search calls.
        self.assertListEqual(["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"], ids)

        ids = self.search.get_ids_for_page(0)
        self.assertEqual(3, send_mock.call_count)  # no extra search calls.
        self.assertListEqual(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], ids)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_midstream_key_change(self, send_mock):
        # First page, 0.
        ids = self.search.get_ids_for_page(0)
        self.assertListEqual(["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"], ids)
        self.assertEqual(1, send_mock.call_count)

        # Next page.
        ids = self.search.get_ids_for_page(1)
        self.assertListEqual(["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"], ids)
        self.assertEqual(2, send_mock.call_count)

        # New key, say after a delay.
        self.search.scroll_key = uuid.uuid4()
        self.search.save()
        send_mock.side_effect = scroll_effect  # new key == new scroll

        # Next page.
        ids = self.search.get_ids_for_page(2)
        self.assertListEqual(["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"], ids)
        self.assertEqual(3 + 2, send_mock.call_count)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_exhausts_population(self, send_mock):
        ids = self.search.get_ids_for_page(3)
        self.assertListEqual(["wp:16", "wp:17", "wp:18", "wp:19"], ids)
        self.assertEqual(4, send_mock.call_count)

        ids = self.search.get_ids_for_page(4)
        self.assertListEqual([], ids)
        self.assertEqual(5, send_mock.call_count)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_empty_list_is_valid_cache_hit(self, send_mock):
        ids = self.search.get_ids_for_page(4)
        self.assertListEqual([], ids)
        self.assertEqual(5, send_mock.call_count)

        # Should be same as above.
        ids = self.search.get_ids_for_page(4)
        self.assertListEqual([], ids)
        self.assertEqual(5, send_mock.call_count)

    @patch(
        "whoweb.search.models.ScrollSearch.send_scroll_search",
        side_effect=scroll_effect,
    )
    def test_exhausted_population_short_circuits_later_pages(self, send_mock):
        ids = self.search.get_ids_for_page(4)
        self.assertListEqual([], ids)
        self.assertEqual(5, send_mock.call_count)

        ids = self.search.get_ids_for_page(10)
        self.assertListEqual([], ids)
        self.assertEqual(5, send_mock.call_count)
