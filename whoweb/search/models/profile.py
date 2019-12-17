import json
import re
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict

import dacite
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder

from whoweb.core.router import router
from whoweb.core.utils import PERSONAL_DOMAINS

RETRY = "retry"
COMPLETE = "complete"
VALIDATED = "validated"
FAILED = "failed"

WORK = "work"
PERSONAL = "personal"
SOCIAL = "social"
PHONE = "phone"
PROFILE = "profile"

User = get_user_model()


@dataclass
class ResultExperience:
    company_name: str = ""
    title: str = ""


@dataclass
class ResultEducation:
    school: str = ""
    degree: str = ""


@dataclass
class Skill:
    tag: str = ""


@dataclass
class GradedEmail:
    email: str = ""
    grade: str = ""
    email_type: str = ""

    def __post_init__(self):
        if not self.email_type:
            self.email_type = PERSONAL if self.is_personal else WORK

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


@dataclass
class GradedPhone:
    status: str = ""
    phone_type: str = ""
    number: str = ""

    PASSING_STATUSES = ["connected", "connected-75"]
    _status_order = {"connected": 100, "connected-75": 75}

    @property
    def status_value(self):
        return self._status_order.get(self.status, 0)

    def __lt__(self, other):
        return self.status_value < other.status_value

    def __gt__(self, other):
        return self.status_value > other.status_value


@dataclass
class GoogleCSEExtra:
    company: str = ""
    title: str = ""


@dataclass
class SocialProfile:
    url: Optional[str] = None
    typeId: Optional[str] = None


@dataclass
class DerivedContact:
    status: str
    email: Optional[str] = None
    emails: List[str] = field(default_factory=list)
    grade: Optional[str] = None
    graded_emails: List[GradedEmail] = field(default_factory=list)
    extra: Optional[GoogleCSEExtra] = None
    fc: Optional[Dict] = field(default_factory=dict)
    linkedin_url: Optional[str] = ""
    facebook: Optional[str] = ""
    twitter: Optional[str] = ""
    phone: List[str] = field(default_factory=list)
    graded_phones: Dict = field(default_factory=dict)
    phone_details: List[GradedPhone] = field(default_factory=list)
    filters: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.fc:
            return
        social_profiles = self.fc.get("socialProfiles", [])
        social_profiles_by_type = {
            social["typeId"]: social["url"]
            for social in social_profiles
            if social and social.get("typeId") and social.get("url")
        }
        if not self.linkedin_url:
            self.linkedin_url = social_profiles_by_type.get("linkedin")
        if not self.facebook:
            self.facebook = social_profiles_by_type.get("facebook")
        if not self.twitter:
            self.twitter = social_profiles_by_type.get("twitter")

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

    @classmethod
    def from_dict(self, data):
        return dacite.from_dict(DerivedContact, data=data, config=profile_load_config)


@dataclass
class ResultProfile:
    _id: Optional[str] = field(default=None)
    user_id: Optional[str] = field(default=None, repr=False)
    profile_id: Optional[str] = field(default=None, repr=False)
    primary_alias: Optional[str] = field(default=None, repr=False)
    web_profile_id: Optional[str] = field(default=None, repr=False)
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
    experience: List[ResultExperience] = field(default_factory=list)
    education_history: List[ResultEducation] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)

    email: Optional[str] = None
    emails: List[str] = field(default_factory=list)
    grade: Optional[str] = None
    graded_emails: List[GradedEmail] = field(default_factory=list)
    graded_phones: List[GradedPhone] = field(default_factory=list)
    li_url: str = ""
    facebook: str = ""
    twitter: str = ""
    invite_key: Optional[str] = None
    mx_domain: Optional[str] = field(default=None, init=False)

    derivation_requested_email: bool = False
    derivation_requested_phone: bool = False
    returned_status: str = ""

    GRADE_VALUES = {"A+": 100, "A": 90, "B+": 75, "B": 60}

    def __post_init__(self):
        #  dacite fails to create instances with InitVar types, for now,
        #  so attrs will be on self
        self._id = self._id or self.user_id or self.profile_id
        primary = self.primary_alias or self._id
        self.web_id = primary if primary.startswith("wp:") else self.web_profile_id

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
                json=dict(
                    email=email or self.email,
                    webprofile_id=self.id,
                    first_name=self.first_name,
                    last_name=self.last_name,
                )
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

    def graded_addresses(self):
        return [graded.email for graded in self.graded_emails]

    def set_derived_contact(self, derived: DerivedContact):
        self.email = derived.email
        self.emails = derived.emails
        self.graded_emails = sorted(
            derived.graded_emails,
            key=lambda g: ResultProfile.GRADE_VALUES.get(g.grade, 0),
            reverse=True,
        )
        if self.email:
            grades = {graded.email: graded.grade for graded in self.graded_emails}
            self.grade = grades.get(self.email, "")

        self.graded_phones = sorted(derived.phone_details, reverse=True)

        self.li_url = derived.linkedin_url
        self.facebook = derived.facebook
        self.twitter = derived.twitter

        if not self.company and derived.extra:
            self.company = derived.extra.company
        if not self.title and derived.extra:
            self.title = derived.extra.title

        self.derivation_requested_email = derived.requested_email
        self.derivation_requested_phone = derived.requested_email
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
            self.email, self.grade = max(
                graded, key=lambda x: ResultProfile.GRADE_VALUES.get(x[1])
            )
            # self.normalize_email_grades()
            self.set_status()
        return self

    def normalize_email_grades(self):
        if self.email and self.grade:
            graded = GradedEmail(email=self.email, grade=self.grade)
            if graded not in self.graded_emails:
                self.graded_emails.append(graded)

    def derive_contact(self, defer=(), filters=None, timeout=120, producer=None):
        if self.derivation_status == VALIDATED:
            return self.derivation_status

        if self.id.startswith("email:"):
            email = self.id.split("email:")[-1]
        elif self.web_id:
            url_args = {
                "include_social": True,
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
                derived = DerivedContact.from_dict(data=derivation)
                if not hasattr(derivation, "filters"):
                    derived.filters = filters
                self.set_derived_contact(derived)
                return self.derivation_status
        else:
            try:
                email = User.objects.get(self.id).email
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
        return bool(
            [
                phone.status in GradedPhone.PASSING_STATUSES
                for phone in self.graded_phones
            ]
        )

    def to_json(self):
        return asdict(self)

    def to_version(self, version="2019-12-05"):
        fields = {}
        if version == "2019-12-05":
            fields = {
                "profile_id": self.id,
                "relevance_score": self.relevance_score,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "company": self.company,
                "title": self.title,
                "industry": self.industry,
                "city": self.city,
                "state": self.state,
                "country": self.country,
                "email": [asdict(email) for email in self.graded_emails],
                "phone": [asdict(p) for p in self.graded_phones],
                "experience": [asdict(e) for e in self.experience],
                "education_history": [asdict(edu) for edu in self.education_history],
                "skills": [asdict(skill) for skill in self.skills],
            }
        return json.dumps(fields, cls=DjangoJSONEncoder)

    @classmethod
    def from_json(cls, data):
        return dacite.from_dict(data_class=cls, data=data, config=profile_load_config)


profile_load_config = dacite.Config(
    type_hooks={
        str: lambda s: str(s) if s else "",
        List[GradedEmail]: DerivedContact.parse_graded_emails,
    }
)
