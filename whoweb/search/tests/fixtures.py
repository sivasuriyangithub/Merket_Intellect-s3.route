# coding=utf-8

import json

import pytest
from bson.json_util import object_hook

from whoweb.search.models import ResultProfile
from .json_data import PENDING, DONE

done = json.loads(DONE, object_hook=object_hook, strict=False)
pending = json.loads(PENDING, object_hook=object_hook, strict=False)


@pytest.fixture(scope="session")
def raw_derived():
    return done


@pytest.fixture(scope="session")
def search_results():
    return pending


@pytest.fixture
def search_result_profiles(search_results):
    return [ResultProfile(**prof) for prof in search_results]


@pytest.fixture
def result_profile_derived():
    return ResultProfile(**done[0])


@pytest.fixture
def result_profile_derived_another():
    return ResultProfile(**done[1])


@pytest.fixture
def query_no_contact():
    return {
        "defer": ["degree_levels", "company_counts", "contact"],
        "user_id": "512cce8c7cc2133a2be3543d",
        "filters": {
            "desired": [
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO"],
                    "truth": True,
                }
            ],
            "required": [
                {
                    "field": "near",
                    "value": [{"locale": "United States", "miles": "1"}],
                    "truth": True,
                },
                {
                    "field": "keyword",
                    "value": [
                        "Fundraising",
                        "Philanthropy",
                        "Development",
                        "Annual Fund",
                        "Direct Marketing",
                        "Direct Response",
                        "Digital Marketing",
                        "Advancement",
                        "Donor",
                        "Donors",
                        "Donor Relations",
                    ],
                    "truth": True,
                },
                {
                    "field": "industry",
                    "value": [
                        "Nonprofit Organization Management",
                        "Religious Institutions",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": [
                        "Development",
                        "Annual Fund",
                        "Philanthropy",
                        "Marketing",
                        "Fundraising",
                        "Advancement",
                        "Prospect Research",
                        "Communications",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": ["retired", "former"],
                    "truth": False,
                },
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO", "VP", "Director"],
                    "truth": True,
                },
            ],
            "limit": 5000,
            "skip": 0,
        },
    }


@pytest.fixture
def query_specified_profiles_in_filters():
    return {
        "defer": ["degree_levels", "company_counts"],
        "user_id": "512cce8c7cc2133a2be3543d",
        "with_invites": True,
        "filters": {
            "required": [
                {
                    "field": "_id",
                    "value": [
                        "wp:1",
                        "wp:2",
                        "wp:3",
                        "wp:4",
                        "wp:5",
                        "wp:6",
                        "wp:11",
                        "wp:12",
                        "wp:13",
                        "wp:14",
                        "wp:15",
                        "wp:16",
                    ],
                    "truth": True,
                },
                {"field": "_id", "value": ["wp:1"], "truth": False},
            ],
            "limit": 20,
            "skip": 0,
        },
    }


@pytest.fixture
def query_contact_invites():
    return {
        "defer": ["degree_levels", "company_counts"],
        "user_id": "512cce8c7cc2133a2be3543d",
        "with_invites": True,
        "filters": {
            "desired": [
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO"],
                    "truth": True,
                }
            ],
            "required": [
                {
                    "field": "near",
                    "value": [{"locale": "United States", "miles": "1"}],
                    "truth": True,
                },
                {
                    "field": "keyword",
                    "value": [
                        "Fundraising",
                        "Philanthropy",
                        "Development",
                        "Annual Fund",
                        "Direct Marketing",
                        "Direct Response",
                        "Digital Marketing",
                        "Advancement",
                        "Donor",
                        "Donors",
                        "Donor Relations",
                    ],
                    "truth": True,
                },
                {
                    "field": "industry",
                    "value": [
                        "Nonprofit Organization Management",
                        "Religious Institutions",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": [
                        "Development",
                        "Annual Fund",
                        "Philanthropy",
                        "Marketing",
                        "Fundraising",
                        "Advancement",
                        "Prospect Research",
                        "Communications",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": ["retired", "former"],
                    "truth": False,
                },
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO", "VP", "Director"],
                    "truth": True,
                },
            ],
            "limit": 5000,
            "skip": 0,
        },
    }


