from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.tracking.urls import public_urlpatterns as public_tracking

api_v1 = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.accounts.urls")),
    path("orgs/", include("apps.organizations.urls")),
    path("masterdata/", include("apps.masterdata.urls")),
    path("shipments/", include("apps.shipments.urls")),
    path("audit/", include("apps.audit.urls")),
    path("tracking/", include("apps.tracking.urls")),
    path("exceptions/", include("apps.exceptions.urls")),
    path("public/", include(public_tracking)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
]
