from django.urls import path

from . import views

app_name = "search"
urlpatterns = [
    path(
        "export/<uuid:uuid>/download/results.csv",
        view=views.download,
        name="download_export",
    ),
    path(
        "export/<uuid:uuid>/download/<uuid:same_uuid>__fetch.csv",
        view=views.download,
        name="download_export_with_named_file_ext",
    ),
    path("export/<uuid:uuid>/validate/", view=views.validate, name="validate_export"),
]
