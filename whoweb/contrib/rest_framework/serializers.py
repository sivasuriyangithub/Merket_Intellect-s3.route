from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from .fields import IdOrHyperlinkedRelatedField


class IdOrHyperlinkedModelSerializer(HyperlinkedModelSerializer):

    serializer_related_field = IdOrHyperlinkedRelatedField
    id_field_name = "public_id"

    def get_default_field_names(self, declared_fields, model_info):
        """
        Return the default list of field names that will be used if the
        `Meta.fields` option is not specified.
        """
        return (
            [self.url_field_name]
            + list(declared_fields)
            + list(model_info.fields)
            + list(model_info.forward_relations)
        )

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """
        Create nested fields for forward and reverse relationships.
        """

        class NestedSerializer(IdOrHyperlinkedModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = "__all__"

        field_class = NestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs
