"""Vues d'inscription, connexion et profil."""
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import InscriptionSerializer, ConnexionSerializer, UtilisateurSerializer
from .models import Utilisateur
from .throttles import ConnexionRateThrottle, InscriptionRateThrottle

class InscriptionView(generics.CreateAPIView):
    """Crée un compte Chantial."""
    serializer_class = InscriptionSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [InscriptionRateThrottle]

class ConnexionView(APIView):
    """Retourne des jetons JWT après authentification."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ConnexionRateThrottle]

    def post(self, request):
        """Traite la connexion."""
        s = ConnexionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        u = s.validated_data["utilisateur"]
        refresh = RefreshToken.for_user(u)
        return Response({"access":str(refresh.access_token),"refresh":str(refresh),
                         "utilisateur":UtilisateurSerializer(u).data})

class ProfilView(generics.RetrieveUpdateAPIView):
    """Consulte ou modifie le profil connecté."""
    serializer_class = UtilisateurSerializer
    def get_object(self):
        """Retourne le compte authentifié."""
        return self.request.user



class UtilisateurViewSet(viewsets.ModelViewSet):
    """Liste les comptes utiles ; seules les mutations administrateur sont autorisées."""
    serializer_class = UtilisateurSerializer

    def get_throttles(self):
        """Limite spécifiquement la création publique de comptes."""
        if self.action == "create":
            return [InscriptionRateThrottle()]
        return super().get_throttles()

    def get_permissions(self):
        """Autorise la création publique ; protège les autres opérations."""
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        """Utilise le sérialiseur d'inscription lors de la création d'un compte."""
        return InscriptionSerializer if self.action == "create" else UtilisateurSerializer

    def get_queryset(self):
        u = self.request.user
        if u.role == Utilisateur.Role.ADMINISTRATEUR:
            return Utilisateur.objects.all().order_by("-date_creation")
        if u.role == Utilisateur.Role.ENTREPRENEUR:
            return Utilisateur.objects.filter(
                role=Utilisateur.Role.BAILLEUR,
                statut=Utilisateur.Statut.ACTIF
            ).order_by("first_name", "last_name")
        return Utilisateur.objects.filter(pk=u.pk)

    def update(self, request, *args, **kwargs):
        if request.user.role != Utilisateur.Role.ADMINISTRATEUR:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Action réservée à l'administrateur.")
        instance = self.get_object()
        for champ in ("first_name","last_name","email","telephone","role","statut"):
            if champ in request.data:
                setattr(instance, champ, request.data[champ])
        instance.save()
        return Response(UtilisateurSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != Utilisateur.Role.ADMINISTRATEUR:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Action réservée à l'administrateur.")
        instance = self.get_object()
        instance.statut = Utilisateur.Statut.INACTIF
        instance.save(update_fields=["statut"])
        return Response(status=204)
