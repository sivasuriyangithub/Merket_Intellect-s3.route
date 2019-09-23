import csv
import json

from django.http import StreamingHttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from rest_framework import viewsets
from slugify import slugify

from whoweb.payments.models import BillingAccount
from whoweb.users.models import UserProfile  # for type
from .events import DOWNLOAD_VALIDATION, DOWNLOAD
from .models import SearchExport
from .serializers import SearchExportSerializer


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@require_POST
def create(request):
    from whoweb.users.models import Group

    data = json.loads(request.body)
    xperweb_id = data["xperweb_id"]
    email = data["email"]
    group_name = data["group_name"]
    group_id = data.get("group_id", group_name)
    creds = data["credits"]
    query = data["query"]
    uploadable = data["for_campaign"]
    billing_account_name = f"{group_name} Primary Billing Account"

    profile, _ = UserProfile.get_or_create(username=xperweb_id, email=email)
    group, _ = Group.objects.get_or_create(name=group_name, slug=slugify(group_id))
    seat, _ = group.get_or_add_user(user=profile.user)
    billing_account = BillingAccount.objects.get_or_create(
        name=billing_account_name, slug=slugify(billing_account_name), group=group
    )
    billing_member, _ = billing_account.get_or_add_user(
        user=profile.user, seat=seat, seat_credits=creds
    )
    export = SearchExport.create_from_query(
        seat=seat, query=query, uploadable=uploadable
    )
    return JsonResponse(SearchExportSerializer(export).data)


@require_GET
def download(request, uuid):
    try:
        export = SearchExport.objects.get(uuid=uuid)
    except SearchExport.DoesNotExist:
        raise Http404("Export not found")
    export.log_event(evt=DOWNLOAD, data={"request": repr(request)})

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (
            writer.writerow([(x.encode("utf-8") if x else "") for x in row])
            for row in export.generate_csv_rows()
        ),
        content_type="text/csv",
    )
    response["Content-Disposition"] = (
        f"attachment; "
        f"filename='whoknows_search_results_{export.created.date()}__fetch.csv'"
    )
    return response


@require_GET
def validate(request, uuid):
    try:
        export = SearchExport.objects.get(uuid=uuid)
    except SearchExport.DoesNotExist:
        raise Http404("Export not found")

    export.log_event(evt=DOWNLOAD_VALIDATION, data={"request": repr(request)})
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (
            writer.writerow([(x.encode("utf-8") if x else "") for x in row])
            for row in export.get_ungraded_email_rows()
        ),
        content_type="text/csv",
    )
    response["Content-Disposition"] = (
        f"attachment; " f"filename='wk_validation_{export.created.date()}.csv'"
    )
    return response


class SearchExportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SearchExport.objects.all().order_by("-created")
    serializer_class = SearchExportSerializer
