import json

# Create your models here.
from django.core.exceptions import FieldDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import ModelBase, Model, DEFERRED, ModelState
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.signals import pre_init, post_init

from whoweb.contrib.postgres.utils import serialize_model


class AbstractEmbeddedModel(metaclass=ModelBase):
    class Meta:
        abstract = True
        managed = False

    def __init__(self, *args, **kwargs):
        # Alias some things as locals to avoid repeat global lookups
        cls = self.__class__
        opts = self._meta
        _setattr = setattr
        _DEFERRED = DEFERRED

        pre_init.send(sender=cls, args=args, kwargs=kwargs)

        # Set up the storage for instance state
        self._state = ModelState()

        # There is a rather weird disparity here; if kwargs, it's set, then args
        # overrides it. It should be one or the other; don't duplicate the work
        # The reason for the kwargs check is that standard iterator passes in by
        # args, and instantiation for iteration is 33% faster.
        if len(args) > len(opts.concrete_fields):
            # Daft, but matches old exception sans the err msg.
            raise IndexError("Number of args exceeds number of fields")

        if not kwargs:
            fields_iter = iter(opts.concrete_fields)
            # The ordering of the zip calls matter - zip throws StopIteration
            # when an iter throws it. So if the first iter throws it, the second
            # is *not* consumed. We rely on this, so don't change the order
            # without changing the logic.
            for val, field in zip(args, fields_iter):
                if val is _DEFERRED:
                    continue
                _setattr(self, field.attname, val)
        else:
            # Slower, kwargs-ready version.
            fields_iter = iter(opts.fields)
            for val, field in zip(args, fields_iter):
                if val is _DEFERRED:
                    continue
                _setattr(self, field.attname, val)
                kwargs.pop(field.name, None)

        # Now we're left with the unprocessed fields that *must* come from
        # keywords, or default.

        for field in fields_iter:
            is_related_object = False
            # Virtual field
            if field.attname not in kwargs and field.column is None:
                continue
            if kwargs:
                if isinstance(field.remote_field, ForeignObjectRel):
                    try:
                        # Assume object instance was passed in.
                        rel_obj = kwargs.pop(field.name)
                        is_related_object = True
                    except KeyError:
                        try:
                            # Object instance wasn't passed in -- must be an ID.
                            val = kwargs.pop(field.attname)
                        except KeyError:
                            val = field.get_default()
                    else:
                        # Object instance was passed in. Special case: You can
                        # pass in "None" for related objects if it's allowed.
                        if rel_obj is None and field.null:
                            val = None
                else:
                    try:
                        val = kwargs.pop(field.attname)
                    except KeyError:
                        # This is done with an exception rather than the
                        # default argument on pop because we don't want
                        # get_default() to be evaluated, and then not used.
                        # Refs #12057.
                        val = field.get_default()
            else:
                val = field.get_default()

            if is_related_object:
                # If we are passed a related instance, set it using the
                # field.name instead of field.attname (e.g. "user" instead of
                # "user_id") so that the object gets properly cached (and type
                # checked) by the RelatedObjectDescriptor.
                if rel_obj is not _DEFERRED:
                    _setattr(self, field.name, rel_obj)
            else:
                if val is not _DEFERRED:
                    _setattr(self, field.attname, val)

        if kwargs:
            property_names = opts._property_names
            for prop in tuple(kwargs):
                try:
                    # Any remaining kwargs must correspond to properties or
                    # virtual fields.
                    if prop in property_names or opts.get_field(prop):
                        if kwargs[prop] is not _DEFERRED:
                            _setattr(self, prop, kwargs[prop])
                        del kwargs[prop]
                except (AttributeError, FieldDoesNotExist):
                    pass
            for kwarg in kwargs:
                raise TypeError(
                    "%s() got an unexpected keyword argument '%s'"
                    % (cls.__name__, kwarg)
                )
        super().__init__()
        post_init.send(sender=cls, instance=self)

    def __str__(self):
        return "%s object (%s)" % (self.__class__.__name__, "embedded")

    @property
    def pk(self):
        return hash(
            json.dumps(serialize_model(self), sort_keys=True, cls=DjangoJSONEncoder)
        )

    def serialize(self):
        return serialize_model(self)

    # Ok what's all this about?
    # In order to use a model as an "embedded" field,
    # it MUST NOT have the attribute `prepare_database_save`
    # otherwise, the field must implement remote_field,
    # which, as ugly as all this is, is even uglier and more django-magic-dependent.
    # The following lines are a way to borrow models.Model methods
    # without breaking substitution -- because it is NOT a subclass of Model.
    #
    # If you, future developer, can take advantage of the django Model boilerplate
    # while also implementing embedded field with Field.remote_field,
    # please do, and erase the following.

    from_db = Model.__dict__["from_db"]
    check = Model.__dict__["check"]
    _check_swappable = Model.__dict__["_check_swappable"]
    _check_model = Model.__dict__["_check_model"]
    _check_managers = Model.__dict__["_check_managers"]
    _check_fields = Model.__dict__["_check_fields"]
    _check_m2m_through_same_relationship = Model.__dict__[
        "_check_m2m_through_same_relationship"
    ]
    _check_id_field = Model.__dict__["_check_id_field"]
    _check_field_name_clashes = Model.__dict__["_check_field_name_clashes"]
    _check_column_name_clashes = Model.__dict__["_check_column_name_clashes"]
    _check_model_name_db_lookup_clashes = Model.__dict__[
        "_check_model_name_db_lookup_clashes"
    ]
    _check_property_name_related_field_accessor_clashes = Model.__dict__[
        "_check_property_name_related_field_accessor_clashes"
    ]
    _check_single_primary_key = Model.__dict__["_check_single_primary_key"]
    _check_index_together = Model.__dict__["_check_index_together"]
    _check_unique_together = Model.__dict__["_check_unique_together"]
    _check_indexes = Model.__dict__["_check_indexes"]
    _check_local_fields = Model.__dict__["_check_local_fields"]
    _check_ordering = Model.__dict__["_check_ordering"]
    _check_long_column_names = Model.__dict__["_check_long_column_names"]
    _check_constraints = Model.__dict__["_check_constraints"]


for method in [
    "__repr__",
    "__str__",
    "__eq__",
    "__hash__",
    "__reduce__",
    "__getstate__",
    "__setstate__",
    "get_deferred_fields",
    "refresh_from_db",
    "serializable_value",
    "_get_FIELD_display",
    "_get_next_or_previous_by_FIELD",
    "_get_next_or_previous_in_order",
    "clean",
    "validate_unique",
    "_get_unique_checks",
    "_perform_unique_checks",
    "_perform_date_checks",
    "date_error_message",
    "unique_error_message",
    "full_clean",
    "clean_fields",
]:
    setattr(AbstractEmbeddedModel, method, getattr(Model, method))
