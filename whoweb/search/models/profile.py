import re
from dataclasses import dataclass, asdict, InitVar, field
from typing import Optional, List, Dict

import dacite
import requests
from django.conf import settings
from django.contrib.auth import get_user_model

from whoweb.core.router import router

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


@dataclass
class Phone:
    phone: str = ""
    phone_type: str = ""
    status: str = ""


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
    l: Optional[Dict] = field(default_factory=dict)
    rr: Optional[Dict] = field(default_factory=dict)
    nym: Optional[Dict] = field(default_factory=dict)
    tfr: Optional[List] = field(default_factory=list)
    tiq: Optional[Dict] = field(default_factory=dict)
    fc: Optional[Dict] = field(default_factory=dict)
    p: Optional[Dict] = field(default_factory=dict)
    vn: Optional[Dict] = field(default_factory=dict)
    am: Optional[Dict] = field(default_factory=dict)
    linkedin_url: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    phone: List[str] = field(default_factory=list)
    graded_phones: Dict = field(default_factory=dict)
    phone_details: List[Phone] = field(default_factory=list)

    def __post_init__(self):
        if not self.fc:
            return
        social_profiles = self.fc.get("socialProfiles", [])
        social_profiles_by_type = {
            social.typeId: social.url
            for social in social_profiles
            if social and social.typeId and social.url
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
    validation_registry: Optional[Dict] = field(default=None, init=False)
    derived_contact: Optional[DerivedContact] = field(default=None, init=False)
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
    phone: List[Phone] = field(default_factory=list)
    li_url: str = ""
    facebook: str = ""
    twitter: str = ""
    invite_key: Optional[str] = None
    mx_domain: Optional[str] = field(default=None, init=False)

    GRADE_VALUES = {"A+": 100, "A": 90, "B+": 75, "B": 60}

    def __post_init__(self):
        #  dacite fails to create instances with InitVar types, for now,
        #  so attrs will be on self
        self._id = self._id or self.user_id or self.profile_id
        primary = self.primary_alias or self._id
        self.web_id = primary if primary.startswith("wp:") else self.web_profile_id
        if self.derived_contact:
            self.set_derived_contact(
                derivation=self.derived_contact,
                validation_registry=self.validation_registry,
            )

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
        return [graded.email for graded in self.sorted_graded_emails]

    def set_derived_contact(
        self, derivation: DerivedContact, validation_registry: Dict = None
    ):
        self.email = derivation.email
        self.emails = derivation.emails
        if self.email:
            grades = {graded.email: graded.grade for graded in self.graded_emails}
            self.grade = grades.get(self.email, "")
        elif validation_registry:
            self.update_validation(validation_registry)

        self.li_url = derivation.linkedin_url
        self.facebook = derivation.facebook
        self.twitter = derivation.twitter
        self.phone = derivation.phone_details

        if not self.company:
            self.company = derivation.extra.company
        if not self.title:
            self.title = derivation.extra.title

        if self.passing_grade:
            self.derivation_status = VALIDATED
        elif derivation.status == RETRY:
            self.derivation_status = RETRY
        elif self.email or self.emails:
            self.derivation_status = COMPLETE
        else:
            self.derivation_status = FAILED

    def update_validation(self, validation_registry):
        valid_emails = [email for email in self.emails if email in validation_registry]
        if valid_emails:
            self.email = max(
                valid_emails,
                key=lambda g: (
                    ResultProfile.GRADE_VALUES.get(validation_registry.get(g), 0)
                ),
            )
        if self.email and not self.grade:
            self.grade = validation_registry.get(self.email)

    def derive_contact(self, defer=(), filters=None, timeout=120):
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
                derivation = router.derive_email(params=url_args, timeout=timeout)
            except requests.Timeout:
                return RETRY
            else:
                derived = DerivedContact.from_dict(data=derivation)
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
    def sorted_graded_emails(self):
        return sorted(
            self.graded_emails,
            key=lambda g: ResultProfile.GRADE_VALUES.get(g.grade, 0),
            reverse=True,
        )

    @property
    def passing_grade(self):
        return self.grade[0] in ["A", "B"] if self.grade else False

    def to_json(self):
        data = {
            "_id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "company": self.company,
            "industry": self.industry,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "relevance_score": self.relevance_score,
            "experience": [asdict(exp) for exp in self.experience],
            "education_history": [asdict(edu) for edu in self.education_history],
            "skills": [asdict(skill) for skill in self.skills],
            "email": self.email,
            "emails": self.emails,
            "grade": self.grade,
            "graded_emails": self.graded_emails,
            "phone": self.phone,
            "li_url": self.li_url,
            "invite_key": self.invite_key,
        }
        return asdict(self)

    @classmethod
    def from_json(cls, data, validation_registry=None):
        if validation_registry:
            data["validation_registry"] = validation_registry
        print(data)
        return dacite.from_dict(data_class=cls, data=data, config=profile_load_config)


profile_load_config = dacite.Config(
    type_hooks={
        str: lambda s: str(s) if s else "",
        List[GradedEmail]: DerivedContact.parse_graded_emails,
    }
)
