from django import forms

from whoweb.payments.models import BillingAccountMember, BillingAccountOwner


class BillingAccountMemberAdminForm(forms.ModelForm):
    class Meta:
        model = BillingAccountMember
        exclude = ("user",)
        labels = {"organization": "Billing account"}
        help_texts = {
            "credits": "Save this object with Pool Credits unchecked to edit this field.",
            "trial_credits": "Save this object with Pool Credits unchecked to edit this field.",
        }


class BillingAccountMemberAdminInlineForm(forms.ModelForm):
    class Meta:
        model = BillingAccountMember
        exclude = ("user",)
        labels = {"organization": "Billing account"}
        help_texts = {
            "seat_credits": "Save this object with Pool Credits unchecked to edit this field.",
            "seat_trial_credits": "Save this object with Pool Credits unchecked to edit this field.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pool_credits:
            self.fields["seat_credits"].widget = forms.PasswordInput(
                attrs={"readonly": "readonly", "size": 1}
            )
            self.fields["seat_trial_credits"].widget = forms.PasswordInput(
                attrs={"readonly": "readonly", "size": 1}
            )

    def save_model(self, request, obj, form, change):
        obj.user = obj.seat.user
        super().save_model(request, obj, form, change)


class BillingAccountOwnerAdminForm(forms.ModelForm):
    class Meta:
        model = BillingAccountOwner
        fields = "__all__"
        labels = {
            "organization": "Billing account",
            "organization_user": "Billing account member",
        }
