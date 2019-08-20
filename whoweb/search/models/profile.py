import re
from copy import deepcopy

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


class ResultExperience(dict):
    def __init__(self, **kwargs):
        super(ResultExperience, self).__init__(
            company_name=kwargs.get("company_name", ""), title=kwargs.get("title", "")
        )

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, item):
        return self[item]


class ResultEducation(dict):
    def __init__(self, **kwargs):
        super(ResultEducation, self).__init__(
            school=kwargs.get("school", ""), degree=kwargs.get("degree", "")
        )

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, item):
        return self[item]


class Skill(dict):
    def __init__(self, **kwargs):
        super(Skill, self).__init__(tag=kwargs.get("tag"))

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, item):
        return self[item]


class ResultProfile(object):
    grade_values = {"A+": 100, "A": 90, "B+": 75, "B": 60}

    social_link_type_names = [
        "facebook",
        "twitter",
        "angellist",
        "google",
        "googleprofile",
        "quora",
        "github",
        "bitbucket",
        "stackexchange",
        "flickr",
        "youtube",
    ]

    __slots__ = [
        "id",
        "web_id",
        "first_name",
        "last_name",
        "title",
        "country",
        "relevance_score",
        "experience",
        "education_history",
        "skills",
        "email",
        "grade",
        "emails",
        "graded_emails",
        "social_profiles",
        "social_profiles_by_type",
        "li_url",
        "phone",
        "company",
        "title",
        "industry",
        "city",
        "state",
        "passing_grade",
        "mx_domain",
        "derivation_status",
        "_invite_key",
    ]

    def __init__(self, _id=None, validation_registry=None, **kwargs):
        self.mx_domain = None
        self.email = None
        self.grade = None
        self.passing_grade = False
        self.li_url = None
        self.phone = []
        self.emails = []
        self.graded_emails = []
        self.social_profiles = []

        self.id = _id or kwargs.get("user_id", kwargs["profile_id"])
        primary_alias = kwargs.get("primary_alias", self.id)
        self.web_id = (
            primary_alias
            if primary_alias.startswith("wp:")
            else kwargs.get("web_profile_id")
        )
        self.first_name = kwargs.get("first_name", "")
        self.last_name = kwargs.get("last_name", "")
        self.title = kwargs.get("title", "")
        self.company = kwargs.get("company", "")
        self.industry = kwargs.get("industry", "")
        self.city = kwargs.get("city", "")
        self.state = kwargs.get("state", "")
        self.country = kwargs.get("country", "")
        self.relevance_score = str(kwargs.get("relevance_score", ""))
        self.experience = [
            ResultExperience(**exp) for exp in kwargs.get("experience", [])
        ]
        self.education_history = [
            ResultEducation(**edu) for edu in kwargs.get("education_history", [])
        ]
        self.skills = [Skill(**skill) for skill in kwargs.get("skills", [])]
        derivation = kwargs.get("derived_contact")
        if derivation:
            self.set_derived_contact(
                derivation=derivation, validation_registry=validation_registry
            )
        else:
            self.derivation_status = None

        self._invite_key = kwargs.get("invite_key")

    def __repr__(self):
        return "<ResultProfile {} email: {}>".format(self.id, self.email)

    @property
    def absolute_profile_url(self):
        return "{}/users/{}".format(settings.XPERWEB_ORIGIN, self.id)

    @property
    def facebook(self):
        return self.social_profiles_by_type.get("facebook")

    @property
    def twitter(self):
        return self.social_profiles_by_type.get("twitter")

    @property
    def angellist(self):
        return self.social_profiles_by_type.get("angellist")

    @property
    def google(self):
        return self.social_profiles_by_type.get(
            "google"
        ) or self.social_profiles_by_type.get("googleplus")

    @property
    def googleprofile(self):
        return self.social_profiles_by_type.get("googleprofile")

    @property
    def quora(self):
        return self.social_profiles_by_type.get("quora")

    @property
    def github(self):
        return self.social_profiles_by_type.get("github")

    @property
    def bitbucket(self):
        return self.social_profiles_by_type.get("bitbucket")

    @property
    def stackexchange(self):
        return self.social_profiles_by_type.get("stackexchange")

    @property
    def flickr(self):
        return self.social_profiles_by_type.get("flickr")

    @property
    def youtube(self):
        return self.social_profiles_by_type.get("youtube")

    @property
    def social_links(self):
        return [getattr(self, name, "") for name in self.social_link_type_names]

    def get_invite_key(self, email=None, refresh=False):
        if not (email or self.email):
            return
        if refresh or self._invite_key is None:
            self._invite_key = router.get_exportable_invite_key(
                email=email or self.email,
                webprofile_id=self.id,
                first_name=self.first_name,
                last_name=self.last_name,
            )
        return self._invite_key

    @property
    def domain(self):
        if self.email:
            return self.email.split("@")[1]

    def set_mx(self, mx_registry=None):
        if mx_registry and self.domain:
            self.mx_domain = mx_registry.get(self.domain, None)
        return self

    def experience_as_strings(self):
        return ["{}, {}".format(exp.company_name, exp.title) for exp in self.experience]

    def education_history_as_strings(self):
        return [
            "{}, {}".format(edu.school, edu.degree) for edu in self.education_history
        ]

    @property
    def skill_tags(self):
        return [skill.tag for skill in self.skills]

    def graded_addresses(self):
        return [email["email"] for email in self.graded_emails]

    def set_derived_contact(self, derivation, validation_registry=None):
        self.email = derivation.get("email")
        self.emails = derivation.get("emails", [])
        _graded_emails = derivation.get("_graded_emails")  # db_field: _graded_emails
        if _graded_emails:
            self.graded_emails = _graded_emails
            grades = {graded["email"]: graded["grade"] for graded in self.graded_emails}
        else:
            grades = derivation.get("graded_emails", {})
            try:
                self.graded_emails = [
                    {"email": k, "grade": v} for k, v in grades.items()
                ]
            except AttributeError:
                # backwards compat, where graded_emails in stored data already is formatted as list of dicts.
                self.graded_emails = deepcopy(grades)
                grades = {
                    graded["email"]: graded["grade"] for graded in self.graded_emails
                }
        if self.email:
            self.grade = grades.get(self.email, "")
        elif validation_registry:
            self.update_validation(validation_registry)

        self.passing_grade = self.grade[0] in ["A", "B"] if self.grade else False
        self.social_profiles = (
            derivation.get(
                "_social_profiles", (derivation.get("fc") or {}).get("socialProfiles")
            )
            or []
        )
        self.social_profiles_by_type = {
            social.get("typeId"): social.get("url")
            for social in self.social_profiles
            if social and (social.get("url") and social.get("typeId"))
        }

        self.li_url = derivation.get(
            "linkedin_url", self.social_profiles_by_type.get("linkedin", "")
        )
        self.phone = derivation.get("phone", [])
        extra = derivation.get("extra")
        if extra:
            self.company = extra.get("company")
            self.title = extra.get("title")

        if self.passing_grade:
            self.derivation_status = VALIDATED
        elif derivation.get("status") == RETRY:
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
                    ResultProfile.grade_values.get(validation_registry.get(g), 0)
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
            for filter in filters:
                url_args.append(("filter", filter))
            try:
                derivation = router.derive_email(params=url_args, timeout=timeout)
            except requests.Timeout:
                return RETRY
            else:
                self.set_derived_contact(derivation)
                return self.derivation_status
        else:
            try:
                user = User.objects.get(self.id)
                email = user.email
            except User.DoesNotExist:
                user = None
                email = None

        if email:
            mock_derivation = {
                "email": email,
                "grade": "A",
                "emails": [email],
                "graded_emails": {email: "A"},
            }
            self.set_derived_contact(mock_derivation)
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
            "experience": [dict(exp) for exp in self.experience],
            "education_history": [dict(edu) for edu in self.education_history],
            "skills": [dict(skill) for skill in self.skills],
            "derived_contact": {
                "email": self.email,
                "emails": self.emails,
                "grade": self.grade,
                "phone": self.phone,
                "linkedin_url": self.li_url,
                "_graded_emails": self.graded_emails,
                "_social_profiles": self.social_profiles,
            },
            "invite_key": self._invite_key,
        }
        return data

    @classmethod
    def from_json(cls, val, validation_registry=None):
        return cls(validation_registry=validation_registry, **val)
