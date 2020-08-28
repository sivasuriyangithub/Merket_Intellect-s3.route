from typing import Optional, List, Dict, Any

from django.contrib.auth import get_user_model
from pydantic import BaseModel

from whoweb.payments.models import BillingAccountMember
from whoweb.users.models import Seat

User = get_user_model()


class FilterValueList(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    tags: List[str] = []
    values: List[str] = []
