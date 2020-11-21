import json
import re
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4

import requests
import six
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import Http404
from model_utils.models import TimeStampedModel
from pydantic import BaseModel, Extra, parse_obj_as, validator, root_validator
from rest_framework.reverse import reverse

from whoweb.payments.models import BillingAccountMember
from whoweb.core.router import router
from whoweb.core.utils import PERSONAL_DOMAINS
from whoweb.users.models import Seat

RETRY = "retry"
COMPLETE = "complete"
VALIDATED = "validated"
FAILED = "failed"

WORK = "work"
PERSONAL = "personal"
SOCIAL = "social"
PHONE = "phone"
PROFILE = "profile"
GRADE_VALUES = {"A+": 100, "A": 90, "B+": 75, "B": 60}

User = get_user_model()


class SocialTypeName(Enum):
    GOOGLE = "google"
    HI5 = "hi5"
    ANGEL = "angel"
    PINTEREST = "pinterest"
    TWITTER = "twitter"
    QUORA = "quora"
    LINKEDIN = "linkedin"
    MEETUP = "meetup"
    CRUNCHBASE = "crunchbase"
    GRAVATAR = "gravatar"
    KLOUT = "klout"
    FACEBOOK = "facebook"
    GOOGLEPLUS = "googleplus"
    ABOUTME = "aboutme"
    ANGELLIST = "angellist"

    def __str__(self):
        return self.value


class SocialLink(BaseModel):
    typeName: str
    url: str


