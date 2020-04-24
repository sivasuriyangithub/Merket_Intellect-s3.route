import json
from collections import defaultdict
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.renderers import JSONOpenAPIRenderer

from whoweb.contrib.rest_framework.schemas import FutureSchemaGenerator


class TagGroupSchemaGenerator(FutureSchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=request, public=public)
        paths = schema["paths"]
        top_level_path_tags = defaultdict(set)
        for path, path_obj in paths.items():
            for operation, op_obj in path_obj.items():
                if "tags" in op_obj:
                    for tag in op_obj["tags"]:
                        tag: str = tag
                        parts = tag.split("/", maxsplit=1)
                        top_level_path_tags[parts[0]].update(op_obj["tags"])

        schema.update(
            {
                "x-tagGroups": [
                    {"name": top.title(), "tags": list(tags)}
                    for top, tags in top_level_path_tags.items()
                ]
            }
        )
        return schema


class DjangoJSONOpenAPIRenderer(JSONOpenAPIRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        return json.dumps(data, indent=2, cls=DefaultCallableJSONEncoder).encode(
            "utf-8"
        )


class DefaultCallableJSONEncoder(DjangoJSONEncoder):
    """
    JSONEncoder subclass that can handle django-field-style callable defaults.
    """

    def default(self, o):
        if callable(o):
            return o()
        return super().default(o)
