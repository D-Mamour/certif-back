"""API documentaire : justificatifs, OCR et documents RAG."""
from rest_framework import decorators, permissions, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from comptes.models import Utilisateur
from intelligence.services.rag import ServiceRAG
from intelligence.services.analyse import ServiceAnalyse
from projets.views import projets_accessibles
from .models import DocumentProjet, ExtractionOCR, Justificatif
from .serializers import DocumentProjetSerializer, ExtractionOCRSerializer, JustificatifSerializer
from .services.ocr import ServiceOCR


class JustificatifViewSet(viewsets.ModelViewSet):
    """Gère les justificatifs et lance automatiquement leur extraction OCR."""
    serializer_class = JustificatifSerializer
    # Le multipart est déclaré explicitement : le dépôt de fichier reste fiable
    # quel que soit le client HTTP utilisé par le frontend.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Ne retourne que les justificatifs des projets accessibles."""
        return Justificatif.objects.filter(
            depense__etape__projet__in=projets_accessibles(self.request.user)
        ).select_related("depense", "depense__etape", "depense__etape__projet")

    def perform_create(self, serializer):
        """Réserve le dépôt au propriétaire entrepreneur puis exécute l'OCR."""
        depense = serializer.validated_data["depense"]
        if (
            self.request.user.role != Utilisateur.Role.ENTREPRENEUR
            or depense.projet.entrepreneur_id != self.request.user.id
        ):
            raise PermissionDenied("Seul l'entrepreneur du projet peut déposer un justificatif.")

        justificatif = serializer.save()
        from .services.empreintes import calculer_empreintes
        try:
            calculer_empreintes(justificatif)
        except Exception:
            pass
        # L'échec OCR ne supprime jamais le justificatif : le document reste consultable.
        try:
            donnees = ServiceOCR().extraire(justificatif.fichier)
            ExtractionOCR.objects.update_or_create(justificatif=justificatif, defaults=donnees)
        except Exception as exc:
            ExtractionOCR.objects.update_or_create(
                justificatif=justificatif,
                defaults={"texte_extrait": f"OCR indisponible : {exc}"},
            )

        # Chaîne d'automatisation Chantial : le dépôt d'un justificatif déclenche
        # immédiatement les contrôles métier, l'analyse du projet, la création
        # éventuelle d'anomalies/recommandations et l'alerte destinée au bailleur.
        # Une indisponibilité du service d'intelligence ne doit jamais annuler
        # l'enregistrement du justificatif déjà reçu.
        try:
            ServiceAnalyse().analyser_projet(depense.projet)
        except Exception:
            # L'échec est volontairement isolé ici : le justificatif reste stocké
            # et une analyse pourra être relancée depuis l'interface.
            pass

    @decorators.action(detail=False, methods=["get"], url_path="etat-ocr")
    def etat_ocr(self, request):
        """Indique si le moteur Tesseract est réellement disponible sur le serveur."""
        etat = ServiceOCR.etat_moteur()
        return Response(etat, status=status.HTTP_200_OK if etat.get("disponible") else status.HTTP_503_SERVICE_UNAVAILABLE)

    @decorators.action(detail=True, methods=["post"], url_path="relancer-ocr")
    def relancer_ocr(self, request, pk=None):
        """Relance manuellement l'OCR d'un justificatif déjà déposé."""
        justificatif = self.get_object()
        try:
            donnees = ServiceOCR().extraire(justificatif.fichier)
            extraction, _ = ExtractionOCR.objects.update_or_create(
                justificatif=justificatif, defaults=donnees
            )
            return Response(ExtractionOCRSerializer(extraction).data)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ExtractionOCRViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose les résultats OCR des justificatifs accessibles."""
    serializer_class = ExtractionOCRSerializer

    def get_queryset(self):
        return ExtractionOCR.objects.filter(
            justificatif__depense__etape__projet__in=projets_accessibles(self.request.user)
        ).select_related("justificatif")


class DocumentProjetViewSet(viewsets.ModelViewSet):
    """Gère les documents utilisés comme contexte par le RAG."""
    serializer_class = DocumentProjetSerializer

    def get_queryset(self):
        return DocumentProjet.objects.filter(projet__in=projets_accessibles(self.request.user))

    def perform_create(self, serializer):
        """Réserve le dépôt documentaire à l'entrepreneur propriétaire."""
        projet = serializer.validated_data["projet"]
        if (
            self.request.user.role != Utilisateur.Role.ENTREPRENEUR
            or projet.entrepreneur_id != self.request.user.id
        ):
            raise PermissionDenied("Seul l'entrepreneur du projet peut ajouter un document.")
        serializer.save(ajoute_par=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def indexer_rag(self, request, pk=None):
        """Extrait, fragmente et vectorise un document pour le RAG."""
        document = self.get_object()
        try:
            ServiceRAG().indexer_document(document)
            return Response({"detail": "Document indexé.", "id": str(document.id)})
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

from .models import PrixReference, LigneFacture
from .serializers import PrixReferenceSerializer, LigneFactureSerializer
class PrixReferenceViewSet(viewsets.ModelViewSet):
    """Référentiel de prix provenant d'un devis validé ou d'une source marché documentée."""
    serializer_class=PrixReferenceSerializer
    def get_queryset(self):
        return PrixReference.objects.filter(projet__in=projets_accessibles(self.request.user)) | PrixReference.objects.filter(projet__isnull=True)
    def perform_create(self,serializer):
        projet=serializer.validated_data.get('projet')
        if projet and (self.request.user.role != Utilisateur.Role.ENTREPRENEUR or projet.entrepreneur_id != self.request.user.id): raise PermissionDenied('Action réservée à l’entrepreneur du projet.')
        serializer.save()
class LigneFactureViewSet(viewsets.ModelViewSet):
    serializer_class=LigneFactureSerializer
    def get_queryset(self): return LigneFacture.objects.filter(extraction__justificatif__depense__etape__projet__in=projets_accessibles(self.request.user))
