from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import MultipleChoiceField, iter_options, to_choices_dict
from rest_framework.relations import (
    HyperlinkedRelatedField,
    SlugRelatedField,
)


class TagulousField(SlugRelatedField):
    def __init__(self, slug_field="name", many=True, **kwargs):
        super().__init__(slug_field=slug_field, many=many, **kwargs)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(**{self.slug_field: data})
        except ObjectDoesNotExist:
            return str(data)
        except (TypeError, ValueError):
            self.fail("invalid")

    def get_queryset(self):
        return getattr(self.parent.Meta.model, self.source).tag_model.objects.all()


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
        try:
            if self.pk_field is not None:
                non_url = self.pk_field.to_internal_value(data)
            else:
                non_url = data
            lookup_kwargs = {self.lookup_field: non_url}
            return self.get_queryset().get(**lookup_kwargs)
        except (ObjectDoesNotExist, TypeError, ValueError):
            return super().to_internal_value(data)
