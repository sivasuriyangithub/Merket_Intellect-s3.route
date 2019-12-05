import csv

from django.http import (
    StreamingHttpResponse,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.views.decorators.http import require_GET
from rest_framework import mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import GenericViewSet

from whoweb.contrib.rest_framework.permissions import IsSuperUser
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


@require_GET
def download(request, uuid, filetype="csv"):
    try:
        export = SearchExport.objects.get(uuid=uuid)
    except SearchExport.DoesNotExist:
        raise Http404("Export not found")
    export.log_event(evt=DOWNLOAD, data={"request": repr(request)})

    pseudo_buffer = Echo()
    if filetype == "csv":
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in export.generate_csv_rows()),
            content_type="text/csv",
        )
        response[
            "Content-Disposition"
        ] = f"attachment; filename=whoknows_search_results_{export.created.date()}.csv"
        return response
    elif filetype == "json":

        def content():
            rows = export.generate_json_rows()
            yield '{"results":['
            first = True
            while True:
                try:
                    row = rows.__next__()
                except StopIteration:
                    yield "]}"
                    break
                else:
                    if first:
                        yield row
                        first = False
                    else:
                        yield "," + row

        response = StreamingHttpResponse(
            content(), content_type="application/json; charset=UTF-8"
        )
        response[
            "Content-Disposition"
        ] = f"attachment; filename=whoknows_search_results_{export.created.date()}.json"
        return response
    return HttpResponseBadRequest("Unknown file format requested.")


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
        (writer.writerow(row) for row in export.get_ungraded_email_rows()),
        content_type="text/csv",
    )
    response[
        "Content-Disposition"
    ] = f"attachment; filename=wk_validation_{export.created.date()}.csv"
    return response


class SearchExportViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = SearchExport.objects.all().order_by("-created")
    serializer_class = SearchExportSerializer
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]
