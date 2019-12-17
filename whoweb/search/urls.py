from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r"exports", views.SearchExportViewSet, basename="searchexport")
router.register(
    r"export-results", views.SearchExportResultViewSet, basename="exportresult"
)

app_name = "search"
urlpatterns = [
    path(
        "exports/<uuid:uuid>/download/results.<str:filetype>",
        view=views.download,
        name="download_export",
    ),
    path(
        "exports/<uuid:uuid>/download/<uuid:same_uuid>__fetch.<str:filetype>",
        view=views.download,
        name="download_export_with_named_file_ext",
    ),
    path("export/<uuid:uuid>/validate/", view=views.validate, name="validate_export"),
]
