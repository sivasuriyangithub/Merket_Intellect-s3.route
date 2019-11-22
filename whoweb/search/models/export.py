import csv
import logging
import uuid as uuid
import zipfile
from datetime import timedelta
from functools import partial
from math import ceil
from typing import Optional, List, Iterable

import requests
from celery import group
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.six import string_types, StringIO
from django.utils.translation import ugettext_lazy as _
from django_celery_results.models import TaskResult
from dns import resolver
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.managers import QueryManagerMixin
from model_utils.models import TimeStampedModel
from requests_cache import CachedSession

from whoweb.contrib.fields import CompressedBinaryJSONField
from whoweb.contrib.postgres.fields import EmbeddedModelField, ChoiceArrayField
from whoweb.core.models import ModelEvent
from whoweb.core.router import router, external_link
from whoweb.search.events import (
    GENERATING_PAGES,
    FINALIZING,
    POST_VALIDATION,
    FETCH_VALIDATION,
    SPAWN_MX,
    POPULATE_DATA,
    DERIVATION_SPAWN,
    FINALIZE_PAGE,
    ENQUEUED_FROM_QUERY,
)
from whoweb.users.models import Seat
from .profile import ResultProfile, WORK, PERSONAL, SOCIAL, PROFILE
from .profile_spec import ensure_profile_matches_spec, ensure_contact_info_matches_spec
from .scroll import FilteredSearchQuery, ScrollSearch

logger = logging.getLogger(__name__)
User = get_user_model()
DATAVALIDATION_URL = "https://dv3.datavalidation.com/api/v2/user/me"


class SubscriptionError(Exception):
    pass


class SearchExportManager(QueryManagerMixin, models.Manager):
    pass


