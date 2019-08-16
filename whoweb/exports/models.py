import logging
import uuid as uuid
from copy import deepcopy
from functools import partial

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, DatabaseError, transaction
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel

from whoweb.contrib.fields import CompressedBinaryField
from whoweb.contrib.postgres.fields import EmbeddedModelField, ChoiceArrayField
from whoweb.core.router import router
from whoweb.search.models import FilteredSearchQuery, ScrollSearch

logger = logging.getLogger(__name__)
User = get_user_model()


class SearchExport(TimeStampedModel):
    DERIVATION_RATIO = 5.2
    SIMPLE_CAP = 1000

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
    scroll = models.ForeignKey(ScrollSearch, on_delete=models.SET_NULL, null=True)
    uuid = models.UUIDField(default=uuid.uuid4)
    query = EmbeddedModelField(
        FilteredSearchQuery, blank=False, default=FilteredSearchQuery
    )
    validation_list_id = models.CharField(max_length=50, null=True, editable=False)
    columns = ChoiceArrayField(
        base_field=models.IntegerField(
            choices=[(k, v) for k, v in ALL_COLUMNS.items()]
        ),
        default=partial(list, BASE_COLS),
        editable=False,
    )
    status = StatusField(_("status"), default="created")
    status_changed = MonitorField(_("status changed"), monitor="status")
    sent = models.CharField(max_length=255, editable=False)
    sent_at = MonitorField(
        _("sent at"), monitor="sent", editable=False, null=True, default=None
    )
    progress_counter = models.IntegerField(default=0)
    target = models.IntegerField(default=0)
    notify = models.BooleanField(default=False)
    charge = models.BooleanField(default=False)
    uploadable = models.BooleanField(default=False, editable=False)

    on_trial = models.BooleanField(default=False)  # ????

    # Managers
    objects = models.Manager()
    internal = QueryManager(uploadable=False)

    def should_derive_email(self):
        return bool("contact" not in (self.query.defer or []))

    should_derive_email.boolean = True
    should_derive_email.short_description = "Derive Emails"

    def with_invites(self):
        return bool(self.should_derive_email() and self.query.with_invites)

    with_invites.boolean = True
    with_invites = property(with_invites)

    @property
    def skip(self):
        return self.query.filters.skip

    @property
    def specified_ids(self):
        top_level = self.query.filters.profiles
        if top_level:
            return top_level
        plus_ids = set()
        minus_ids = set()
        for required in self.query.filters.required:
            if required.field == "_id":
                if required.truth is True:
                    plus_ids.update(required.value or [])
                if required.truth is False:
                    minus_ids.update(required.value or [])
        return list(plus_ids.difference(minus_ids))

    @specified_ids.setter
    def specified_ids(self, ids):
        self.query.filters.profiles = ids

    @property
    def num_ids_needed(self):
        remaining_profile_count = self.target - self.progress_counter
        if not self.specified_ids and self.should_derive_email:
            return int(remaining_profile_count * self.DERIVATION_RATIO)
        else:
            return remaining_profile_count

    @property
    def start_from_count(self):
        progress_plus_skip = self.progress_counter + self.skip
        if not self.specified_ids and self.should_derive_email:
            return int(progress_plus_skip * self.DERIVATION_RATIO)
        else:
            return progress_plus_skip

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

    def simple_search(self):
        query = self.query.serialize()
        query["ids_only"] = True
        query["filters"]["limit"] = self.num_ids_needed
        query["filters"]["skip"] = self.start_from_count

        results = router.unified_search(
            json=query, timeout=120, encoder=DjangoJSONEncoder
        ).get("results", [])
        ids = [result["profile_id"] for result in results]
        return ids

    def ensure_scroll_interface(self, force=False):
        if self.scroll is None:
            search, created = ScrollSearch.get_or_create(
                query=self.query, user_id=self.user_id
            )
            self.scroll = search
            self.save()
        return self.scroll.ensure_live(force=force)

    def _generate_pages(self):
        if self.specified_ids:
            ids = self.specified_ids[self.start_from_count :]
            if not ids:
                return
        elif self.num_ids_needed < self.SIMPLE_CAP:
            ids = self.simple_search()
            if not ids:
                return
        else:
            ids = []

        search = self.ensure_scroll_interface(force=True)

        pages = []

        if ids:
            num_ids_needed = min(self.num_ids_needed, len(ids))
        elif self.start_from_count >= self.population():
            return
        elif self.num_ids_needed + self.start_from_count > self.population():
            num_ids_needed = self.population() - self.start_from_count
        else:
            num_ids_needed = self.num_ids_needed

        num_pages = int(ceil(float(num_ids_needed) / search.page_size))
        last_completed_page = (
            ExportPage.objects(pk__in=self.page_ids, data__exists=True)
            .order_by("-page")
            .first()
        )
        if not last_completed_page:
            start_page = int(ceil(float(self.start_from_count) / search.page_size))
        else:
            start_page = last_completed_page.page + 1

        if ids:
            # Mock scroll with given ids.
            for page in range(start_page, num_pages + start_page):
                page_ids = ids[: search.page_size]
                search.set_web_ids(
                    ids=page_ids, page=page
                )  # mock the page results so we don't store ids over and over again
                pages.append(ExportPage.create(page_num=page, export=self))
                ids = ids[search.page_size :]
                if len(ids) == 0:
                    break

        else:
            # Actual Scrolling
            for page in range(start_page, num_pages + start_page):
                logger.debug("Eagerly fetching page %d of scroll", page)
                profile_ids = search.get_page(page=page, ids_only=True)
                if profile_ids:
                    pages.append(ExportPage.create(page_num=page, export=self))
                else:
                    break

        if pages:
            # Last page
            remainder = num_ids_needed % search.page_size
            if remainder > 0:
                pages[-1].modify(
                    target=remainder
                )  # set target so we dont try to derive the whole page
            for page in pages:
                self.modify(add_to_set__pages=page)
            return pages

    def generate_pages(self, task_context=None):
        try:
            export = SearchExport.objects.select_for_update(
                nowait=True, of=("self",)
            ).get(pk=self.pk)
        except DatabaseError as e:
            logger.exception(e)
            return
        self.log_event(message=GENERATING_PAGES, task=task_context)
        with transaction.atomic():
            export._generate_pages()


class SearchExportPage(TimeStampedModel):
    export = models.ForeignKey(
        SearchExport, on_delete=models.CASCADE, related_name="pages"
    )
    data = CompressedBinaryField(null=True, editable=False)
    page = models.PositiveIntegerField()
    working_data = JSONField(editable=False)
    count = models.IntegerField(default=0)
    target = models.IntegerField(null=True)
