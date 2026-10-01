"""Modèles liés aux comptes et aux rôles."""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class GestionnaireUtilisateur(BaseUserManager):
    """Crée les utilisateurs Chantial avec l'email comme identifiant."""
    def create_user(self, email, password=None, **extra_fields):
        """Crée un utilisateur standard et chiffre son mot de passe."""
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email)
        utilisateur = self.model(email=email, **extra_fields)
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, password=None, **extra_fields):
        """Crée un administrateur Django."""
        extra_fields.setdefault("role", "ADMINISTRATEUR")
        extra_fields.setdefault("statut", "ACTIF")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class Utilisateur(AbstractUser):
    """Représente entrepreneur, bailleur ou administrateur via l'attribut rôle."""
    class Role(models.TextChoices):
        ENTREPRENEUR="ENTREPRENEUR","Entrepreneur"
        BAILLEUR="BAILLEUR","Bailleur"
        ADMINISTRATEUR="ADMINISTRATEUR","Administrateur"

    class Statut(models.TextChoices):
        ACTIF="ACTIF","Actif"
        INACTIF="INACTIF","Inactif"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF)
    date_creation = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = GestionnaireUtilisateur()

    def __str__(self):
        """Retourne l'adresse email de l'utilisateur."""
        return self.email
