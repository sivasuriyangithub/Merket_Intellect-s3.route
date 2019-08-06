from functools import partial

import uuid as uuid
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Create your models here.
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel

from whoweb.contrib.postgres.fields import EmbeddedModelField, ChoiceArrayField
from whoweb.contrib.fields import CompressedBinaryField
from whoweb.search.models import FilteredSearchQuery

User = get_user_model()


class SearchExport(TimeStampedModel):
    ALL_COLUMNS = {
        0: "invitekey",
        1: "First Name",
        2: "Last Name",
        3: "Title",
        4: "Company",
        5: "Industry",
        6: "City",
        7: "State",
        8: "Country",
        9: "Profile URL",
        10: "Experience",
        11: "Education",
        12: "Skills",
        13: "Email",
        14: "Email Grade",
        15: "LinkedIn URL",
        16: "Phone Number",
        17: "Additional Emails",
        18: "Facebook",
        19: "Twitter",
        20: "AngelList",
        21: "Google Plus",
        22: "Google Profile",
        23: "Quora",
        24: "GitHub",
        25: "BitBucket",
        26: "StackExchange",
        27: "Flickr",
        28: "YouTube",
        29: "domain",
        30: "mxdomain",
    }
    INTRO_COLS = [0]
    BASE_COLS = list(range(1, 18))
    DERIVATION_COLS = list(range(18, 29))
    UPLOADABLE_COLS = [29, 30]
    EXPANDABLE_COLS = [10, 11, 12, 16, 17]

    STATUS = Choices(
        ("created", "Created"),
        ("pages_working", "Pages Running"),
        ("pages_complete", "Pages Complete"),
        ("validating", "Awaiting External Validation"),
        ("post_processing", "Running Post Processing Hooks"),
        ("complete", "Export Complete"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4)
    query = EmbeddedModelField(FilteredSearchQuery, blank=False)
    validation_list_id = models.CharField(max_length=50, null=True, editable=False)
    columns = ChoiceArrayField(
        base_field=models.IntegerField(
            choices=[(k, v) for k, v in ALL_COLUMNS.items()]
        ),
        default=partial(list, BASE_COLS),
    )
    status = StatusField(_("status"), default="created")
    status_changed = MonitorField(_("status changed"), monitor="status")
    sent = models.CharField(max_length=255, editable=False)
    sent_at = models.DateTimeField()
    progress_counter = models.IntegerField(default=0)
    target = models.IntegerField(default=0)
    notify = models.BooleanField(default=False)
    charge = models.BooleanField(default=False)
    uploadable = models.BooleanField(default=False, editable=False)

    on_trial = models.BooleanField(default=False)  # ????

    # Managers
    objects = models.Manager()
    internal = QueryManager(uploadable=False)

    @property
    def with_invites(self):
        return self.should_derive_email and self.query.with_invites

    @property
    def should_derive_email(self):
        return "contact" not in self.query.defer or []

    def set_columns(self, indexes=(), save=False):
        if indexes:
            self.columns = indexes
        elif self.with_invites:
            self.columns = self.INTRO_COLS + self.BASE_COLS + self.DERIVATION_COLS
        elif self.should_derive_email:
            self.columns = self.BASE_COLS + self.DERIVATION_COLS
        else:
            self.columns = self.BASE_COLS
        if self.uploadable and not indexes:
            self.columns = self.columns + self.UPLOADABLE_COLS

        if save:
            self.save()

    def get_column_names(self):
        if self.uploadable:
            return [
                SearchExport.ALL_COLUMNS[idx].lower().replace(" ", "_")
                for idx in self.columns
            ]
        else:
            return [SearchExport.ALL_COLUMNS[idx] for idx in self.columns]


class SearchExportPage(TimeStampedModel):
    export = models.ForeignKey(SearchExport, on_delete=models.CASCADE)
    data = CompressedBinaryField(null=True, editable=False)
    page = models.PositiveIntegerField()
    working_data = JSONField(editable=False)
    count = models.IntegerField(default=0)
    target = models.IntegerField(null=True)
