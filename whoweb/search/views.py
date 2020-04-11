import csv
import itertools

from django.http import StreamingHttpResponse, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from rest_framework import mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.search.models import ResultProfile
from whoweb.search.models.export import SearchExportPage
from .events import DOWNLOAD_VALIDATION, DOWNLOAD
from .models import SearchExport
from .serializers import (
    SearchExportSerializer,
    SearchExportDataSerializer,
    ResultProfileSerializer,
)


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@require_GET
def download(request, uuid, filetype="csv", *args, **kwargs):
    try:
        export = SearchExport.objects.get(uuid=uuid)
    except SearchExport.DoesNotExist:
        raise Http404("Export not found")
    export.log_event(
        evt=DOWNLOAD, data={"request": repr(request), "headers": repr(request.headers)}
    )

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

    export.log_event(
        evt=DOWNLOAD_VALIDATION,
        data={"request": repr(request), "headers": repr(request.headers)},
    )
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
    NestedViewSetMixin,
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


class ExportResultsSetPagination(PageNumberPagination):
    page_size = 1
    page_size_query_param = "page_size"
    max_page_size = 1


class SearchExportResultViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet
):
    pagination_class = ExportResultsSetPagination
    serializer_class = SearchExportDataSerializer
    queryset = SearchExportPage.objects.filter(data__isnull=False)
    permission_classes = [IsAdminUser]

    def retrieve(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        qs_page = self.paginate_queryset(queryset)
        if qs_page is not None:
            serializer = self.get_serializer(
                itertools.chain(
                    *[
                        (ResultProfile(**profile).dict() for profile in page.data)
                        for page in qs_page
                    ]
                ),
                many=True,
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            itertools.chain(
                *(
                    (ResultProfile(**profile).dict() for profile in page.data)
                    for page in queryset
                )
            ),
            many=True,
        )
        return Response(serializer.data)


class DeriveProfileViewSet(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = ResultProfileSerializer
    permission_classes = [IsSuperUser]
