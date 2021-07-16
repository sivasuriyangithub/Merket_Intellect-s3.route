from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from .fields import IdOrHyperlinkedRelatedField


class TaggableMixin(object):
    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        super().update(instance=instance, validated_data=validated_data)
        if tags is not None:
            instance.tags = tags
            instance.save()
        return instance

    def create(self, validated_data):
        tags = validated_data.pop("tags", None)
        instance = super().create(validated_data)
        if tags is not None:
            instance.tags = tags
            instance.save()
        return instance


class IdOrHyperlinkedModelSerializer(HyperlinkedModelSerializer):

    serializer_related_field = IdOrHyperlinkedRelatedField
    id_field_name = "public_id"

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """
        Create nested fields for forward and reverse relationships.
        """

        class PublicPKNestedSerializer(IdOrHyperlinkedModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = "__all__"

            def __init__(self, *args, lookup_field=None, **kwargs):
                super().__init__(*args, **kwargs)

        field_class = PublicPKNestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs
