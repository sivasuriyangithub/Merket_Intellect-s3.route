from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.models import ResultProfile, DerivedContact


def test_load_underived_profile(search_results):
    result_profile = ResultProfile(**search_results[0])
    assert result_profile.email is None
    assert "Tirlea" == result_profile.last_name


def test_load_derivation(raw_derived):
    derivation = DerivedContact(**raw_derived[0])
    assert "patrick@beast.vc" == derivation.email


def test_load_derived_profile(raw_derived):
    result_profile = ResultProfile(**raw_derived[0])
    assert "patrick@beast.vc" == result_profile.email
    assert "Strong" == result_profile.last_name


def test_load_unload_underived_profile(search_results):
    for search_result in search_results:
        result_profile = ResultProfile(**search_result)
        print(result_profile)
        once = result_profile.dict()
        loaded = ResultProfile(**once)
        twice = loaded.dict()
        assert result_profile.last_name, loaded.last_name
        assert once == twice


def test_load_unload_derived_profile(raw_derived):
    result_profile = ResultProfile(**raw_derived[0])

    once = result_profile.dict()
    loaded = ResultProfile(**once)

    assert result_profile.last_name == loaded.last_name
    assert once == loaded.dict()
