import json
import logging
from copy import deepcopy
from typing import Union, List, Optional

import requests
import six
from django.conf import settings

from . import areas
from .requestor import ColdEmailApiRequestor
from .utils import utf8

logger = logging.getLogger("coldEmail")


def convert_to_coldemail_object(
    resp: Union[dict, list, "ColdEmailObject"], api_key: Optional[str]
) -> Union["ColdEmailObject", List["ColdEmailObject"], None]:
    types = {
        "campaign": Campaign,
        "list": CampaignList,
        "message": Message,
        "record": ListRecord,
        "single_email": SingleEmail,
    }
    if isinstance(resp, list):
        return [convert_to_coldemail_object(i, api_key) for i in resp]
    elif isinstance(resp, dict) and not isinstance(resp, ColdEmailObject):
        resp = resp.copy()

        klass_name = None
        for typ in types.keys():
            if resp.get(typ):
                klass_name = typ

        if isinstance(klass_name, six.string_types):
            klass = types.get(klass_name, ColdEmailObject)
        else:
            klass = ColdEmailObject

        if klass_name in resp:
            obj_or_array: Union[dict, list] = resp[klass_name]
            if isinstance(obj_or_array, list):
                return [klass.construct_from(obj, api_key) for obj in obj_or_array]
            else:
                return klass.construct_from(obj_or_array, api_key)
        else:
            return klass.construct_from(resp, api_key)
    else:
        return resp


def _compute_diff(current, previous):
    if isinstance(current, dict):
        previous = previous or {}
        diff = current.copy()
        for key in set(previous.keys()) - set(diff.keys()):
            diff[key] = ""
        return diff
    return current if current is not None else ""


def _serialize_list(array, previous):
    array = array or []
    previous = previous or []
    params = {}

    for i, v in enumerate(array):
        previous_item = previous[i] if len(previous) > i else None
        if hasattr(v, "serialize"):
            params[str(i)] = v.serialize(previous_item)
        else:
            params[str(i)] = _compute_diff(v, previous_item)

    return params


