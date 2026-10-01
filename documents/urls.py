"""Routes de l'application documents."""
from rest_framework.routers import DefaultRouter
from .views import JustificatifViewSet, ExtractionOCRViewSet, DocumentProjetViewSet, PrixReferenceViewSet, LigneFactureViewSet

router = DefaultRouter()
router.register(r"justificatifs", JustificatifViewSet, basename="justificatifs")
router.register(r"extractions-ocr", ExtractionOCRViewSet, basename="extractions-ocr")
router.register(r"documents", DocumentProjetViewSet, basename="documents")
router.register(r"prix-references", PrixReferenceViewSet, basename="prix-references")
router.register(r"lignes-factures", LigneFactureViewSet, basename="lignes-factures")

urlpatterns = router.urls
