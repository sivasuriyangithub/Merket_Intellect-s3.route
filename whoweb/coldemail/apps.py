from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ColdemailConfig(AppConfig):
    name = "whoweb.coldemail"
    verbose_name = _("Cold Email")
