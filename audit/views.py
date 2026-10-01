"""API de consultation de l'audit."""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Historique
from .serializers import HistoriqueSerializer
from .services import ServiceAudit


class HistoriqueViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose l'historique ; l'écriture passe par ``ServiceAudit``."""
    serializer_class = HistoriqueSerializer

    def get_queryset(self):
        """Limite l'historique au compte sauf pour l'administrateur."""
        utilisateur = self.request.user
        return Historique.objects.all() if utilisateur.role == "ADMINISTRATEUR" else Historique.objects.filter(utilisateur=utilisateur)

    @action(detail=False, methods=["get"], url_path="integrite")
    def integrite(self, request):
        """Vérifie la continuité de la chaîne de hachage du journal d'audit."""
        ok, rupture = ServiceAudit.verifier_integrite()
        return Response({"integre": ok, "rupture": rupture})
