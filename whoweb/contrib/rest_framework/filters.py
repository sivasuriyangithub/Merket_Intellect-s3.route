from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import OrderingFilter as DefaultOrderingFilter
from rest_framework.filters import SearchFilter as DefaultSearchFilter


class OperationHolderMixin:
    def __and__(self, other):
        return OperandHolder(AND, self, other)

    def __or__(self, other):
        return OperandHolder(OR, self, other)

    def __rand__(self, other):
        return OperandHolder(AND, other, self)

    def __ror__(self, other):
        return OperandHolder(OR, other, self)

    def __invert__(self):
        raise UserWarning("Implicit queryset inversion filtering not allowed")


class OperandHolder(OperationHolderMixin):
    def __init__(self, operator_class, op1_class, op2_class):
        self.operator_class = operator_class
        self.op1_class = op1_class
        self.op2_class = op2_class

    def __call__(self, *args, **kwargs):
        op1 = self.op1_class(*args, **kwargs)
        op2 = self.op2_class(*args, **kwargs)
        return self.operator_class(op1, op2)


class AND:
    def __init__(self, op1, op2):
        self.op1 = op1
        self.op2 = op2

    def filter_queryset(self, request, queryset, view):
        return (
            self.op1.filter_queryset(request, queryset, view).filter()
            & self.op2.filter_queryset(request, queryset, view).filter()
        )

    def __repr__(self):
        return f"{self.op1} & {self.op2}"


class OR:
    def __init__(self, op1, op2):
        self.op1 = op1
        self.op2 = op2

    def filter_queryset(self, request, queryset, view):
        return (
            self.op1.filter_queryset(request, queryset, view).filter()
            | self.op2.filter_queryset(request, queryset, view).filter()
        )

    def __repr__(self):
        return f"{self.op1} | {self.op2}"


class BasePermissionMetaclass(OperationHolderMixin, type):
    pass


class BaseFilterBackend(metaclass=BasePermissionMetaclass):
    """
    A *composable* base class from which all permission backends should inherit.
    """

    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        raise NotImplementedError(".filter_queryset() must be overridden.")

    def get_schema_fields(self, view):
        assert (
            coreapi is not None
        ), "coreapi must be installed to use `get_schema_fields()`"
        assert (
            coreschema is not None
        ), "coreschema must be installed to use `get_schema_fields()`"
        return []

    def get_schema_operation_parameters(self, view):
        return []


class SearchFilter(DefaultSearchFilter, metaclass=BasePermissionMetaclass):
    pass


class OrderingFilter(DefaultOrderingFilter, metaclass=BasePermissionMetaclass):
    pass


class ObjectPermissionsFilter(BaseFilterBackend):
    """
    A filter backend that limits results to those where the requesting user
    has read object level permissions.
    """

    perm_format = "%(app_label)s.view_%(model_name)s"
    shortcut_kwargs = {
        "accept_global_perms": False,
    }

    def filter_queryset(self, request, queryset, view):
        # We want to defer this import until runtime, rather than import-time.
        # See https://github.com/encode/django-rest-framework/issues/4608
        # (Also see #1624 for why we need to make this import explicitly)
        from guardian.shortcuts import get_objects_for_user

        user = request.user
        permission = self.perm_format % {
            "app_label": queryset.model._meta.app_label,
            "model_name": queryset.model._meta.model_name,
        }

        return get_objects_for_user(user, permission, queryset, **self.shortcut_kwargs)
