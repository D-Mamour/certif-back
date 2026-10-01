"""Routes de l'application interactions."""
from rest_framework.routers import DefaultRouter
from .views import DemandeViewSet, AlerteViewSet

router = DefaultRouter()
router.register(r"demandes", DemandeViewSet, basename="demandes")
router.register(r"alertes", AlerteViewSet, basename="alertes")

urlpatterns = router.urls
