import json
import logging
from collections import Iterable, Mapping
from functools import partial

from six import string_types

_empty_list = []  # type: List

import graphql.utils.is_valid_value

from graphql import (
    GraphQLCoreBackend,
    GraphQLScalarType,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
)

logger = logging.getLogger(__name__)


class ExceptionLocatingGraphQLCoreBackend(GraphQLCoreBackend):
    """
    Log the stacktrace for exceptions during document.execute
    prior to or missed by executor such as those in initializing ExecutionContext()
    """

    def document_from_string(
        self, schema, document_string
    ):  # type: (GraphQLSchema, Union[Document, str]) -> GraphQLDocument
        graphql_document = super().document_from_string(
            schema=schema, document_string=document_string
        )

        def with_stacktrace(execute, *args, **kwargs):
            try:
                return execute(*args, **kwargs)
            except Exception as e:
                logger.debug(e, exc_info=True)
                raise

        graphql_document.execute = partial(with_stacktrace, graphql_document.execute)
        return graphql_document


# graphql.execution.values.coerce_value = patched_coerce_value

# _is_valid_value = graphql.execution.values.is_valid_value


def _is_valid_value(value, type):
    # type: (Any, Any) -> List
    """Given a type and any value, return True if that value is valid."""
    if isinstance(type, GraphQLNonNull):
        of_type = type.of_type
        if value is None:
            return [u'Expected "{}", found null.'.format(type)]

        return _is_valid_value(value, of_type)

    if value is None:
        return _empty_list

    if isinstance(type, GraphQLList):
        item_type = type.of_type
        if not isinstance(value, string_types) and isinstance(value, Iterable):
            errors = []
            for i, item in enumerate(value):
                item_errors = _is_valid_value(item, item_type)
                for error in item_errors:
                    errors.append(u"In element #{}: {}".format(i, error))

            return errors

        else:
            return _is_valid_value(value, item_type)

    if isinstance(type, GraphQLInputObjectType):
        if not isinstance(value, Mapping):
            return [u'Expected "{}", found not an object.'.format(type)]

        fields = type.fields
        errors = []

        for provided_field in sorted(value.keys()):
            if provided_field not in fields:
                errors.append(u'In field "{}": Unknown field.'.format(provided_field))

        for field_name, field in fields.items():
            subfield_errors = _is_valid_value(value.get(field_name), field.type)
            errors.extend(
                u'In field "{}": {}'.format(field_name, e) for e in subfield_errors
            )

        return errors

    assert isinstance(type, (GraphQLScalarType, GraphQLEnumType)), "Must be input type"

    # Scalar/Enum input checks to ensure the type can parse the value to
    # a non-null value.
    ###  -----------   start patch --------------
    try:
        parse_result = type.parse_value(value)  # original
    except TypeError:
        parse_result = None
    ###  -----------   end patch --------------

    if parse_result is None:
        return [u'Expected type "{}", found {}.'.format(type, json.dumps(value))]

    return _empty_list


graphql.utils.is_valid_value.is_valid_value = _is_valid_value
