"""Routes de l'application intelligence."""
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import AnalyseViewSet, AnomalieViewSet, RecommandationViewSet, AssistantChantialView

router = DefaultRouter()
router.register(r"analyses", AnalyseViewSet, basename="analyses")
router.register(r"anomalies", AnomalieViewSet, basename="anomalies")
router.register(r"recommandations", RecommandationViewSet, basename="recommandations")

urlpatterns = [
    path("assistant/", AssistantChantialView.as_view(), name="assistant-chantial"),
] + router.urls
