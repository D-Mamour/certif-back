"""Routes de l'application audit."""
from rest_framework.routers import DefaultRouter
from .views import HistoriqueViewSet

router = DefaultRouter()
router.register(r"historique", HistoriqueViewSet, basename="historique")

urlpatterns = router.urls
