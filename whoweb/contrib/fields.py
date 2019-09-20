import json
import zlib

from django.db import models
from django.utils.translation import ugettext_lazy as _


class CompressedBinaryJSONField(models.BinaryField):
    description = _(
        "BinaryField that uses zlib to compress and decompress strings as JSON"
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("editable", True)
        super().__init__(*args, **kwargs)

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is not None:
            string = json.dumps(value)
            value = zlib.compress(string.encode())
        return super().get_db_prep_value(value, connection, prepared)

    def from_db_value(self, value, *args, **kwargs):
        value = super().to_python(value)
        if value is not None:
            bytestring = zlib.decompress(value, zlib.MAX_WBITS | 32)
            value = json.loads(bytestring.decode())
        return value
