from django.utils.text import camel_case_to_spaces
from rest_framework import serializers
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.schemas.utils import is_list_view


class VerboseAutoSchema(AutoSchema):

    method_mapping = {
        "get": "Retrieve",
        "post": "Create",
        "put": "Replace",
        "patch": "Update",
        "partial_update": "Update",
        "delete": "Destroy",
    }

    def __init__(self, tags=None):
        """
        :param operation_id_base: user-defined name in operationId. If empty, it will be deducted from the Model/Serializer/View name.
        :param component_name: user-defined component's name. If empty, it will be deducted from the Serializer's class name.
        """
        if tags and not all(isinstance(tag, str) for tag in tags):
            raise ValueError("tags must be a list or tuple of string.")
        self._tags = tags
        super().__init__()

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation["summary"] = self.get_summary(path, method)
        operation["tags"] = self.get_tags(path, method)
        return operation

    def get_summary(self, path, method):
        method_name = getattr(self.view, "action", method.lower())
        action_name = getattr(self.view, "name", None)
        if method_name not in self.method_mapping and action_name:
            return action_name.title()
        else:
            opid = self._get_operation_id(path, method)
            return camel_case_to_spaces(opid).title()

    def get_tags(self, path, method):
        # If user have specified tags, use them.
        if self._tags:
            return self._tags

        # First element of a specific path could be valid tag. This is a fallback solution.
        # PUT, PATCH, GET(Retrieve), DELETE:        /user_profile/{id}/       tags = [user-profile]
        # POST, GET(List):                          /user_profile/            tags = [user-profile]
        if path.startswith("/ww/api/"):
            path = path[8:]

        return [path.split("{")[0].replace("_", "-")]

    def _get_request_serializer(self, path, method):
        view = self.view

        if not hasattr(view, "request_serializer_class"):
            return self._get_serializer(path, method)
        serializer_class = view.request_serializer_class
        if serializer_class and issubclass(serializer_class, serializers.Serializer):
            return serializer_class(context=view.get_serializer_context())

    def _get_response_serializer(self, path, method):
        view = self.view

        if not hasattr(view, "response_serializer_class"):
            return self._get_serializer(path, method)
        serializer_class = view.response_serializer_class
        if serializer_class and issubclass(serializer_class, serializers.Serializer):
            return serializer_class(context=view.get_serializer_context())

    def _get_request_body(self, path, method):
        if method not in ("PUT", "PATCH", "POST"):
            return {}

        self.request_media_types = self.map_parsers(path, method)

        serializer = self._get_request_serializer(path, method)

        if not isinstance(serializer, serializers.Serializer):
            return {}

        content = self._map_serializer(serializer)
        # No required fields for PATCH
        if method == "PATCH":
            content.pop("required", None)
        # No read_only fields for request.
        for name, schema in content["properties"].copy().items():
            if "readOnly" in schema:
                del content["properties"][name]

        return {"content": {ct: {"schema": content} for ct in self.request_media_types}}

    def _get_responses(self, path, method):
        # TODO: Handle multiple codes and pagination classes.
        if method == "DELETE":
            return {"204": {"description": ""}}

        self.response_media_types = self.map_renderers(path, method)

        item_schema = {}
        serializer = self._get_response_serializer(path, method)

        if isinstance(serializer, serializers.Serializer):
            item_schema = self._map_serializer(serializer)
            # No write_only fields for response.
            for name, schema in item_schema["properties"].copy().items():
                if "writeOnly" in schema:
                    del item_schema["properties"][name]
                    if "required" in item_schema:
                        item_schema["required"] = [
                            f for f in item_schema["required"] if f != name
                        ]

        if is_list_view(path, method, self.view):
            response_schema = {
                "type": "array",
                "items": item_schema,
            }
            paginator = self._get_paginator()
            if paginator:
                response_schema = paginator.get_paginated_response_schema(
                    response_schema
                )
        else:
            response_schema = item_schema

        return {
            "200": {
                "content": {
                    ct: {"schema": response_schema} for ct in self.response_media_types
                },
                # description is a mandatory property,
                # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#responseObject
                # TODO: put something meaningful into it
                "description": "",
            }
        }
