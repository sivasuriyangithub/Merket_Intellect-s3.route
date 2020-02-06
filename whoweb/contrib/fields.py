import base64
import hashlib
import json
import zlib

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.functional import Promise
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


class Creator(object):
    """
    A placeholder class that provides a way to set the attribute on the model.
    """

    def __init__(self, field):
        self.field = field

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):
        obj.__dict__[self.field.name] = self.field.to_python(value)


class ObscuredInt(object):

    ENCODE = "e"
    DECODE = "d"

    @classmethod
    def vign(cls, txt="", typ=DECODE, salt="A"):
        SEP = "a"
        key = "0cd2441527430cd528448ff80a776e50b9f28c9bd5256a68c243bb552438a23b1d01c294fa5307186cd26466777248823367045953d2f7e626d3592b34c800b4"
        # shuffle(string.ascii_letters + string.digits)
        universe = "TiX5Ch9zr2kZOK0mvFtAdebqBfyw8HaclpWxQPNY17GgMuV6nD4soRES3jIJLU"
        uni_len = len(universe)

        if typ == cls.ENCODE:
            md5 = hashlib.md5(txt.encode())
            pre = base64.b32encode(md5.digest()).decode().rstrip("=")
            txt = (pre + SEP + txt)[-1 * max(12, len(txt) + 1) :]
        ret_txt = ""
        k_len = len(key)
        for i, l in enumerate(txt):
            txt_idx = universe.index(l)
            k = key[i % k_len]
            key_idx = universe.index(k)
            if typ == cls.DECODE:
                key_idx *= -1
            code = universe[(txt_idx + key_idx) % uni_len]
            ret_txt += code

        if typ == cls.DECODE:
            ret_txt = ret_txt.split(SEP)[-1]
        return ret_txt

    @classmethod
    def encode(cls, value, prefix=None):
        return f"{prefix}_{cls.vign(str(value), cls.ENCODE, prefix)}"

    @classmethod
    def decode(cls, value):
        prefix, encoded_id = value.split("_")
        decoded = cls.vign(encoded_id, cls.DECODE)
        return decoded


class ObscuredAutoField(models.AutoField):
    def __init__(self, prefix, *args, **kwargs):
        self.prefix = prefix
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, Creator(self))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["prefix"] = self.prefix
        return name, path, args, kwargs

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return value
        return ObscuredInt.encode(value, self.prefix)

    def to_python(self, value):
        if isinstance(value, str) and "_" in value:
            return value
        if value is None:
            return value
        return ObscuredInt.encode(value, self.prefix)

    def get_prep_value(self, value):
        from django.db.models.expressions import OuterRef

        if isinstance(value, Promise):  # super.super
            value = value._proxy____cast()
        if value is None or isinstance(value, OuterRef):  # super
            return value
        return int(ObscuredInt.decode(value))

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)


def random_public_id():
    return get_random_string(length=16)


class ObscureIdMixin(models.Model):
    class Meta:
        abstract = True

    public_id = models.CharField(
        max_length=16,
        verbose_name="ID",
        default=random_public_id,
        editable=False,
        unique=True,
    )
