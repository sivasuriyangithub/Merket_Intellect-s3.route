import pytest

from .factories import ColdCampaignFactory
from ..models import ColdCampaign


@pytest.fixture
def cold_campaign() -> ColdCampaign:
    return ColdCampaignFactory()