class SearchExport(TimeStampedModel):
    DERIVATION_RATIO = 5.2
    SIMPLE_CAP = 1000
    SKIP_CODE = "MAGIC_SKIP_CODE_NO_VALIDATION_NEEDED"

    ALL_COLUMNS = {
        0: "invitekey",
        1: "Profile ID",
        2: "First Name",
        3: "Last Name",
        4: "Title",
        5: "Company",
        6: "Industry",
        7: "City",
        8: "State",
        9: "Country",
        10: "Email",
        11: "Email Type",
        12: "Email Grade",
        13: "Email 2",
        14: "Email 2 Type",
        15: "Email 2 Grade",
        16: "Email 3",
        17: "Email 3 Type",
        18: "Email 3 Grade",
        19: "Phone Number",
        20: "Phone Number Type",
        21: "Phone Number 2",
        22: "Phone Number 2 Type",
        23: "Phone Number 3",
        24: "Phone Number 3 Type",
        25: "WhoKnows URL",
        26: "LinkedIn URL",
        27: "Facebook",
        28: "Twitter",
        29: "domain",
        30: "mxdomain",
    }
    INTRO_COLS = [0]
    BASE_COLS = list(range(1, 10)) + [25]
    DERIVATION_COLS = list(range(10, 25)) + [26, 27, 28]
    UPLOADABLE_COLS = [29, 30]

    STATUS = Choices(
        (0, "created", "Created"),
        (2, "pages_working", "Pages Running"),
        (4, "pages_complete", "Pages Complete"),
        (8, "validating", "Awaiting External Validation"),
        (16, "validated", "Validation Complete"),
        (32, "post_processed", "Post Processing Hooks Done"),
        (128, "complete", "Export Complete"),
    )

    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    scroll = models.ForeignKey(ScrollSearch, on_delete=models.SET_NULL, null=True)
    uuid = models.UUIDField(default=uuid.uuid4, db_index=True, blank=True)
    query = EmbeddedModelField(
        FilteredSearchQuery, blank=False, default=FilteredSearchQuery
    )
    validation_list_id = models.CharField(max_length=50, null=True, editable=False)
    status = models.IntegerField(
        _("status"), db_index=True, choices=STATUS, blank=True, default=STATUS.created
    )
    status_changed = MonitorField(_("status changed"), monitor="status")
    sent = models.CharField(max_length=255, editable=False)
    sent_at = MonitorField(
        _("sent at"), monitor="sent", editable=False, null=True, default=None
    )
    progress_counter = models.IntegerField(default=0)
    target = models.IntegerField(default=0)
    charged = models.IntegerField(default=0)
    refunded = models.IntegerField(default=0)
    valid_count = models.IntegerField(null=True, blank=True)

    notify = models.BooleanField(default=False)
    charge = models.BooleanField(default=False)
    uploadable = models.BooleanField(default=False, editable=False)

    on_trial = models.BooleanField(default=False)  # ????

    events = GenericRelation(ModelEvent, related_query_name="export")

    # Managers
    objects = SearchExportManager()
    internal = SearchExportManager(uploadable=True)

    class Meta:
        verbose_name = "export"

    def __str__(self):
        return "%s (%s) %s" % (self.__class__.__name__, self.pk, self.uuid.hex)

    @classmethod
    def create_from_query(cls, seat: Seat, query: dict, **kwargs):
        with transaction.atomic():
            export = cls(seat=seat, query=query, **kwargs)
            export._set_target()
            if export.should_derive_email:
                charged = seat.billing.charge(export.target)
                if not charged:
                    raise SubscriptionError(
                        "Not enough credits to complete this export"
                    )
                export.charged = export.target
            export.save()
        tasks = export.processing_signatures()
        res = tasks.apply_async()
        export.log_event(
            evt=ENQUEUED_FROM_QUERY, signatures=str(tasks), async_result=str(res)
        )
        return export

    def locked(self, **kwargs):
        return (
            self.__class__.objects.filter(id=self.pk, **kwargs)
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

    def should_remove_derivation_failures(self):
        return len(self.specified_ids) == 0 or self.uploadable

    should_remove_derivation_failures.boolean = True
    should_remove_derivation_failures = property(should_remove_derivation_failures)

    def defer_validation(self):
        return FilteredSearchQuery.DEFER_CHOICES.VALIDATION in self.query.defer

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

    @property
    def columns(self):
        if self.with_invites:
            columns = self.INTRO_COLS + self.BASE_COLS + self.DERIVATION_COLS
        elif self.should_derive_email:
            columns = self.BASE_COLS + self.DERIVATION_COLS
        else:
            columns = self.BASE_COLS
        if self.uploadable:
            columns = columns + self.UPLOADABLE_COLS
        return sorted(columns)

    def _set_target(self, save=False):
        limit = self.query.filters.limit or 0
        skip = self.query.filters.skip or 0
        initial_query_target = limit - skip
        specified_target = len(self.specified_ids)
        if specified_target > 0:
            initial_query_target = specified_target
        self.target = initial_query_target
        if save:
            self.save()
        return self

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
                query=self.query, user_id=self.seat_id
            )
            self.scroll = search
            self.save()
        return self.scroll.ensure_live(force=force)

    def get_raw(self):
        for page in self.pages.iterator(chunk_size=4):
            for row in page.data:
                yield row

    def get_profiles(self, validation_registry=None, raw=None):
        if raw is None:
            raw = self.get_raw()
        for profile in raw:
            if profile:
                yield ResultProfile.from_json(
                    profile, validation_registry=validation_registry
                )

    def get_ungraded_email_rows(self):
        for profile in self.get_profiles():
            if profile.passing_grade:
                continue
            profile_id = profile.web_id or profile.id
            graded_emails = set(profile.graded_addresses())
            non_validated_emails = set(profile.emails)
            pending = non_validated_emails.difference(graded_emails)
            for email in pending:
                yield (email, profile_id)

    def generate_email_id_pairs(self):

        for profile in self.get_profiles(
            validation_registry=self.get_validation_registry()
        ):
            if profile.email and profile.id:
                yield (profile.email, profile.id)

    def get_csv_row(
        self, profile: ResultProfile, enforce_valid_contact=False, with_invite=False
    ):
        if enforce_valid_contact:
            if not profile.email or not profile.passing_grade:
                return
        row = [
            profile.id,
            profile.first_name,
            profile.last_name,
            profile.title,
            profile.company,
            profile.industry,
            profile.city,
            profile.state,
            profile.country,
        ]
        if enforce_valid_contact:
            for i in range(3):
                try:
                    entry = profile.sorted_graded_emails[i]
                    row.extend([entry.email, "", entry.grade])  # profile.email_type
                except IndexError:
                    row.extend(["", "", ""])
            for i in range(3):
                try:
                    entry = profile.phone[i]
                    row.extend([entry.phone, entry.phone_type, entry.status])
                except IndexError:
                    row.extend(["", "", ""])
        row.append(profile.absolute_profile_url)
        if enforce_valid_contact:
            row.extend([profile.li_url, profile.facebook, profile.twitter])
        if with_invite:
            key = profile.get_invite_key(profile.email)
            if not key:
                return
            row = [key] + row
        if self.uploadable:
            row += [profile.domain or "", profile.mx_domain or ""]
        return row

    def generate_csv_rows(self, rows=None, validation_registry=None):
        if validation_registry is None:
            validation_registry = self.get_validation_registry()

        profiles = partial(
            self.get_profiles, validation_registry=validation_registry, raw=rows
        )  # resettable generator, because we have to walk this twice.

        mx_registry = MXDomain.registry_for_domains(
            domains=[profile.domain for profile in profiles() if profile.domain]
        )
        mx_profiles = (
            profile.set_mx(mx_registry=mx_registry) for profile in profiles()
        )
        yield self.get_column_names()
        for _ in range(self.target):
            try:
                profile = mx_profiles.__next__()
            except StopIteration:
                return
            yield self.get_csv_row(
                profile,
                enforce_valid_contact=self.should_derive_email,
                with_invite=self.with_invites,
            )

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
            start_page = last_completed_page.page_num + 1

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
                profile_ids = search.get_ids_for_page(page=page)
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
            return SearchExportPage.objects.bulk_create(pages, ignore_conflicts=True)

    def generate_pages(self, task_context=None):
        with transaction.atomic():
            export = self.locked()
            if export:
                self.log_event(GENERATING_PAGES, task=task_context)
                export.status = SearchExport.STATUS.pages_working
                export.save()
                return export._generate_pages()

    def get_next_empty_page(self, batch=1) -> Optional["SearchExportPage"]:
        return self.pages.filter(data__isnull=True)[:batch]

    def do_post_pages_completion(self, task_context=None):
        with transaction.atomic():
            export = self.locked(status__lt=SearchExport.STATUS.pages_complete)
            if export:
                export.log_event(FINALIZING, task=task_context)
                if export.charge:
                    refund = export.target - min(export.progress_counter, export.target)
                    export.seat.billing.refund(refund)
                    export.charged = F("charged") - refund
                    export.refunded = F("refunded") + refund
                export.status = SearchExport.STATUS.pages_complete
                export.save()

    def do_post_validation_completion(self):
        with transaction.atomic():
            export = self.locked(status__lt=SearchExport.STATUS.validated)
            if not export:
                return
            if export.charge and export.defer_validation:
                valid = sum(1 for _ in export.get_validation_results())
                refund = export.charged - valid
                if refund > 0:
                    export.seat.billing.refund(refund)
                    export.charged = F("charged") - refund  # == valid, one would hope.
                    export.refunded = F("refunded") + refund
                export.valid_count = valid
            export.status = SearchExport.STATUS.validated
            export.save()
        if export.defer_validation:
            export.return_validation_results_to_cache()
        return True

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
            url=f"{DATAVALIDATION_URL}/list/create_from_url/",
            headers={"Authorization": f"Bearer {settings.DATAVALIDATION_KEY}"},
            data=dict(
                url=external_link(self.get_validation_url()),
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
            f"{DATAVALIDATION_URL}/list/{self.validation_list_id}/",
            headers={"Authorization": f"Bearer {settings.DATAVALIDATION_KEY}"},
        ).json()

        if status.get("status_value") == "FAILED":
            return False

        if status.get("status_percent_complete", 0) < 100:
            return False
        r = requests.head(
            f"{DATAVALIDATION_URL}/list/{self.validation_list_id}/download_result/",
            headers={"Authorization": f"Bearer {settings.DATAVALIDATION_KEY}"},
        )
        if not r.ok:
            return False
        s = CachedSession(expire_after=timedelta(days=30).total_seconds())
        r = s.get(
            f"{DATAVALIDATION_URL}/list/{self.validation_list_id}/download_result/",
            headers={"Authorization": f"Bearer {settings.DATAVALIDATION_KEY}"},
            stream=True,
        )
        return r.ok

    def get_validation_results(self, only_valid=True):
        if not self.defer_validation or self.validation_list_id == self.SKIP_CODE:
            return []

        s = CachedSession(expire_after=timedelta(days=30).total_seconds())
        r = s.get(
            f"{DATAVALIDATION_URL}/list/{self.validation_list_id}/download_result/",
            headers={"Authorization": f"Bearer {settings.DATAVALIDATION_KEY}"},
            stream=True,
        )
        r.raise_for_status()

        z = zipfile.ZipFile(StringIO(r.content))

        for name in z.namelist():
            data = StringIO(z.read(name))
            reader: Iterable[List[str]] = csv.reader(data)
            for row in reader:
                logger.debug(row)
                if len(row) != 3:
                    continue
                if only_valid and row[2][0] not in ["A", "B"]:
                    continue
                yield {"email": row[0], "profile_id": row[1], "grade": row[2]}

    def get_validation_registry(self):
        return {
            grade["email"]: grade["grade"] for grade in self.get_validation_results()
        }

    def return_validation_results_to_cache(self):
        upload_limit = 250
        results_gen = self.get_validation_results(only_valid=False)
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

    def get_mx_task_group(self):
        from whoweb.search.tasks import fetch_mx_domain

        tasks = []
        for email, web_id in self.generate_email_id_pairs():
            mxd = MXDomain.from_email(email)
            if not mxd.mx_domain:
                tasks.append(fetch_mx_domain.si(mxd.pk))
        if not tasks:
            return None
        task_group = group(tasks)
        group_task = task_group.apply_async()
        group_result = group_task.save()
        self.log_event(evt=SPAWN_MX, task=group_result)
        return group_result

    def push_to_webhooks(self, rows):
        pass

    #   TODO
    #     for hook in self.query.export.webhooks:
    #         results = []
    #         if self.query.export.is_flat:
    #             csv_rows = self.generate_csv_rows(rows)
    #             results = [
    #                 {tup[0]: tup[1] for tup in zip(self.get_column_names(), row)}
    #                 for row in csv_rows
    #             ]
    #         else:
    #             for row in rows:
    #                 contact_info = row.get("derived_contact", None)
    #                 versioned_profile = ensure_profile_matches_spec(row)
    #                 if contact_info:
    #                     versioned_derivation = ensure_contact_info_matches_spec(
    #                         contact_info, profile=None
    #                     )
    #                     versioned_profile["contact"] = versioned_derivation
    #                 results.append(versioned_profile)
    #         for row in results:
    #             requests.post(url=hook, json=row)

    def send_link(self):
        if self.sent:
            return
        if not self.notify:
            return
        with transaction.atomic():
            export = self.locked()
            if not export:
                return
            if export.sent:
                return
            email = self.seat.email
            link = external_link(self.get_absolute_url())
            json_link = link + ".json"
            subject = "Your WhoKnows Export Results"
            template = "search/download_export.html"
            html_message = render_to_string(
                template_name=template,
                context=dict(
                    link=link,
                    json_link=json_link,
                    graph_url=None,
                    tracker=None,
                    unsubscribe_link=None,
                ),
            )
            send_mail(
                subject=subject,
                html_message=html_message,
                recipient_list=[email],
                from_email=None,
                message=html_message,
            )
            self.sent = email
            self.status = self.STATUS.complete
            self.save()

    def processing_signatures(self, on_complete=None):
        from whoweb.search.tasks import (
            process_export,
            check_export_has_data,
            validate_rows,
            fetch_validation_results,
            send_notification,
            do_post_validation_completion,
            spawn_mx_group,
            header_check,
            alert_xperweb,
        )

        sigs = process_export.si(self.pk) | check_export_has_data.si(export_id=self.pk)
        if on_complete:
            sigs |= on_complete
        if self.defer_validation:
            sigs |= (
                validate_rows.si(self.pk)
                | fetch_validation_results.si(self.pk)
                | do_post_validation_completion.si(self.pk)
            )
        if self.notify:
            sigs |= send_notification.si(self.pk)
        if self.uploadable:
            sigs |= (
                spawn_mx_group.si(self.pk)
                | header_check.s()  # mutable signature to accept group_id
            )
        sigs |= alert_xperweb.si(self.pk)
        return sigs

    def get_validation_url(self):
        return reverse("search:validate_export", kwargs={"uuid": self.uuid})

    def get_named_fetch_url(self):
        return reverse(
            "search:download_export_with_named_file_ext",
            kwargs={"uuid": self.uuid, "same_uuid": self.uuid},
        )

    def get_absolute_url(self):
        return reverse("search:download_export", kwargs={"uuid": self.uuid})

    def log_event(self, evt, *, start=None, end=None, task=None, **data):
        if hasattr(task, "id"):
            data["task_id"] = task.id
        if isinstance(evt, string_types):
            code = 0
            message = evt
        else:
            code = evt[0]
            message = evt[1]
        try:
            ModelEvent.objects.create(
                ref=self, code=code, message=message, start=start, end=end, data=data
            )
        except TypeError:
            ModelEvent.objects.create(
                ref=self,
                code=code,
                message=message,
                start=start,
                end=end,
                data=str(data),
            )


