import typing
from json import JSONEncoder

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import JSONField
from django.core import exceptions
from django.forms import SelectMultiple
from django.utils.translation import ugettext_lazy as _

from whoweb.contrib.postgres.abstract_models import AbstractEmbeddedModel
from whoweb.contrib.postgres.utils import make_mdl, serialize_model, EmbeddedJSONEncoder
from .forms import EmbeddedModelFormField


# class ModelSubterfuge:
#     def __init__(self, embedded_model):
#         self.subterfuge = embedded_model
#


class CastOnAssignDescriptor(object):
    """
    A property descriptor which ensures that `field.to_python()` is called on _every_ assignment to the field.
    This used to be provided by the `django.db.models.subclassing.Creator` class, which in turn
    was used by the deprecated-in-Django-1.10 `SubfieldBase` class, hence the reimplementation here.

    https://stackoverflow.com/a/39471064
    """

    def __init__(self, field):
        self.field = field

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):
        obj.__dict__[self.field.name] = self.field.to_python(value)


class EmbeddedArrayField(ArrayField):
    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only)
        setattr(cls, name, CastOnAssignDescriptor(self))

    def to_python(self, value):
        values = super().to_python(value)
        if isinstance(values, list):
            values = [self.base_field.to_python(val) for val in values]
        return values


class EmbeddedModelField(JSONField):
    """
    Example:
    class Blog(models.Model):
        name = models.CharField(max_length=100)
        tagline = models.TextField()
        class Meta:
            abstract = True
    class BlogForm(forms.ModelForm):
        class Meta:
            model = Blog
            fields = (
                'comment', 'author'
            )
    class Entry(models.Model):
        blog = models.EmbeddedModelField(
            model_container=Blog,
            model_form_class=BlogForm
        )
    """

    description = _(
        "Allows for the inclusion of an instance of an abstract model as a field inside a document"
    )
    default_error_messages = {
        "invalid": _("Value must be a valid instance of an abstract Model.")
    }

    def __init__(
        self,
        model_container: typing.Type[AbstractEmbeddedModel],
        encoder: typing.Optional[JSONEncoder] = EmbeddedJSONEncoder,
        **kwargs,
    ):
        super(EmbeddedModelField, self).__init__(encoder=encoder, **kwargs)
        self.model_container = model_container

    def deconstruct(self):
        name, path, args, kwargs = super(EmbeddedModelField, self).deconstruct()
        kwargs["model_container"] = self.model_container
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        """
        Overrides Django's default to_python to allow correct
        translation to instance.
        """
        if value is None or isinstance(value, self.model_container):
            return value
        value = super(EmbeddedModelField, self).to_python(value)
        if not isinstance(value, dict):
            raise ValueError(
                f"Value: {value} must be an instance of {self.model_container} or dict"
            )
        instance = make_mdl(self.model_container, value)
        return instance

    def validate(self, value, model_instance):
        if value is not None:
            if not isinstance(value, self.model_container):
                raise ValueError(
                    f"Value: {value} must be an instance of {self.model_container}"
                )
        try:
            value = serialize_model(value)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages["invalid"], code="invalid", params={"value": value}
            )
        super().validate(value, model_instance)

    def get_prep_value(self, value):
        if value is not None:
            value = self.to_python(value)
            value = serialize_model(value)
        return super().get_prep_value(value)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": EmbeddedModelFormField,
                "model_container": self.model_container,
                **kwargs,
            }
        )

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only)
        setattr(cls, name, CastOnAssignDescriptor(self))


class ChoiceArrayField(ArrayField):
    """
    A field that allows us to store an array of choices.

    Uses Django's postgres ArrayField
    and a MultipleChoiceField for its formfield.

    Usage:

        choices = ChoiceArrayField(models.CharField(max_length=...,
                                                    choices=(...,)),
                                   default=[...])
    """

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.TypedMultipleChoiceField,
            "choices": self.base_field.choices,
            "coerce": self.base_field.to_python,
            "widget": SelectMultiple,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)

    # def to_python(self, value):
    #     res = super().to_python(value)
    #     if isinstance(res, list):
    #         value = [self.base_field.to_python(val) for val in res]
    #     return value
