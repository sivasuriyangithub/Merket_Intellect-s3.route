from graphql_relay import to_global_id
from rest_framework import serializers


class NodeRelatedField(serializers.RelatedField):
    """
    A read only field that represents its targets using their
    plain string representation.
    """

    def __init__(self, node: str, **kwargs):
        kwargs["read_only"] = True
        self.node = node
        super().__init__(**kwargs)

    def to_representation(self, value):
        return to_global_id(self.node, value)
