from copy import copy

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework_extensions.routers import ExtendedDefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from whoweb.search.urls import router as search_router
from whoweb.users.urls import router as user_router
from whoweb.campaigns.urls import router as campaign_router
from whoweb.coldemail.urls import router as coldemail_router
from whoweb.payments.urls import router as payments_router

router = ExtendedDefaultRouter()
router.root_view_name = "home"
router.registry.extend(search_router.registry)
router.registry.extend(user_router.registry)
router.registry.extend(campaign_router.registry)
router.registry.extend(coldemail_router.registry)
router.registry.extend(payments_router.registry)

urlpatterns = [
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # path("accounts/", include("allauth.urls")),
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    # Your stuff: custom urls includes go here.
    path("search/", include("whoweb.search.urls", namespace="search")),
    # path("reply/", include("whoweb.coldemail.urls", namespace="coldemail")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
urlpatterns = [path("ww/", include(urlpatterns))]