@pytest.fixture
def query_contact_no_invites():
    return {
        "defer": ["degree_levels", "company_counts"],
        "user_id": "512cce8c7cc2133a2be3543d",
        "filters": {
            "desired": [
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO"],
                    "truth": True,
                }
            ],
            "required": [
                {
                    "field": "near",
                    "value": [{"locale": "United States", "miles": "1"}],
                    "truth": True,
                },
                {
                    "field": "keyword",
                    "value": [
                        "Fundraising",
                        "Philanthropy",
                        "Development",
                        "Annual Fund",
                        "Direct Marketing",
                        "Direct Response",
                        "Digital Marketing",
                        "Advancement",
                        "Donor",
                        "Donors",
                        "Donor Relations",
                    ],
                    "truth": True,
                },
                {
                    "field": "industry",
                    "value": [
                        "Nonprofit Organization Management",
                        "Religious Institutions",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": [
                        "Development",
                        "Annual Fund",
                        "Philanthropy",
                        "Marketing",
                        "Fundraising",
                        "Advancement",
                        "Prospect Research",
                        "Communications",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": ["retired", "former"],
                    "truth": False,
                },
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO", "VP", "Director"],
                    "truth": True,
                },
            ],
            "limit": 5000,
            "skip": 0,
        },
    }


@pytest.fixture
def query_contact_invites_defer_validation():
    return {
        "defer": ["degree_levels", "company_counts", "validation"],
        "user_id": "512cce8c7cc2133a2be3543d",
        "with_invites": True,
        "filters": {
            "desired": [
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO"],
                    "truth": True,
                }
            ],
            "required": [
                {
                    "field": "near",
                    "value": [{"locale": "United States", "miles": "1"}],
                    "truth": True,
                },
                {
                    "field": "keyword",
                    "value": [
                        "Fundraising",
                        "Philanthropy",
                        "Development",
                        "Annual Fund",
                        "Direct Marketing",
                        "Direct Response",
                        "Digital Marketing",
                        "Advancement",
                        "Donor",
                        "Donors",
                        "Donor Relations",
                    ],
                    "truth": True,
                },
                {
                    "field": "industry",
                    "value": [
                        "Nonprofit Organization Management",
                        "Religious Institutions",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": [
                        "Development",
                        "Annual Fund",
                        "Philanthropy",
                        "Marketing",
                        "Fundraising",
                        "Advancement",
                        "Prospect Research",
                        "Communications",
                    ],
                    "truth": True,
                },
                {
                    "field": "current_experience.title",
                    "value": ["retired", "former"],
                    "truth": False,
                },
                {
                    "field": "current_experience.seniority_level",
                    "value": ["CXO", "VP", "Director"],
                    "truth": True,
                },
            ],
            "limit": 5000,
            "skip": 0,
        },
    }


@pytest.fixture
def user_facing_column_headers():
    return [
        "Profile ID",
        "First Name",
        "Last Name",
        "Title",
        "Company",
        "Industry",
        "City",
        "State",
        "Country",
        "Email",
        "Email Type",
        "Email Grade",
        "Email 2",
        "Email 2 Type",
        "Email 2 Grade",
        "Email 3",
        "Email 3 Type",
        "Email 3 Grade",
        "Phone Number",
        "Phone Number Type",
        "Phone Number 2",
        "Phone Number 2 Type",
        "Phone Number 3",
        "Phone Number 3 Type",
        "WhoKnows URL",
        "LinkedIn URL",
        "Facebook",
        "Twitter",
    ]


@pytest.fixture
def all_uploadable_column_headers():
    return [
        "invitekey",
        "profile_id",
        "first_name",
        "last_name",
        "title",
        "company",
        "industry",
        "city",
        "state",
        "country",
        "email",
        "email_type",
        "email_grade",
        "email_2",
        "email_2_type",
        "email_2_grade",
        "email_3",
        "email_3_type",
        "email_3_grade",
        "phone_number",
        "phone_number_type",
        "phone_number_2",
        "phone_number_2_type",
        "phone_number_3",
        "phone_number_3_type",
        "whoknows_url",
        "linkedin_url",
        "facebook",
        "twitter",
        "domain",
        "mxdomain",
    ]
