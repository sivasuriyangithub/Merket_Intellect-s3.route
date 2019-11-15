from rest_framework.fields import MultipleChoiceField


class MultipleChoiceListField(MultipleChoiceField):
    def to_representation(self, value):
        return list(super().to_representation(value))
