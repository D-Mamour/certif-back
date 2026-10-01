"""Routes racines de l'API Chantial."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("comptes.urls")),
    path("api/", include("comptes.api_urls")),
    path("api/", include("projets.urls")),
    path("api/", include("finances.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("intelligence.urls")),
    path("api/", include("interactions.urls")),
    path("api/", include("audit.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
