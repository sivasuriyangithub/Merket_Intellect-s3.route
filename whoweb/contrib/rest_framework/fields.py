from rest_framework.fields import MultipleChoiceField


class MultipleChoiceListField(MultipleChoiceField):
    def to_representation(self, value):
        return list(super().to_representation(value))

    def to_internal_value(self, data):
        return list(super().to_internal_value(data))
