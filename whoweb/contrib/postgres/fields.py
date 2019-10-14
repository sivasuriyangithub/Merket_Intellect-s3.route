import typing
from django import forms
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import JSONField
from django.core import exceptions
from django.db.models import Model
from django.forms import SelectMultiple
from django.utils.translation import ugettext_lazy as _

from whoweb.contrib.postgres.utils import useful_field, make_mdl, serialize_model
from .forms import EmbeddedModelFormField


# class ModelSubterfuge:
#     def __init__(self, embedded_model):
#         self.subterfuge = embedded_model
#


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

    def __init__(self, model_container: typing.Type[Model], **kwargs):
        super(EmbeddedModelField, self).__init__(**kwargs)
        self.model_container = model_container

    def deconstruct(self):
        name, path, args, kwargs = super(EmbeddedModelField, self).deconstruct()
        kwargs["model_container"] = self.model_container
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
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
        try:
            val = self.get_db_prep_value(value)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages["invalid"], code="invalid", params={"value": value}
            )
        super().validate(val, model_instance)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if value is None and self.blank:
            return None
        if not isinstance(value, self.model_container):
            raise ValueError(
                f"Value: {value} must be an instance of {self.model_container}"
            )
        model_object = serialize_model(value, connection, prepared)
        return super(EmbeddedModelField, self).get_db_prep_value(
            model_object, connection, prepared
        )

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": EmbeddedModelFormField,
                "model_container": self.model_container,
                **kwargs,
            }
        )


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
