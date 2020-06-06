from promise import Promise
from promise.dataloader import DataLoader


def genLoader(Type):
    class GenLoad(DataLoader):
        def batch_load_fn(self, keys):
            objects_by_keys = dict()
            # Here we return a promise that will result on the
            # corresponding result for each key in keys
            if hasattr(Type._meta.model, "public_id"):
                attr = "public_id"
            else:
                attr = "pk"
            lookup = {"{0}__in".format(attr): keys}
            for obj in Type._meta.model.objects.filter(**lookup):
                objects_by_keys[str(getattr(obj, attr))] = obj
            return Promise.resolve(
                [objects_by_keys.get(str(key), None) for key in keys]
            )

    return GenLoad


class Loaders(object):
    def __init__(self):
        self._generated = {}

    def _get_for_node(self, typ):
        if not typ.__name__ in self._generated:
            self._generated[typ.__name__] = genLoader(typ)()
        return self._generated[typ.__name__]

    def load(self, typ, key):
        return self._get_for_node(typ).load(key)

    def load_many(self, typ, key):
        return self._get_for_node(typ).load_many(key)
