import json
import zlib

from django.db import models
from django.utils.translation import ugettext_lazy as _


class CompressedBinaryField(models.BinaryField):
    description = _(
        "BinaryField that uses zlib to compress and decompress automatically"
    )

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is not None:
            value = zlib.compress(json.dumps(value))
        return super(CompressedBinaryField, self).get_db_prep_value(
            value, connection, prepared
        )

    def to_python(self, value):
        value = super(CompressedBinaryField, self).to_python(value)
        if value is not None:
            value = json.loads(zlib.decompress(value, zlib.MAX_WBITS | 32))
        return value
