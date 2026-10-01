"""API des demandes et alertes."""
from django.db.models import Q
from rest_framework import decorators, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from comptes.models import Utilisateur
from projets.views import projets_accessibles
from .models import Alerte, Demande
from .serializers import AlerteSerializer, DemandeSerializer


class DemandeViewSet(viewsets.ModelViewSet):
    """Gère les demandes entre bailleur et entrepreneur."""
    serializer_class = DemandeSerializer

    def get_queryset(self):
        return Demande.objects.filter(
            Q(auteur=self.request.user) | Q(destinataire=self.request.user)
        ).select_related("projet", "depense", "auteur", "destinataire")

    def perform_create(self, serializer):
        """Vérifie que le projet est accessible et que le destinataire est un acteur du projet."""
        projet = serializer.validated_data["projet"]
        destinataire = serializer.validated_data["destinataire"]
        depense = serializer.validated_data.get("depense")
        if not projets_accessibles(self.request.user).filter(pk=projet.pk).exists():
            raise PermissionDenied("Projet inaccessible.")
        acteurs = {projet.entrepreneur_id, projet.bailleur_id}
        if destinataire.id not in acteurs or destinataire.id == self.request.user.id:
            raise ValidationError({"destinataire": "Le destinataire doit être l'autre acteur du projet."})
        if depense and depense.etape.projet_id != projet.id:
            raise ValidationError({"depense": "Cette dépense n'appartient pas au projet."})
        demande = serializer.save(auteur=self.request.user)
        Alerte.objects.create(
            utilisateur=destinataire, projet=projet, type_alerte="NOUVELLE_DEMANDE",
            niveau="INFO", message=f"Nouvelle demande : {demande.message[:180]}"
        )

    @decorators.action(detail=True, methods=["post"])
    def repondre(self, request, pk=None):
        """Permet au destinataire de répondre puis clôture la demande."""
        demande = self.get_object()
        if demande.destinataire_id != request.user.id:
            raise PermissionDenied("Seul le destinataire peut répondre à cette demande.")
        reponse = str(request.data.get("reponse", "")).strip()
        if not reponse:
            raise ValidationError({"reponse": "La réponse est obligatoire."})
        demande.reponse = reponse
        demande.statut = "TRAITEE"
        demande.save(update_fields=["reponse", "statut"])
        return Response(self.get_serializer(demande).data)


class AlerteViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose les alertes personnelles et permet de les marquer comme lues."""
    serializer_class = AlerteSerializer

    def get_queryset(self):
        return Alerte.objects.filter(utilisateur=self.request.user).order_by("-date_creation")

    @decorators.action(detail=True, methods=["post"])
    def marquer_lue(self, request, pk=None):
        alerte = self.get_object()
        alerte.est_lue = True
        alerte.save(update_fields=["est_lue"])
        return Response(self.get_serializer(alerte).data)

    @decorators.action(detail=False, methods=["post"])
    def tout_marquer_lu(self, request):
        self.get_queryset().filter(est_lue=False).update(est_lue=True)
        return Response({"detail": "Toutes les alertes ont été marquées comme lues."})
