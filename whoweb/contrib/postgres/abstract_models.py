import json

# Create your models here.
from django.core.exceptions import FieldDoesNotExist
from django.db.models.base import ModelBase, Model, DEFERRED, ModelState
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.signals import pre_init, post_init

from whoweb.contrib.postgres.utils import serialize_model, EmbeddedJSONEncoder


class AbstractEmbeddedModel(Model):
    class Meta:
        abstract = True
        managed = False

    def __str__(self):
        return "%s object (%s)" % (self.__class__.__name__, "embedded")

    @property
    def pk(self):
        return hash(
            json.dumps(serialize_model(self), sort_keys=True, cls=EmbeddedJSONEncoder)
        )

    def serialize(self):
        return serialize_model(self)

    # Ok what's all this about?
    # In order to use a model as an "embedded" field,
    # it MUST NOT have the attribute `prepare_database_save`
    # otherwise, the field must implement remote_field.
    # The following lines are a way to borrow models.Model methods
    # without breaking substitution -- because it is NOT a subclass of Model.
    #
    # If you, future developer, can take advantage of the django Model boilerplate
    # while also implementing embedded field with Field.remote_field,
    # please do, and erase the following.

    def __getattribute__(self, item):
        if item == "prepare_database_save":
            raise AttributeError(item)
        return super().__getattribute__(item)

    def __dir__(self):
        return sorted(
            (set(dir(self.__class__)) | set(self.__dict__.keys()))
            - {"prepare_database_save"}
        )
