import calendar

from dateutil import parser

PARTNER = "p"
EXPIRY = "x"
PROFILE = "w"


def flattenDates(obj):
    for (key, val) in obj.items():
        if isinstance(val, dict):
            if val.get("$date"):
                obj[key] = val.get("$date")
            else:
                flattenDates(val)
        if isinstance(val, list):
            for v in val:
                flattenDates(v)
    return obj


def flatten_graded_emails(_, top):
    graded = top.get("graded_emails", [])
    if isinstance(graded, dict):
        return graded.keys()
    return [grade["email"] for grade in graded if grade.get("email")]


def spec(version):
    def epochparse(x, top):
        if x is None:
            return None
        try:
            return calendar.timegm(parser.parse(str(x), fuzzy=True).timetuple())
        except ValueError:
            # Could be "Present"
            return None

    if version == "2017-09-29":
        fields = {
            "profile_id": True,
            "relevance_score": True,
            "first_name": True,
            "full_name": True,
            "last_name": True,
            "company": True,
            "title": True,
            "business_function": True,
            "seniority_level": True,
            "industry": True,
            "picture_url": True,
            "city": True,
            "state": True,
            "country": True,
            "geo_loc": [True],
            "email": [True],
            "phone": [True],
            "social_links": [{"url": True, "typeName": True}],
            "current_experience": [
                {
                    "company_name": True,
                    "title": True,
                    "business_function": True,
                    "seniority_level": True,
                    "department": True,
                    "group_id": True,
                    "company_size": True,
                    "start": epochparse,
                    "end": epochparse,
                    "duration": True,
                    "description": True,
                }
            ],
            "experience": [
                {
                    "company_name": True,
                    "title": True,
                    "business_function": True,
                    "seniority_level": True,
                    "department": True,
                    "group_id": True,
                    "company_size": True,
                    "start": epochparse,
                    "end": epochparse,
                    "duration": True,
                    "description": True,
                }
            ],
            "education_history": [
                {
                    "school": True,
                    "degree": True,
                    "major": True,
                    "degree_level": True,
                    "start": epochparse,
                    "end": epochparse,
                    "summary": True,
                }
            ],
            "diversity": {
                "gender": {
                    "male": lambda x, y: round(x, 4) if x else 0,
                    "female": lambda x, y: round(x, 4) if x else 0,
                },
                "ethnic": {
                    "multiple": lambda x, y: round(x / 100, 4) if x else 0,
                    "hispanic": lambda x, y: round(x / 100, 4) if x else 0,
                    "black": lambda x, y: round(x / 100, 4) if x else 0,
                    "asian": lambda x, y: round(x / 100, 4) if x else 0,
                    "white": lambda x, y: round(x / 100, 4) if x else 0,
                    "native": lambda x, y: round(x / 100, 4) if x else 0,
                },
            },
            "total_experience": True,
            "time_at_current_company": True,
            "time_at_current_position": True,
            "skills": [{"tag": True, "level": True}],
            "attenuated_skills": [
                {"depth": True, "strength": True, "tag": True, "level": True}
            ],
        }
        return fields


def contact_info_spec(version):
    if version == "2017-09-29":
        return {
            "email": flatten_graded_emails,
            "phone": [True],
            "social_links": [{"url": True, "typeName": True}],
        }


def _extract(spec, target, topLevel=None):
    """
    :param spec: Definition of specification
    :param target: Source struct for the current block
    :param topLevel: Source struct
    :return: Populated data in the specified structure.
    :rtype: Any
    """
    if hasattr(spec, "__call__"):
        return spec(target, topLevel)
    if target is None:
        return None
    if topLevel is None:
        topLevel = target
    if spec is True:
        return target
    if type(spec) == list:
        return [
            _extract(spec[0], target_element, topLevel) for target_element in target
        ]
    if type(spec) == dict:
        sub_target = {}
        for sub_key, sub_val in spec.items():
            sub_target[sub_key] = _extract(sub_val, target.get(sub_key), topLevel)
        return sub_target
    return None


def ensure_profile_matches_spec(profile, version="2017-09-29"):
    return _extract(spec(version), profile)


def ensure_contact_info_matches_spec(derivation, profile, version="2017-09-29"):
    fc = (derivation.get("fc") or {}).get("socialProfiles") or []

    rr = (derivation.get("rr") or {}).get("links", {})

    social_profiles_by_type = {
        social.get("typeId"): social.get("url")
        for social in fc
        if social and (social.get("url") and social.get("typeId"))
    }

    social_profiles_by_type.update(rr)

    linkedin_url = derivation.get(
        "linkedin_url", social_profiles_by_type.get("linkedin", "")
    )

    derivation["social_links"] = [
        {"typeName": key, "url": value}
        for key, value in social_profiles_by_type.items()
    ]

    contact_obj = _extract(contact_info_spec(version), derivation)
    # add profile keys:
    if profile:
        contact_obj["first_name"] = profile.get("first_name")
        contact_obj["last_name"] = profile.get("last_name")
        contact_obj["company"] = profile.get("company")
        contact_obj["title"] = profile.get("title")
        contact_obj["city"] = profile.get("city")
        contact_obj["state"] = profile.get("state")
        contact_obj["country"] = profile.get("country")
        contact_obj["picture_url"] = profile.get("picture_url")

    if linkedin_url:  # add it to social links
        links = contact_obj.get("social_links") or []  # could be None
        types = {link.get("typeName", "").lower() for link in links}
        if "linkedin" not in types:
            links.append({"url": linkedin_url, "typeName": "linkedin"})
            contact_obj["social_links"] = links
    return contact_obj
