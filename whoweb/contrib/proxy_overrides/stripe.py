from djstripe.fields import StripeForeignKey
from proxy_overrides.base import ProxyField


class ProxyStripeForeignKey(ProxyField):
    def __init__(self, *args, **kwargs):
        super(ProxyStripeForeignKey, self).__init__(StripeForeignKey(*args, **kwargs))
