from enum import Enum

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from graphql_relay import from_global_id
from rest_framework.fields import (
    MultipleChoiceField,
    iter_options,
    to_choices_dict,
    ChoiceField,
)
from rest_framework.relations import (
    HyperlinkedRelatedField,
    SlugRelatedField,
    ManyRelatedField,
)


class TagulousField(SlugRelatedField):
    def __init__(self, slug_field="name", **kwargs):
        super().__init__(slug_field=slug_field, **kwargs)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(**{self.slug_field: data})
        except ObjectDoesNotExist:
            return str(data)
        except (TypeError, ValueError):
            self.fail("invalid")

    def get_queryset(self):
        if hasattr(self, "parent") and isinstance(self.parent, ManyRelatedField):
            field = self.parent
        else:
            field = self
        return getattr(field.parent.Meta.model, field.source).tag_model.objects.all()


class EnumField(ChoiceField):
    def __init__(self, enum_class, to_choice=None, to_repr=None, **kwargs):

        assert issubclass(enum_class, Enum), f"Enum required, received {enum_class}"

        if to_repr is None:
            to_repr = lambda x: x.name
        self.to_repr = to_repr

        if to_choice is None:
            to_choice = lambda x: (x.name, x.value)
        self.to_choice = to_choice

        self.enum_class = enum_class
        kwargs["choices"] = [self.to_choice(e) for e in self.enum_class]
        kwargs.pop("max_length", None)

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            return self.enum_class[data]
        except (KeyError, ValueError):
            pass

        try:
            return self.enum_class(data)
        except (KeyError, ValueError):
            pass

        self.fail("invalid_choice", input=data)

    def to_representation(self, value):
        if not value:
            return None

        return self.to_repr(value)


class MultipleChoiceEnumField(EnumField, MultipleChoiceField):
    def to_internal_value(self, data):
        return {
            super(MultipleChoiceEnumField, self).to_internal_value(item)
            for item in data
        }

    def to_representation(self, value):
        return {
            super(MultipleChoiceEnumField, self).to_representation(item)
            for item in value
        }


class MultipleChoiceListField(MultipleChoiceField):
    def to_representation(self, value):
        return list(super().to_representation(value))

    def to_internal_value(self, data):
        return list(super().to_internal_value(data))


class PublicPrivateMultipleChoiceListField(MultipleChoiceListField):
    def __init__(self, *args, **kwargs):
        self.public_choices = kwargs.pop("public_choices", [])
        style = kwargs.pop("style", {})
        if "base_template" not in style:
            style.setdefault("template", "contrib/restframework/select_multiple.html")
        kwargs["style"] = style
        super().__init__(*args, **kwargs)

    def public_iter_options(self):
        return iter_options(
            to_choices_dict(self.public_choices)
            if self.public_choices
            else self.grouped_choices,
            cutoff=self.html_cutoff,
            cutoff_text=self.html_cutoff_text,
        )


class IdOrHyperlinkedRelatedField(HyperlinkedRelatedField):
    default_error_messages = {
        "required": _("This field is required."),
        "no_match": _("Invalid hyperlink or pk - No URL match."),
        "incorrect_match": _("Invalid hyperlink or pk - Incorrect URL match."),
        "does_not_exist": _("Invalid hyperlink or pk - Object does not exist."),
        "incorrect_type": _(
            "Incorrect type. Expected URL string or pk value, received {data_type}."
        ),
    }

    def __init__(self, **kwargs):
        self.pk_field = kwargs.pop("pk_field", None)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        # This is a poor place for this because it encourages
        # tight coupling between DRF and GraphQL,
        # instead of keeping GQL as an overlay on DRF.
        # Ideally, we'd introspect the fields in SerializerMutation.get_serializer_kwargs
        # and convert from global_id to model ID there.
        try:
            _typ, data = from_global_id(data)
        except (ValueError, UnicodeDecodeError, AttributeError):
            pass
        try:
            if self.pk_field is not None:
                non_url = self.pk_field.to_internal_value(data)
            else:
                non_url = data
            lookup_kwargs = {self.lookup_field: non_url}
            return self.get_queryset().get(**lookup_kwargs)
        except (ObjectDoesNotExist, TypeError, ValueError):
            return super().to_internal_value(data)
