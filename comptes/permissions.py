"""Permissions métier réutilisables."""
from rest_framework.permissions import BasePermission
from .models import Utilisateur

class CompteActif(BasePermission):
    """Refuse l'accès aux comptes désactivés."""
    def has_permission(self, request, view):
        """Vérifie authentification et statut actif."""
        return bool(request.user and request.user.is_authenticated
                    and request.user.statut == Utilisateur.Statut.ACTIF)

class EstEntrepreneur(BasePermission):
    """Autorise uniquement les entrepreneurs."""
    def has_permission(self, request, view):
        """Vérifie le rôle entrepreneur."""
        return bool(request.user.is_authenticated and request.user.role == Utilisateur.Role.ENTREPRENEUR)

class EstBailleur(BasePermission):
    """Autorise uniquement les bailleurs."""
    def has_permission(self, request, view):
        """Vérifie le rôle bailleur."""
        return bool(request.user.is_authenticated and request.user.role == Utilisateur.Role.BAILLEUR)

class EstAdministrateur(BasePermission):
    """Autorise uniquement les administrateurs."""
    def has_permission(self, request, view):
        """Vérifie le rôle administrateur."""
        return bool(request.user.is_authenticated and request.user.role == Utilisateur.Role.ADMINISTRATEUR)
