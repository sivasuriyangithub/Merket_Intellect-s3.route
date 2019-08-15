import json

from django import forms
from django.contrib.postgres.forms import JSONField
from django.utils.translation import gettext_lazy as _
from prettyjson import PrettyJSONWidget

from whoweb.contrib.postgres.utils import make_mdl, serialize_model

__all__ = ["JSONField"]


class InvalidJSONInput(str):
    pass


class JSONString(str):
    pass


class EmbeddedModelFormField(JSONField):

    default_error_messages = {
        "invalid": _(
            "'%(value)s' value must be valid JSON and convertible to the specified model."
        )
    }

    widget = PrettyJSONWidget

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

    def clean(self, value):
        return super().clean(value)

    def has_changed(self, initial, data):
        if super(JSONField, self).has_changed(initial, data):  # skip JSONField
            return True
