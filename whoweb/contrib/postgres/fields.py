import typing

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db.models import Model
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


class EmbeddedModelField(JSONField):
    """
    Allows for the inclusion of an instance of an abstract model as a JSON document.
    Example:
    class Blog(models.Model):
        name = models.CharField(max_length=100)
        tagline = models.TextField()
        class Meta:
            abstract = True

    class Entry(models.Model):
        blog = EmbeddedModelField(model=Blog)
        headline = models.CharField(max_length=255)
    """

    empty_strings_allowed = False

    def __init__(
        self,
        schema_model: typing.Union[Model, str],
        verbose_name: str = None,
        name: str = None,
        encoder: typing.Callable = None,
        **kwargs
    ):
        super().__init__(verbose_name, name, encoder, **kwargs)

        if isinstance(schema_model, str):
            schema_model = find_model(schema_model)
        self.schema_model = schema_model
        # self.null = True
        # self.instance = None

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["schema_model"] = self.schema_model
        return name, path, args, kwargs

    # def pre_save(self, model_instance, add):
    #     value = getattr(model_instance, self.attname)
    #     if isinstance(value, ModelSubterfuge):
    #         return value
    #
    #     subterfuge = ModelSubterfuge(value)
    #     # setattr(model_instance, self.attname, subterfuge)
    #     return subterfuge

    # def get_db_prep_value(self, value, connection=None, prepared=False):
    #     if isinstance(value, dict):
    #         return value
    #     # if isinstance(value, ModelSubterfuge):
    #     # value = value.subterfuge
    #     if value is None and self.blank:
    #         return None
    #     if not isinstance(value, Model):
    #         raise ValueError(
    #             "Value: {value} must be instance of Model: {model}".format(
    #                 value=value, model=Model
    #             )
    #         )
    #
    #     mdl_ob = {}
    #     for fld in value._meta.get_fields():
    #         if not useful_field(fld):
    #             continue
    #         fld_value = getattr(value, fld.attname)
    #         mdl_ob[fld.attname] = fld.get_db_prep_value(fld_value, connection, prepared)
    #
    #     return mdl_ob

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        """
        Overrides Django's default to_python to allow correct
        translation to instance.
        """
        if value is None or isinstance(value, self.schema_model):
            return value
        assert isinstance(value, dict)

        for field_name in value:
            field = self.schema_model._meta.get_field(field_name)
            value[field_name] = field.to_python(value[field_name])
        return self.schema_model(**value)