class SearchExportPage(TimeStampedModel):
    export = models.ForeignKey(
        SearchExport, on_delete=models.CASCADE, related_name="pages"
    )
    data = CompressedBinaryJSONField(null=True, editable=False)
    page_num = models.PositiveIntegerField()
    working_data = JSONField(editable=False, null=True, default=dict)
    count = models.IntegerField(default=0)
    limit = models.IntegerField(null=True)
    derivation_group: TaskResult = models.ForeignKey(
        TaskResult, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        unique_together = ["export", "page_num"]
        ordering = ["export", "page_num"]

    @classmethod
    def save_profile(cls, page_pk: int, profile: "ResultProfile") -> "SearchExportPage":
        page = cls.objects.get(pk=page_pk)
        if page:
            page.working_data[profile.id] = profile.to_json()
            page.save()
        return page

    def locked(self):
        return (
            self.__class__.objects.filter(id=self.pk)
            .select_for_update(skip_locked=True, of=("self",))
            .first()
        )

    def _populate_data_directly(self):
        if self.data:
            return
        scroll = self.export.scroll
        ids = scroll.get_ids_for_page(self.page_num)
        profiles = scroll.get_profiles_for_page(self.page_num)
        if self.limit:
            self.count = min(self.limit, len(profiles))
            self.data = profiles[: self.limit]
        else:
            self.count = len(profiles)
            self.data = profiles
        self.save()
        # Sometimes search removes duplicate profiles which show up as different ids,
        # in which case we need to push the progress-based skip by the number of dupes.
        adjustment = len(ids) - len(profiles)
        self.export.progress_counter = F("progress_counter") + self.count + adjustment
        self.export.target = F("target") + adjustment
        self.export.save()

    def populate_data_directly(self):
        with transaction.atomic():
            page = self.locked()
            if page:
                return page._populate_data_directly()

    def do_page_process(self, task_context=None):
        from whoweb.search.tasks import (
            process_derivation_fast,
            process_derivation_slow,
            finalize_page,
        )

        if self.data:
            return None

        if not self.export.should_derive_email:
            self.export.log_event(
                evt=POPULATE_DATA, task=task_context, data={"page": self.page_num}
            )
            self.populate_data_directly()
            return None

        profiles = self.export.scroll.get_profiles_for_page(self.page_num)

        if self.export.defer_validation:
            process_derivation = process_derivation_fast
        else:
            process_derivation = process_derivation_slow

        args = (
            self.export.query.defer,
            self.export.should_remove_derivation_failures,
            self.export.with_invites,
            self.export.query.contact_filters or [WORK, PERSONAL, SOCIAL, PROFILE],
        )
        page_sigs = group(
            process_derivation.si(self.pk, profile.to_json(), *args)
            for profile in profiles
        ) | finalize_page.si(self.pk).on_error(finalize_page.si(self.pk))
        return page_sigs

    def _do_post_page_process(self, task_context=None) -> [dict]:
        self.export.log_event(
            evt=FINALIZE_PAGE, task=task_context, data={"page": self.page_num}
        )
        if self.data:
            return []
        profiles = self.working_data.values() if self.working_data else []
        quota = min((self.limit, len(profiles))) if self.limit else len(profiles)
        profiles = profiles[:quota]
        self.count = len(profiles)
        self.data = profiles
        self.working_data = None
        self.save()
        self.export.progress_counter = F("progress_counter") + self.count
        self.export.save()
        return profiles

    def do_post_page_process(self, task_context=None):
        with transaction.atomic():
            page = self.locked()
            if page:
                profiles = page._do_post_page_process(task_context=task_context)
        self.export.push_to_webhooks(profiles)


class MXDomain(models.Model):
    domain = models.CharField(primary_key=True, max_length=255)
    mxs = ArrayField(models.CharField(max_length=255), default=list)

    @classmethod
    def registry_for_domains(cls, domains):
        instances = cls.objects.filter(domain__in=domains)
        return {instance.domain: instance.mx_domain for instance in instances}

    @classmethod
    def from_email(cls, email="@"):
        domain = email.split("@")[1]
        if domain:
            return cls.objects.get_or_create(domain=domain)[0]

    def fetch_mx(self):
        try:
            answers = resolver.query(self.domain, "MX")
        except (resolver.NXDOMAIN, resolver.NoNameservers):
            # Bad domain.
            return
        except (resolver.NoAnswer, resolver.Timeout):
            # Bad
            return
        self.mxs = [answer.exchange.to_text() for answer in answers]
        self.save()

    @property
    def mx_domain(self):
        try:
            return self.mxs[0]
        except IndexError:
            return None
