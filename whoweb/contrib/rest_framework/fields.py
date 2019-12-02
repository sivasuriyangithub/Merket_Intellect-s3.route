from rest_framework.fields import MultipleChoiceField, iter_options, to_choices_dict


class MultipleChoiceListField(MultipleChoiceField):
    def to_representation(self, value):
        return list(super().to_representation(value))

    def to_internal_value(self, data):
        return list(super().to_internal_value(data))


class PublicPrivateMultipleChoiceListField(MultipleChoiceListField):
    def __init__(self, *args, **kwargs):
        self.public_choices = kwargs.pop("public_choices", [])
        style = kwargs.pop("style", {})
        if "base_template" not in style:
            style.setdefault("template", "contrib/restframework/select_multiple.html")
        kwargs["style"] = style
        super().__init__(*args, **kwargs)

    def public_iter_options(self):
        return iter_options(
            to_choices_dict(self.public_choices)
            if self.public_choices
            else self.grouped_choices,
            cutoff=self.html_cutoff,
            cutoff_text=self.html_cutoff_text,
        )
