import json

from django import forms
from django.contrib.postgres.forms import JSONField
from django.utils.translation import gettext_lazy as _

from whoweb.contrib.postgres.utils import make_mdl, serialize_model

__all__ = ["JSONField"]


class InvalidJSONInput(str):
    pass


class JSONString(str):
    pass


class EmbeddedModelFormField(JSONField):
    def __init__(self, model_container=None, **kwargs):
        super(EmbeddedModelFormField, self).__init__(**kwargs)
        self.model_container = model_container

    def to_python(self, value):
        val = super(EmbeddedModelFormField, self).to_python(value)
        return make_mdl(self.model_container, val)

    def prepare_value(self, value):
        if isinstance(value, self.model_container):
            value = serialize_model(value)
        return super(EmbeddedModelFormField, self).prepare_value(value)

    #
    # def has_changed(self, initial, data):
    #     if super().has_changed(initial, data):
    #         return True
    #     # For purposes of seeing whether something has changed, True isn't the
    #     # same as 1 and the order of keys doesn't matter.
    #     data = self.to_python(data)
    #     return json.dumps(initial, sort_keys=True) != json.dumps(data, sort_keys=True)
