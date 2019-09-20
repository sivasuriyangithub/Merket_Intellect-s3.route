import csv

from django.http import StreamingHttpResponse, Http404
from django.views.decorators.http import require_GET

from whoweb.search.events import DOWNLOAD_VALIDATION, DOWNLOAD
from whoweb.search.models import SearchExport


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


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