class ColdEmailObject(dict):
    object_name = None

    def __init__(self, id=None, api_key=None, **params):
        super(ColdEmailObject, self).__init__()

        self._unsaved_values = set()
        self._transient_values = set()

        self._retrieve_params = params
        self._previous = None

        object.__setattr__(self, "api_key", api_key)

        if id:
            self["id"] = id

    def update(self, update_dict, **kwargs):
        for k in update_dict:
            self._unsaved_values.add(k)

        return super(ColdEmailObject, self).update(update_dict)

    def __setattr__(self, k, v):
        if k[0] == "_" or k in self.__dict__:
            return super(ColdEmailObject, self).__setattr__(k, v)

        self[k] = v
        return None

    def __getattr__(self, k):
        if k[0] == "_":
            raise AttributeError(k)

        try:
            return self[k]
        except KeyError as err:
            raise AttributeError(*err.args)

    def __delattr__(self, k):
        if k[0] == "_" or k in self.__dict__:
            return super(ColdEmailObject, self).__delattr__(k)
        else:
            del self[k]

    def __setitem__(self, k, v):
        if v == "":
            raise ValueError(
                "You cannot set %s to an empty string. "
                "We interpret empty strings as None in requests."
                "You may set %s.%s = None to delete the property" % (k, str(self), k)
            )

        super(ColdEmailObject, self).__setitem__(k, v)

        # Allows for unpickling in Python 3.x
        if not hasattr(self, "_unsaved_values"):
            self._unsaved_values = set()

        self._unsaved_values.add(k)

    def __getitem__(self, k):
        try:
            return super(ColdEmailObject, self).__getitem__(k)
        except KeyError as err:
            if k in self._transient_values:
                raise KeyError(
                    "%r.  HINT: The %r attribute was set in the past."
                    "It was then wiped when refreshing the object with "
                    "the result returned by the ColdEmail API, probably as a "
                    "result of a save().  The attributes currently "
                    "available on this object are: %s" % (k, k, ", ".join(self.keys()))
                )
            else:
                raise err

    def __delitem__(self, k):
        super(ColdEmailObject, self).__delitem__(k)

        # Allows for unpickling in Python 3.x
        if hasattr(self, "_unsaved_values"):
            self._unsaved_values.remove(k)

    # Custom unpickling method that uses `update` to update the dictionary
    # without calling __setitem__, which would fail if any value is an empty
    # string
    def __setstate__(self, state):
        self.update(state)

    # Custom pickling method to ensure the instance is pickled as a custom
    # class and not as a dict, otherwise __setstate__ would not be called when
    # unpickling.
    def __reduce__(self):
        reduce_value = (
            type(self),  # callable
            (self.get("id", None), self.api_key),  # args
            dict(self),  # state
        )
        return reduce_value

    @classmethod
    def construct_from(cls, values, key):
        instance = cls(values.get("id"), api_key=key)
        # if cls.object_name:
        #     values = values.get(cls.object_name, values)
        # logger.debug(values)
        instance.refresh_from(values, api_key=key)
        return instance

    def refresh_from(self, values, api_key=None, partial=False):
        self.api_key = api_key or getattr(values, "api_key", None)

        # Wipe old state before setting new. Mark those values which don't persist as transient
        if partial:
            self._unsaved_values = self._unsaved_values - set(values)
        else:
            removed = set(self.keys()) - set(values)
            self._transient_values = self._transient_values | removed
            self._unsaved_values = set()
            self.clear()

        self._transient_values = self._transient_values - set(values)

        for k, v in six.iteritems(values):
            super(ColdEmailObject, self).__setitem__(
                k, convert_to_coldemail_object(v, api_key)
            )

        self._previous = values

    def __repr__(self):
        ident_parts = [type(self).__name__]

        if isinstance(self.get("object"), six.string_types):
            ident_parts.append(self.get("object"))

        if isinstance(self.get("id"), six.string_types):
            ident_parts.append("id=%s" % (self.get("id"),))

        unicode_repr = "<%s at %s> JSON: %s" % (
            " ".join(ident_parts),
            hex(id(self)),
            str(self),
        )

        if six.PY2:
            return unicode_repr.encode("utf-8")
        else:
            return unicode_repr

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=2)

    @property
    def coldemail_id(self):
        return self.id

    def serialize(self, previous):
        params = {}
        unsaved_keys = self._unsaved_values or set()
        previous = previous or self._previous or {}

        for k, v in six.iteritems(self):
            if k == "id" or (isinstance(k, str) and k.startswith("_")):
                continue
            elif isinstance(v, APIResource):
                continue
            elif hasattr(v, "serialize"):
                params[k] = v.serialize(previous.get(k, None))
            elif k in unsaved_keys:
                params[k] = _compute_diff(v, previous.get(k, None))
            elif k == "additional_owners" and v is not None:
                params[k] = _serialize_list(v, previous.get(k, None))

        return params

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __copy__(self):
        copied = ColdEmailObject(self.get("id"), self.api_key)

        copied._retrieve_params = self._retrieve_params

        for k, v in six.iteritems(self):
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(ColdEmailObject, copied).__setitem__(k, v)

        return copied

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __deepcopy__(self, memo):
        copied = self.__copy__()
        memo[id(self)] = copied

        for k, v in six.iteritems(self):
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(ColdEmailObject, copied).__setitem__(k, deepcopy(v, memo))

        return copied


class APIResource(ColdEmailObject):
    @classmethod
    def retrieve(cls, id, api_key=None, **params):
        instance = cls(id, api_key, **params)
        instance.refresh()
        return instance

    def request(self, area: str, action: str, **params):
        if not params:
            params = self._retrieve_params

        requestor = ColdEmailApiRequestor(self.api_key)
        response, api_key = requestor.request(area, action, **params)
        return convert_to_coldemail_object(response, api_key)

    def refresh(self):
        data = self.request(
            area=self.get_area(), action=self.detail_action, **self.instance_args()
        )
        logger.debug(data)
        self.refresh_from(data)
        return self

    @classmethod
    def get_area(cls):
        if hasattr(cls, "area"):
            return cls.area
        raise NotImplementedError(
            "APIResource is an abstract class.  You should perform "
            "actions on its subclasses (e.g. Campaign, CampaignList)"
        )

    def instance_args(self):
        id = self.get("id")
        id = utf8(id)
        return {"id": id}


class CreateableResource(APIResource):
    @classmethod
    def create(cls, api_key=None, **params):
        requestor = ColdEmailApiRequestor(api_key)
        response, api_key = requestor.request(cls.area, cls.create_action, **params)
        result = convert_to_coldemail_object(response, api_key)
        return cls.construct_from(result, api_key)