class ResultExperience(BaseModel):
    company_name: str = ""
    title: str = ""
    description: str = ""

    @validator(
        "*", pre=True, always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        return v or ""


class ResultEducation(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    course: str = ""
    institution: str = ""

    @validator(
        "*", pre=True, always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        return v or ""


class Skill(BaseModel):
    tag: str = ""

    @validator(
        "*", pre=True, always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        return v or ""


class GenderDiversity(BaseModel):
    male: float = None
    female: float = None


class EthnicDiversity(BaseModel):
    multiple: Optional[float] = None
    hispanic: Optional[float] = None
    black: Optional[float] = None
    asian: Optional[float] = None
    white: Optional[float] = None
    native: Optional[float] = None


class Diversity(BaseModel):
    gender: Optional[GenderDiversity] = None
    ethnic: Optional[EthnicDiversity] = None


class GradedEmail(BaseModel):
    email: str = ""
    grade: str = ""
    email_type: str = ""

    @root_validator(pre=True)
    def populate_email_type(cls, vals):
        if not vals.get("email_type"):
            vals["email_type"] = (
                PERSONAL
                if vals.get("email", "").lower().split("@")[1] in PERSONAL_DOMAINS
                else WORK
            )
        return vals

    @validator(
        "*", pre=True, always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        return v or ""

    @property
    def is_passing(self):
        return bool(self.email and self.grade[0] in ["A", "B"])

    @property
    def domain(self):
        return self.email.lower().split("@")[1]

    @property
    def is_personal(self):
        return self.email_type == PERSONAL or self.domain in PERSONAL_DOMAINS

    @property
    def is_work(self):
        return self.email_type == WORK or self.domain not in PERSONAL_DOMAINS


PASSING_STATUSES = ["connected", "connected-75"]
STATUS_ORDER = {"connected": 100, "connected-75": 75}


class GradedPhone(BaseModel):
    status: str = ""
    phone_type: str = ""
    number: str = ""

    @property
    def status_value(self):
        return STATUS_ORDER.get(self.status, 0)

    @validator(
        "*", pre=True, always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        return v or ""

    def __lt__(self, other):
        return self.status_value < other.status_value

    def __gt__(self, other):
        return self.status_value > other.status_value


class GoogleCSEExtra(BaseModel):
    company: str = ""
    title: str = ""

    @validator(
        "*", pre=True, always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        return v or ""


class SocialProfile(BaseModel):
    url: Optional[str] = None
    typeId: Optional[str] = None


class DerivedContact(BaseModel):
    status: str
    email: Optional[str] = None
    emails: List[str] = []
    grade: Optional[str] = None
    graded_emails: List[GradedEmail] = []
    extra: Optional[GoogleCSEExtra] = None
    fc: Optional[Dict] = dict()
    linkedin_url: Optional[str] = ""
    facebook: Optional[str] = ""
    twitter: Optional[str] = ""
    phone: List[str] = []
    graded_phones: Dict = dict()
    phone_details: List[GradedPhone] = []
    social_links: List[SocialLink] = []
    filters: List[str] = []

    class Config:
        extra = Extra.allow

    @root_validator(pre=True)
    def set_primary_social_links(cls, values):
        social_links = parse_obj_as(List[SocialLink], values.get("social_links", []))
        social_profiles_by_type = {
            social.typeName: social.url for social in social_links
        }
        values.setdefault("linkedin_url", social_profiles_by_type.get("linkedin"))
        values.setdefault("facebook", social_profiles_by_type.get("facebook"))
        values.setdefault("twitter", social_profiles_by_type.get("twitter"))
        return values

    @validator("graded_emails", pre=True)
    def fix_graded_emails(cls, val):
        return DerivedContact.parse_graded_emails(val)

    @staticmethod
    def parse_graded_emails(potentially_unparsed_graded_emails):
        if isinstance(potentially_unparsed_graded_emails, dict):
            return [
                {"email": key, "grade": value}
                for key, value in potentially_unparsed_graded_emails.items()
            ]
        return potentially_unparsed_graded_emails

    @property
    def requested_email(self):
        return bool(set(self.filters).intersection([WORK, PERSONAL]))

    @property
    def requested_phone(self):
        return bool(set(self.filters).intersection([PHONE]))


class ResultProfile(BaseModel):
    _id: Optional[str] = None
    web_id: Optional[str] = None
    user_id: Optional[str] = None
    profile_id: Optional[str] = None
    primary_alias: Optional[str] = None
    web_profile_id: Optional[str] = None
    derivation_status: Optional[str] = None

    first_name: str = ""
    last_name: str = ""
    title: str = ""
    company: str = ""
    industry: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    relevance_score: str = ""
    experience: List[ResultExperience] = []
    education_history: List[ResultEducation] = []
    skills: List[Skill] = []
    attenuated_skills: Any = None

    geo_loc: Optional[List[float]] = None
    picture_url: str = ""
    seniority_level: str = ""
    time_at_current_company: int = None
    time_at_current_position: int = None
    total_experience: int = None
    business_function: str = ""
    diversity: Optional[Diversity] = None

    email: Optional[str] = None
    emails: List[str] = []
    grade: Optional[str] = None
    graded_emails: List[GradedEmail] = []
    graded_phones: List[GradedPhone] = []
    social_links: List[SocialLink] = []
    li_url: str = ""
    facebook: str = ""
    twitter: str = ""
    invite_key: Optional[str] = None
    mx_domain: Optional[str] = None

    derivation_requested_email: bool = False
    derivation_requested_phone: bool = False
    returned_status: str = ""

    class Config:
        extra = Extra.allow

    @root_validator(pre=True)
    def set_id_field(cls, values):
        values.setdefault(
            "_id",
            values.get("_id") or values.get("user_id") or values.get("profile_id"),
        )

        primary = values.get("primary_alias") or values["_id"]
        values.setdefault(
            "web_id",
            primary
            if primary and primary.startswith("wp:")
            else values.get("web_profile_id"),
        )
        return values

    @validator(
        "first_name",
        "last_name",
        "title",
        "company",
        "industry",
        "city",
        "state",
        "country",
        "relevance_score",
        "picture_url",
        "seniority_level",
        "business_function",
        "li_url",
        "facebook",
        "twitter",
        "returned_status",
        pre=True,
        always=True,
    )
    def set_str_none_to_emptystring(cls, v):
        """
        Search is inconsistent in returning null or empty strings.
        Data may also erroneously be a list of tags, instead of one value.

        "industry": ["health", "health care", "care"]

        """
        if isinstance(v, (list, tuple)):
            try:
                return sorted(v, key=len, reverse=True)[0]
            except IndexError:
                return ""
        return v or ""

    @root_validator(pre=True)
    def adapt_email_search_result_to_graded_format(cls, values):
        email = values.get("email")
        if isinstance(email, list) and "graded_emails" not in values:
            graded_emails = sorted(
                [
                    GradedEmail(
                        email=e.get("address", ""),
                        grade=e.get("grade", ""),
                        email_type=e.get("email_type", ""),
                    )
                    for e in email
                ],
                key=lambda g: GRADE_VALUES.get(g.grade, 0),
                reverse=True,
            )
            if graded_emails:
                values["graded_emails"] = graded_emails
                values["email"] = graded_emails[0].email
                values["grade"] = graded_emails[0].grade
        return values

    def __str__(self):
        return f"<ResultProfile {self.id} email: {self.email}>"

    @property
    def id(self):
        return self._id

    @property
    def absolute_profile_url(self):
        return f"{settings.PUBLIC_ORIGIN}/users/{self.id}"

    def get_invite_key(self, email=None, refresh=False):
        if not (email or self.email):
            return
        if refresh or self.invite_key is None:
            self.invite_key = router.make_exportable_invite_key(
                email=email or self.email,
                webprofile_id=self.id,
                first_name=self.first_name,
                last_name=self.last_name,
            )["key"]
        return self.invite_key

    @property
    def domain(self):
        if self.email:
            return self.email.split("@")[1]

    def set_mx(self, mx_registry=None):
        if mx_registry and self.domain:
            self.mx_domain = mx_registry.get(self.domain, None)
        return self

    @validator("graded_emails", pre=True)
    def parse_graded_emails(cls, val):
        return DerivedContact.parse_graded_emails(val)

    def graded_addresses(self):
        return [graded.email for graded in self.graded_emails]

    def set_derived_contact(self, derived: DerivedContact):
        self.email = derived.email
        self.emails = derived.emails
        self.graded_emails = sorted(
            derived.graded_emails,
            key=lambda g: GRADE_VALUES.get(g.grade, 0),
            reverse=True,
        )
        if self.email:
            grades = {graded.email: graded.grade for graded in self.graded_emails}
            self.grade = grades.get(self.email, "")

        self.graded_phones = sorted(derived.phone_details, reverse=True)

        self.li_url = derived.linkedin_url
        self.facebook = derived.facebook
        self.twitter = derived.twitter
        self.social_links = derived.social_links

        if not self.company and derived.extra:
            self.company = derived.extra.company
        if not self.title and derived.extra:
            self.title = derived.extra.title

        self.derivation_requested_email = derived.requested_email
        self.derivation_requested_phone = derived.requested_phone
        self.returned_status = derived.status
        # self.normalize_email_grades()
        self.set_status()
        return self

    def set_status(self):
        if (self.passing_grade and self.derivation_requested_email) or (
            self.passing_phone and self.derivation_requested_phone
        ):
            self.derivation_status = VALIDATED
        elif self.returned_status == RETRY:
            self.derivation_status = RETRY
        elif self.email or self.emails or self.graded_phones:
            self.derivation_status = COMPLETE
        else:
            self.derivation_status = FAILED

    def update_validation(self, validation_registry):
        graded = []
        for email in self.emails:
            grade = validation_registry.pop(email, None)
            if grade:
                graded.append((email, grade))

        if graded:
            self.email, self.grade = max(graded, key=lambda x: GRADE_VALUES.get(x[1]))
            # self.normalize_email_grades()
            self.set_status()
        return self

    def normalize_email_grades(self):
        if self.email and self.grade:
            graded = GradedEmail(email=self.email, grade=self.grade)
            if graded not in self.graded_emails:
                self.graded_emails.append(graded)

    def derive_contact(
        self, defer=(), filters=None, include_social=True, timeout=120, producer=None
    ):
        if self.derivation_status == VALIDATED:
            return self.derivation_status

        if self.id.startswith("email:"):
            email = self.id.split("email:")[-1]
        elif self.web_id:
            url_args = {
                "include_social": include_social,
                "is_paid": True,
                "is_domain": False,
                "first": self.clean_proper_name(self.first_name),
                "last": self.clean_proper_name(self.last_name),
                "domain": self.company.encode("utf-8") if self.company else None,
                "wp_id": self.web_id,
                "timeout": 90,
            }
            url_args = [(key, value) for key, value in url_args.items()]
            for deferred in defer:
                url_args.append(("defer", deferred))
            if not filters:
                filters = [WORK, PERSONAL, SOCIAL, PROFILE]
            for filt in filters:
                url_args.append(("filter", filt))
            try:
                derivation = router.derive_email(
                    params=url_args,
                    timeout=timeout,
                    request_producer=f"whoweb.search.export/page/{producer}"
                    if producer
                    else None,
                )
            except requests.Timeout:
                return RETRY
            else:
                derived = DerivedContact(**derivation)
                if not hasattr(derivation, "filters"):
                    derived.filters = filters
                self.set_derived_contact(derived)
                return self.derivation_status
        else:
            try:
                email = User.objects.get(username=self.id).email
            except User.DoesNotExist:
                email = None

        if email:
            self.set_derived_contact(
                DerivedContact(
                    email=email,
                    grade="A",
                    emails=[email],
                    graded_emails=[GradedEmail(email=email, grade="A")],
                    status=COMPLETE,
                )
            )
        return self.derivation_status

    @classmethod
    def derive(
        cls,
        _id=None,
        first_name=None,
        last_name=None,
        company=None,
        defer=(),
        filters=(),
        include_social=True,
        timeout=28,
    ) -> "ResultProfile":
        profile = ResultProfile(
            _id=_id, first_name=first_name, last_name=last_name, company=company
        )
        if _id and all([first_name, last_name, company]):
            pass
        elif _id and not all([first_name, last_name, company]):
            lookup_by_id = router.profile_lookup(json={"profile_id": _id})
            profiles = lookup_by_id.get("results")
            if not profiles:
                raise Http404("Unable to find a profile matching the supplied id.")
            profile = ResultProfile(**profiles[0])
        else:
            profile = profile._search_for_this()
        profile.derive_contact(
            defer=defer, filters=filters, include_social=include_social, timeout=timeout
        )
        return profile

    @classmethod
    def enrich(
        cls,
        email=None,
        linkedin_url=None,
        user_id=None,
        profile_id=None,
        update=False,
        min_confidence=None,
        get_web_profile=True,
        no_cache=None,
    ) -> "ResultProfile":

        if profile_id is None:
            profile_id = ""

        if not user_id and profile_id.startswith("user"):
            user_id = profile_id

        if not linkedin_url and "/" in profile_id:
            linkedin_url = profile_id
            if linkedin_url.endswith("/"):
                linkedin_url = linkedin_url[:-1]

        if not email and profile_id.startswith("email"):
            email = profile_id

        if not profile_id.startswith("wp:"):
            profile_id = None

        search = router.profile_lookup(
            json={
                "email": email,
                "linked_in": linkedin_url,
                "user_id": user_id,
                "profile_id": profile_id,
                "no_cache": no_cache,
                "min_confidence": min_confidence,
                "get_web_profile": get_web_profile,
                "update": update,
            },
            timeout=110,
        )
        results = search.get("results")
        if not results:
            raise Http404("Unable to find a profile matching the provided input.")
        profile_data = results[0]

        if status := profile_data.pop("status", None):
            profile_data["returned_status"] = status

        profile = ResultProfile(**profile_data)
        if email and not profile.email:
            profile.email = email
        if linkedin_url and not profile.li_url:
            profile.li_url = linkedin_url

        if "profile_id" not in profile_data:
            profile = profile._search_for_this()

        if linkedin_url and not filter(
            lambda x: x.typeName == "linkedin", profile.social_links
        ):
            profile.social_links.append(
                SocialLink(typeName="linkedin", url=linkedin_url)
            )
        return profile

    def _search_for_this(self):
        required = []
        desired = []

        if self.first_name:
            required.append(
                {"field": "first_name", "value": self.first_name, "truth": True,}
            )

        if self.last_name:
            required.append(
                {"field": "last_name", "value": self.last_name, "truth": True}
            )

        if self.company:
            required.append({"field": "company", "value": self.company, "truth": True})

        if self.title:
            desired.append({"field": "title", "value": self.title, "truth": True})

        if len(required) > 0:
            query = {
                "filters": {"required": required, "desired": desired},
                "limit": 1,
                "skip": 0,
            }
            if profiles := router.unified_search(json=query).get("results"):
                found_profile = ResultProfile(**profiles[0])
                return found_profile
        return self

    @staticmethod
    def clean_proper_name(name):
        if not name:
            return None
        clean_name = re.sub(r"\(.+?\)", "", name).split(",")[0]
        clean_name = re.sub(r"[.,/#!|$%^&*;:{}=_`~()]", "", clean_name).strip()
        for stop_word in [
            "phd",
            "mba",
            "cpa",
            "ms",
            "ma",
            "cfa",
            "md",
            "mfa",
            "msc",
            "pmp",
        ]:
            if clean_name.endswith(stop_word):
                clean_name = clean_name[: (0 - len(stop_word))]
        return clean_name.strip().encode("utf-8")

    @property
    def passing_grade(self):
        return self.grade[0] in ["A", "B"] if self.grade else False

    @property
    def passing_phone(self):
        return bool([phone.status in PASSING_STATUSES for phone in self.graded_phones])

    def to_version(self, version="2019-12-05"):
        data = {}
        if version == "2019-12-05":
            data = self.dict(
                include={
                    "first_name",
                    "last_name",
                    "company",
                    "geo_loc",
                    "total_experience",
                    "time_at_current_company",
                    "time_at_current_position",
                    "seniority_level",
                    "business_function",
                    "diversity",
                    "title",
                    "industry",
                    "city",
                    "state",
                    "country",
                    "graded_emails",
                    "graded_phones",
                    "experience",
                    "education_history",
                    "skills",
                    "social_links",
                }
            )
            data["profile_id"] = self.id or self.web_id
            data["email"] = data.pop("graded_emails", [])
            data["phone"] = data.pop("graded_phones", [])
        return json.dumps(data, cls=DjangoJSONEncoder)


#
# profile_load_config = dacite.Config(
#     type_hooks={
#         str: lambda s: str(s) if s else "",
#         List[GradedEmail]: DerivedContact.parse_graded_emails,
#     }
# )


class DerivationCache(TimeStampedModel):
    billing_seat = models.ForeignKey(BillingAccountMember, on_delete=models.CASCADE)
    profile_id = models.CharField(max_length=255)
    emails = JSONField(default=list)
    phones = JSONField(default=list)

    class Meta:
        unique_together = ("profile_id", "billing_seat")

    @classmethod
    def get_or_charge(cls, billing_seat: BillingAccountMember, profile: ResultProfile):
        graded_emails_serializable = [email.dict() for email in profile.graded_emails]
        graded_phones_serializable = [phone.dict() for phone in profile.graded_phones]
        obj, created = DerivationCache.objects.get_or_create(
            billing_seat=billing_seat,
            profile_id=profile.id,
            defaults={
                "emails": graded_emails_serializable,
                "phones": graded_phones_serializable,
            },
        )
        if created:
            charge = billing_seat.plan.compute_contact_credit_use(profile=profile)
        else:
            cached_emails = [GradedEmail(**email) for email in obj.emails]
            cached_phones = [GradedPhone(**phone) for phone in obj.phones]
            charge = billing_seat.plan.compute_additional_contact_info_credit_use(
                cached_emails=cached_emails,
                cached_phones=cached_phones,
                profile=profile,
            )
            if len(graded_emails_serializable) > len(cached_emails):
                obj.emails = graded_emails_serializable
            if len(graded_phones_serializable) > len(cached_phones):
                obj.phones = graded_phones_serializable
            obj.save()
        return obj, charge


class BatchProfileActionResult(TimeStampedModel):
    billing_seat = models.ForeignKey(BillingAccountMember, on_delete=models.CASCADE)
    id = models.UUIDField(primary_key=True, default=uuid4)
    group_task_id = models.CharField(max_length=255)
    results = JSONField()
    size = models.IntegerField(default=0)

    @property
    def status_url(self):
        return reverse("batch_result-detail", kwargs={"pk": self.id.hex})
