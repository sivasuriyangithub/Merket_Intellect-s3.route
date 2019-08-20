from django.test import SimpleTestCase

from whoweb.search.models import ResultProfile
from .fixtures import pending, done


class TestResultProfile(SimpleTestCase):
    def setUp(self):
        super(TestResultProfile, self).setUp()
        self.maxDiff = None

    def test_load_underived_profile(self):
        result_profile = ResultProfile(**pending[0])
        self.assertIsNone(result_profile.email)
        self.assertEqual("Tirlea", result_profile.last_name)

    def test_load_derived_profile(self):
        result_profile = ResultProfile(**done[0])
        self.assertEqual("patrick@beast.vc", result_profile.email)
        self.assertEqual("Strong", result_profile.last_name)

    def test_load_unload_underived_profile(self):
        result_profile = ResultProfile(**pending[0])
        once = result_profile.to_json()
        loaded = ResultProfile.from_json(once)
        self.assertEqual(result_profile.last_name, loaded.last_name)
        self.assertDictEqual(once, loaded.to_json())

    def test_load_unload_derived_profile(self):
        result_profile = ResultProfile(**done[0])

        once = result_profile.to_json()
        loaded = ResultProfile.from_json(once)

        self.assertEqual(result_profile.last_name, loaded.last_name)
        self.assertDictEqual(once, loaded.to_json())
