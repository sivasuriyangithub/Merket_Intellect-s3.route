from functools import partial

from django import forms
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import AutoField, BigAutoField
from django.forms import modelform_factory
from factory.django import get_model


def find_model(model_name):
    try:
        return get_model(model_name, None)
    except ValueError:
        for app_config in apps.get_apps_configs():
            try:
                return app_config.get_model(model_name)
            except LookupError:
                continue

    ct = ContentType.objects.get(model=model_name)
    return ct.model_class()


def useful_field(field):
    return field.concrete and not isinstance(field, (AutoField, BigAutoField))


def make_mdl(model, model_dict):
    """
    Builds an instance of model from the model_dict.
    """
    for field_name in model_dict:
        field = model._meta.get_field(field_name)
        model_dict[field_name] = field.to_python(model_dict[field_name])
    return model(**model_dict)


def serialize_model(instance, connection=None, prepared=None):
    model_obj = {}
    for fld in instance._meta.get_fields():
        if not useful_field(fld):
            continue
        fld_value = getattr(instance, fld.attname)
        model_obj[fld.attname] = fld.get_db_prep_value(fld_value, connection, prepared)
    return model_obj


def _get_model_form_class(model_form_class, model_container, admin, request):
    if not model_form_class:
        form_kwargs = dict(form=forms.ModelForm, fields=forms.ALL_FIELDS)

        if admin and request:
            form_kwargs["formfield_callback"] = partial(
                admin.formfield_for_dbfield, request=request
            )

        model_form_class = modelform_factory(model_container, **form_kwargs)

    return model_form_class
