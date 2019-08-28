import csv
import logging
import uuid as uuid
import zipfile
from functools import partial
from math import ceil
from typing import Optional, List

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.utils.six import string_types, StringIO
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel

from whoweb.contrib.fields import CompressedBinaryField
from whoweb.contrib.postgres.fields import EmbeddedModelField, ChoiceArrayField
from whoweb.core.models import ModelEvent
from whoweb.core.router import router
from whoweb.search.events import (
    GENERATING_PAGES,
    FINALIZING,
    POST_VALIDATION,
    FETCH_VALIDATION,
)
from whoweb.search.models import ResultProfile
from .scroll import FilteredSearchQuery, ScrollSearch

logger = logging.getLogger(__name__)
User = get_user_model()


class SearchExport(TimeStampedModel):
    DERIVATION_RATIO = 5.2
    SIMPLE_CAP = 1000
    SKIP_CODE = "MAGIC_SKIP_CODE_NO_VALIDATION_NEEDED"

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
        (0, "created", "Created"),
        (2, "pages_working", "Pages Running"),
        (4, "pages_complete", "Pages Complete"),
        (8, "validating", "Awaiting External Validation"),
        (16, "post_processing", "Running Post Processing Hooks"),
        (32, "complete", "Export Complete"),
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
    status = StatusField(_("status"), db_index=True)
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

    events = GenericRelation(ModelEvent, related_query_name="export")

    # Managers
    objects = models.Manager()
    internal = QueryManager(uploadable=False)

    class Meta:
        verbose_name = "export"

    def locked(self):
        return (
            self.__class__.objects.filter(id=self.pk)
            .select_for_update(skip_locked=True, of=("self",))
            .first()
        )

    def is_done_processing_pages(self):
        return (
            int(self.status) >= SearchExport.STATUS.pages_complete
            or self.progress_counter >= self.target
        )

    is_done_processing_pages.boolean = True
    is_done_processing_pages = property(is_done_processing_pages)

    def should_derive_email(self):
        return bool("contact" not in (self.query.defer or []))

    should_derive_email.boolean = True
    should_derive_email.short_description = "Derive Emails"
    should_derive_email = property(should_derive_email)

    def defer_validation(self):
        return FilteredSearchQuery.DEFER_VALIDATION in self.query.defer

    defer_validation.boolean = True
    defer_validation = property(defer_validation)

    def with_invites(self):
        return bool(self.should_derive_email and self.query.with_invites)

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

    def ensure_search_interface(self, force=False):
        if self.scroll is None:
            search, created = ScrollSearch.get_or_create(
                query=self.query, user_id=self.user_id
            )
            self.scroll = search
            self.save()
        return self.scroll.ensure_live(force=force)

    def _generate_pages(self) -> Optional[List["SearchExportPage"]]:
        """

        :return: List of export pages for which search cache has been primed.
        :rtype:
        """
        if self.specified_ids:
            ids = self.specified_ids[self.start_from_count :]
            if not ids:
                return
        elif self.num_ids_needed < self.SIMPLE_CAP:
            search = self.ensure_search_interface()
            ids = search.send_simple_search(
                limit=self.num_ids_needed, skip=self.start_from_count
            )
            if not ids:
                return
        else:
            ids = []

        search = self.ensure_search_interface(force=True)

        pages = []

        if ids:
            num_ids_needed = min(self.num_ids_needed, len(ids))
        elif self.start_from_count >= search.population():
            return
        elif self.num_ids_needed + self.start_from_count > search.population():
            num_ids_needed = search.population() - self.start_from_count
        else:
            num_ids_needed = self.num_ids_needed

        num_pages = int(ceil(float(num_ids_needed) / search.page_size))
        last_completed_page = self.pages.filter(data__isnull=False).last()

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
                pages.append(SearchExportPage(page_num=page, export=self))
                ids = ids[search.page_size :]
                if len(ids) == 0:
                    break

        else:
            # Actual Scrolling
            for page in range(start_page, num_pages + start_page):
                logger.debug("Eagerly fetching page %d of scroll", page)
                profile_ids = search.get_page(page=page, ids_only=True)
                if profile_ids:
                    pages.append(SearchExportPage(page_num=page, export=self))
                else:
                    break

        if pages:
            # Last page
            remainder = num_ids_needed % search.page_size
            if remainder > 0:
                pages[-1].limit = remainder
                # set limit so we dont try to derive the whole page
            return SearchExportPage.objects.bulk_create(pages)

    def generate_pages(self, task_context=None):
        with transaction.atomic():
            export = self.locked()
            if export:
                self.log_event(GENERATING_PAGES, task=task_context)
                export.status = SearchExport.STATUS.pages_working
                export.save()
                return export._generate_pages()

    def _do_post_page_completion(self):
        if self.charge:
            if self.progress_counter < self.target:
                # TODO: refunds
                # self.user(inc__credits=self.target - self.progress_counter)
                self.charged = self.target - self.progress_counter
            else:
                self.charged = self.target
            self.status = SearchExport.STATUS.pages_complete
            self.save()

    def do_post_page_completion(self, task_context=None):
        with transaction.atomic():
            export = self.locked()
            if export:
                self.log_event(FINALIZING, task=task_context)
                return export._do_post_page_completion()

    def upload_validation(self, task_context=None):
        self.log_event(POST_VALIDATION, task=task_context)
        self.status = SearchExport.STATUS.validating
        try:
            _ = self.get_ungraded_email_rows().__next__()
        except StopIteration:
            # empty
            self.validation_list_id = self.SKIP_CODE
            self.save()
            return

        r = requests.post(
            "{}/list/create_from_url/".format(settings.DATAVALIDATION_URL),
            headers={"Authorization": "Bearer {}".format(settings.DATAVALIDATION_KEY)},
            data=dict(
                url=self.generate_validation_url(),
                name=self.uuid.hex,
                email_column_index=0,
                has_header=0,
                start_validation=True,
            ),
        )
        if not r.ok:
            logger.error(
                "Validation API Error: %s. Response: %s ", r.status_code, r.content
            )
        self.validation_list_id = r.json()
        self.save()

    def get_validation_status(self, task_context=None):
        if self.validation_list_id == self.SKIP_CODE:
            return True

        self.log_event(FETCH_VALIDATION, task=task_context)

        status = requests.get(
            "{}/list/{}/".format(settings.DATAVALIDATION_URL, self.validation_list_id),
            headers={"Authorization": "Bearer {}".format(settings.DATAVALIDATION_KEY)},
        ).json()

        if status.get("status_value") == "FAILED":
            return False

        if status.get("status_percent_complete", 0) < 100:
            return False

        r = requests.head(
            "{}/list/{}/download_result/".format(
                settings.DATAVALIDATION_URL, self.validation_list_id
            ),
            headers={"Authorization": "Bearer {}".format(settings.DATAVALIDATION_KEY)},
            stream=True,
        )
        return r.ok

    def get_validation_results(self):
        if self.validation_list_id == self.SKIP_CODE:
            return []
        r = requests.get(
            "{}/list/{}/download_result/".format(
                settings.DATAVALIDATION_URL, self.validation_list_id
            ),
            headers={"Authorization": "Bearer {}".format(settings.DATAVALIDATION_KEY)},
            stream=True,
        )
        r.raise_for_status()

        z = zipfile.ZipFile(StringIO(r.content))

        for name in z.namelist():
            data = StringIO(z.read(name))
            reader = csv.reader(data)
            for row in reader:
                logger.debug(row)
                if len(row) != 3:
                    continue
                yield {"email": row[0], "profile_id": row[1], "grade": row[2]}

    def return_validation_results_to_cache(self):
        upload_limit = 250
        results_gen = self.get_validation_results()
        while True:
            secondary_validations = []
            i = 0
            for row in results_gen:
                i += 1
                secondary_validations.append(row)
                if i == upload_limit:
                    break

            if secondary_validations:
                try:
                    router.update_validations(
                        json={"bulk_validations": secondary_validations}, timeout=90
                    )
                except Exception as e:
                    logger.exception("Error setting validation cache: %s " % e)
            else:
                return True

    def processing_signatures(self, on_complete=None):
        from whoweb.search.tasks import (
            process_export,
            check_export_has_data,
            validate_rows,
            fetch_validation_results,
            send_notification,
            refund_against_target,
            spawn_mx_group,
            header_check,
        )

        sigs = process_export.si(self.pk) | check_export_has_data.si(export_id=self.pk)
        if on_complete:
            sigs |= on_complete
        if self.defer_validation:
            sigs |= validate_rows.si(self.pk) | fetch_validation_results.si(self.pk)
        sigs |= refund_against_target.si(self.pk)
        if self.notify:
            sigs |= send_notification.si(self.pk)
        if self.uploadable:
            sigs |= (
                spawn_mx_group.si(self.pk)
                | header_check.s()  # mutable signature to accept group_id
            )
        return sigs

    def get_raw(self):
        for page in self.pages.iterator(chunk_size=4):
            for row in page.data():
                yield row

    def get_profiles(self, validation_registry=None):
        for profile in self.get_raw():
            if profile:
                yield ResultProfile.from_json(
                    profile, validation_registry=validation_registry
                )

    def get_ungraded_email_rows(self):
        for profile in self.get_profiles():
            if profile.passing_grade:
                continue
            web_id = profile.web_id or profile.id
            graded_emails = set(profile.graded_addresses())
            non_validated_emails = set(profile.emails)
            pending = non_validated_emails.difference(graded_emails)
            for email in pending:
                yield (email, web_id)

    def log_event(self, evt, *, start=None, end=None, task=None, **data):
        if hasattr(task, "id"):
            data["task_id"] = task.id
        if isinstance(evt, string_types):
            code = 0
            message = evt
        else:
            code = evt[0]
            message = evt[1]
        ModelEvent.objects.create(
            ref=self, code=code, message=message, start=start, end=end, data=data
        )


class SearchExportPage(TimeStampedModel):
    export = models.ForeignKey(
        SearchExport, on_delete=models.CASCADE, related_name="pages"
    )
    data = CompressedBinaryField(null=True, editable=False)
    page_num = models.PositiveIntegerField()
    working_data = JSONField(editable=False)
    count = models.IntegerField(default=0)
    limit = models.IntegerField(null=True)

    class Meta:
        unique_together = ["export", "page_num"]
        ordering = ["export", "page_num"]
