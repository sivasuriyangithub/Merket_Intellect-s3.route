from whoweb.contrib.rest_framework.filters import BaseFilterBackend
from whoweb.payments.models import BillingAccount


class BillingAccountMemberPermissionsFilter(BaseFilterBackend):
    """
    A filter backend that limits results to those where the requesting user
    has read object level permissions.
    """

    shortcut_kwargs = {
        "perms": "view_billingaccountmembers",
        "klass": BillingAccount,
        "accept_global_perms": False,
    }

    def filter_queryset(self, request, queryset, view):
        # We want to defer this import until runtime, rather than import-time.
        # See https://github.com/encode/django-rest-framework/issues/4608
        # (Also see #1624 for why we need to make this import explicitly)
        from guardian.shortcuts import get_objects_for_user

        return queryset.filter(
            organization_id__in=get_objects_for_user(
                request.user, **self.shortcut_kwargs
            ).values_list("pk", flat=True)
        )