class UpdateableResource(APIResource):
    def save(self):
        updated_params = self.serialize(None)

        if updated_params:
            updated_params.update(self.instance_args())
            data = self.request(
                area=self.get_area(), action=self.modify_action, **updated_params
            )
            logger.debug(data)
            self.refresh()
        else:
            logger.debug("Trying to save already saved object %r", self)
        return self


class DeleteableResource(APIResource):
    def delete(self, **kwargs):
        kwargs.update(self.instance_args())
        return self.request(area=self.area, action=self.delete_action, **kwargs)


class ListableResource(APIResource):
    @classmethod
    def list(cls, api_key=None, **params):
        requestor = ColdEmailApiRequestor(api_key)
        response, api_key = requestor.request(cls.area, cls.list_action, **params)
        coldemail_object = convert_to_coldemail_object(response, api_key)
        return coldemail_object


# API objects
class Campaign(
    CreateableResource, UpdateableResource, DeleteableResource, ListableResource
):
    area = areas.EMAIL
    object_name = "campaign"
    create_action = "createcampaign"
    detail_action = "getcampaigndetail"
    modify_action = "editcampaign"
    delete_action = "deletecampaign"
    list_action = "getcampaigns"

    def pause(self, **kwargs):
        kwargs.update(self.instance_args())
        res = self.request(self.area, "pausecampaign", limit=1000, **kwargs)
        return res and res.success

    def resume(self, **kwargs):
        kwargs.update(self.instance_args())
        res = self.request(self.area, "resumecampaign", limit=1000, **kwargs)
        return res and res.success

    def click_log(self, **kwargs):
        kwargs.update(self.instance_args())
        result = self.request(self.area, "getclicklog", limit=1000, **kwargs)
        if "log" not in result:
            result.log = []
        return result

    def open_log(self, **kwargs):
        kwargs.update(self.instance_args())
        result = self.request(self.area, "getopenlog", limit=1000, **kwargs)
        if "log" not in result:
            result.log = []
        return result


class ListRecord(ColdEmailObject):
    object_name = "record"
    GOOD_STATUSES = ["Delivered", "delivered"]

    def good_email(self):
        if self.status in self.GOOD_STATUSES:
            return self.email
        return None


class CampaignList(CreateableResource, DeleteableResource, ListableResource):
    area = areas.EMAIL

    object_name = "list"
    detail_action = "getlists"
    list_action = "getlists"
    create_action = "createlist"
    delete_action = "deletelist"

    def __init__(self, *args, **kwargs):
        super(CampaignList, self).__init__(*args, **kwargs)
        object.__setattr__(self, "records", [])

    @classmethod
    def create_by_url(cls, api_key=None, **params):
        requestor = ColdEmailApiRequestor(api_key)
        response, api_key = requestor.request(cls.area, "uploadlistbyurl", **params)
        return convert_to_coldemail_object(
            {"list": {"id": response.get("listid"), "status": response.get("status")}},
            api_key,
        )

    def _records(self, **kwargs):
        kwargs.update(self.instance_args())
        return self.request(area=self.area, action="getlistdetail", **kwargs)

    def good_log(self, refresh=False, **kwargs):
        if not self.records or refresh is True:
            self.records = self._records(filter="active", limit=100000, **kwargs)
        return convert_to_coldemail_object(
            {
                "log": [
                    {"email": row.good_email()}
                    for row in self.records
                    if row.good_email()
                ]
            },
            None,
        )


class Message(
    CreateableResource, UpdateableResource, DeleteableResource, ListableResource
):
    area = areas.EMAIL

    object_name = "message"
    create_action = "addmessage"
    detail_action = "getmessagedetail"
    modify_action = "editmessage"
    delete_action = "deletemessage"
    list_action = "getmessages"

    pass


class SingleEmail(CreateableResource):
    area = areas.EMAIL
    create_action = "sendsingleemail"
    detail_action = "getresultsendsingleemail"


class RoutesObject(object):
    base_url = "https://wkrouter.salesassistedoutreach.com/api/routes/"

    @classmethod
    def create_reply_route(
        cls, match, forwarding_address, forwarding_webhook, api_key=None
    ):
        if not api_key:
            api_key = settings.COLD_ROUTER_API_KEY

        params = dict(
            enabled=True,
            from_filter=match,
            destination=forwarding_address,
            webhook=forwarding_webhook,
        )
        r = requests.post(
            url=cls.base_url,
            data=params,
            headers={"Authorization": "Token {}".format(api_key)},
        )
        r.raise_for_status()
        return r.json()
