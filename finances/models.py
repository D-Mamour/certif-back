"""Modèles financiers."""
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from projets.models import Etape

class Depense(models.Model):
    """Représente une dépense déclarée pour une étape."""
    class Statut(models.TextChoices):
        EN_ATTENTE="EN_ATTENTE","En attente"
        VALIDEE="VALIDEE","Validée"
        REJETEE="REJETEE","Rejetée"

    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    etape=models.ForeignKey(Etape,on_delete=models.CASCADE,related_name="depenses")
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="depenses_declarees")
    libelle=models.CharField(max_length=200)
    montant=models.DecimalField(max_digits=16,decimal_places=2,validators=[MinValueValidator(Decimal("0"))])
    date_depense=models.DateField()
    fournisseur=models.CharField(max_length=180,blank=True)
    statut=models.CharField(max_length=15,choices=Statut.choices,default=Statut.EN_ATTENTE)
    date_creation=models.DateTimeField(auto_now_add=True)

    @property
    def projet(self):
        """Retourne le projet parent."""
        return self.etape.projet
