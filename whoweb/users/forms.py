from django import forms
from django.contrib.auth import get_user_model

from whoweb.users.models import GroupOwner, Seat

User = get_user_model()


class GroupOwnerAdminForm(forms.ModelForm):
    class Meta:
        model = GroupOwner
        fields = "__all__"
        labels = {"organization_user": "Seat", "organization": "Network"}


class SeatAdminForm(forms.ModelForm):
    class Meta:
        model = Seat
        fields = "__all__"
        labels = {"organization_user": "Seat", "organization": "Network"}
