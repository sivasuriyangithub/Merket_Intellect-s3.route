import base64
import json
import zlib

from django.core.serializers.json import DjangoJSONEncoder
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
            string = json.dumps(value, cls=DjangoJSONEncoder)
            value = zlib.compress(string.encode())
        return super().get_db_prep_value(value, connection, prepared)

    def from_db_value(self, value, *args, **kwargs):
        value = super().to_python(value)
        if value is not None:
            bytestring = zlib.decompress(value, zlib.MAX_WBITS | 32)
            value = json.loads(bytestring.decode())
        return value


key = "0cd2441527430cd528448ff80a776e50b9f28c9bd5256a68c243bb552438a23b1d01c294fa5307186cd26466777248823367045953d2f7e626d3592b34c800b4"
universe = "TiX5Ch9zr2kZOK0mvFtAdebqBfyw8HaclpWxQPNY17GgMuV6nD4soRES3jIJLU"  # shuffle(string.ascii_letters + string.digits)
uni_len = len(universe)

ENCODE = "e"
DECODE = "d"
SEP = "A"


def vign(txt="", typ=DECODE, salt="A"):
    if typ == ENCODE:
        pre: str = base64.b64encode(((salt + txt) * 5).encode()).decode()[:10]
        txt = (pre + SEP + txt)[-16:]
    ret_txt = ""
    k_len = len(key)
    for i, l in enumerate(txt):
        txt_idx = universe.index(l)
        k = key[i % k_len]
        key_idx = universe.index(k)
        if typ == DECODE:
            key_idx *= -1
        code = universe[(txt_idx + key_idx) % uni_len]
        ret_txt += code

    if typ == DECODE:
        ret_txt = ret_txt.split(SEP)[-1]
    return ret_txt


class ObscuredInt(object):
    def __init__(self, prefix, id):
        self.id = id
        self.encrypted = f"{prefix}_{vign(str(id), ENCODE, prefix)}"

    @classmethod
    def parse(cls, value, prefix=None):
        if "_" in value:
            prefix, encoded_id = value.split("_")
            _id = vign(encoded_id, DECODE)
            return ObscuredInt(prefix, id=int(_id))
        return ObscuredInt(prefix, id=int(value))

    def __str__(self):
        return self.encrypted


class ObscuredAutoField(models.AutoField):
    def __init__(self, prefix, *args, **kwargs):
        self.prefix = prefix
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return value
        return ObscuredInt(self.prefix, value)

    def to_python(self, value):
        if isinstance(value, ObscuredInt):
            return value
        if value is None:
            return value
        return ObscuredInt.parse(value, self.prefix)

    def get_prep_value(self, value):
        if value is None:
            return value
        value = self.to_python(value)
        return value.id
