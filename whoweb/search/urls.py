from django.urls import path
from rest_framework_extensions.routers import ExtendedSimpleRouter

from . import views

router = ExtendedSimpleRouter()
router.register(r"exports", views.SearchExportViewSet, basename="export").register(
    r"results",
    views.SearchExportResultViewSet,
    basename="exports-result",
    parents_query_lookups=["export__uuid"],
)

app_name = "search"
urlpatterns = [
    path(
        "exports/<uuid:uuid>/download/results.csv",
        view=views.download,
        name="download_export",
    ),
    path(
        "exports/<uuid:uuid>/download/<uuid:same_uuid>__fetch.csv",
        view=views.download,
        name="download_export_with_named_file_ext",
    ),
    path("export/<uuid:uuid>/validate/", view=views.validate, name="validate_export"),
] + router.urls
