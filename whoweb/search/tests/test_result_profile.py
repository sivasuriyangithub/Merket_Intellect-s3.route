from whoweb.search.models import ResultProfile
from .fixtures import pending, done


def test_load_underived_profile():
    result_profile = ResultProfile(**pending[0])
    assert result_profile.email is None
    assert "Tirlea" == result_profile.last_name


def test_load_derived_profile():
    result_profile = ResultProfile(**done[0])
    assert "patrick@beast.vc" == result_profile.email
    assert "Strong" == result_profile.last_name


def test_load_unload_underived_profile():
    result_profile = ResultProfile(**pending[0])
    once = result_profile.to_json()
    loaded = ResultProfile.from_json(once)
    assert result_profile.last_name, loaded.last_name
    assert once == loaded.to_json()


def test_load_unload_derived_profile():
    result_profile = ResultProfile(**done[0])

    once = result_profile.to_json()
    loaded = ResultProfile.from_json(once)

    assert result_profile.last_name == loaded.last_name
    assert once == loaded.to_json()
