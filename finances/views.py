"""API financière."""
from rest_framework import viewsets,decorators
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from comptes.models import Utilisateur
from audit.services import ServiceAudit
from interactions.models import Alerte
from .models import Depense
from .serializers import DepenseSerializer

class DepenseViewSet(viewsets.ModelViewSet):
    """CRUD et validation des dépenses."""
    serializer_class=DepenseSerializer
    def get_queryset(self):
        """Isole les dépenses selon le rôle."""
        u=self.request.user
        if u.role==Utilisateur.Role.ENTREPRENEUR:
            return Depense.objects.filter(etape__projet__entrepreneur=u)
        if u.role==Utilisateur.Role.BAILLEUR:
            return Depense.objects.filter(etape__projet__bailleur=u)
        return Depense.objects.all()

    def perform_create(self,serializer):
        """Crée une dépense uniquement pour une étape appartenant à l'entrepreneur connecté."""
        etape = serializer.validated_data.get("etape")
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or etape.projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        serializer.save(auteur=self.request.user)

    def perform_update(self, serializer):
        depense = self.get_object()
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or depense.projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        serializer.save(auteur=depense.auteur)

    def perform_destroy(self, instance):
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or instance.projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        instance.delete()

    @decorators.action(detail=True,methods=["post"])
    def valider(self,request,pk=None):
        """Valide une dépense uniquement si l'utilisateur est son bailleur."""
        d=self.get_object()
        if request.user!=d.projet.bailleur:
            return Response({"detail":"Action réservée au bailleur du projet."},status=403)
        d.statut=Depense.Statut.VALIDEE; d.save(update_fields=["statut"])
        ServiceAudit.enregistrer("VALIDATION_DEPENSE",request.user,d.projet)
        Alerte.objects.create(utilisateur=d.auteur, projet=d.projet, type_alerte="DEPENSE_VALIDEE", niveau="INFO", message=f"La dépense « {d.libelle} » a été validée.")
        return Response(self.get_serializer(d).data)

    @decorators.action(detail=True,methods=["post"])
    def rejeter(self,request,pk=None):
        """Rejette une dépense uniquement si l'utilisateur est son bailleur."""
        d=self.get_object()
        if request.user!=d.projet.bailleur:
            return Response({"detail":"Action réservée au bailleur du projet."},status=403)
        d.statut=Depense.Statut.REJETEE; d.save(update_fields=["statut"])
        ServiceAudit.enregistrer("REJET_DEPENSE",request.user,d.projet)
        Alerte.objects.create(utilisateur=d.auteur, projet=d.projet, type_alerte="DEPENSE_REJETEE", niveau="ATTENTION", message=f"La dépense « {d.libelle} » a été rejetée. Vérification recommandée.")
        return Response(self.get_serializer(d).data)
