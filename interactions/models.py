"""Modèles d'échange entre bailleur et entrepreneur."""
import uuid
from django.conf import settings
from django.db import models
from projets.models import Projet
from finances.models import Depense

class Demande(models.Model):
    """Représente une demande de justification ou de correction."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="demandes")
    depense=models.ForeignKey(Depense,on_delete=models.SET_NULL,null=True,blank=True,related_name="demandes")
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="demandes_creees")
    destinataire=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="demandes_recues")
    type_demande=models.CharField(max_length=20)
    message=models.TextField()
    reponse=models.TextField(blank=True)
    statut=models.CharField(max_length=30,default="EN_ATTENTE")
    date_creation=models.DateTimeField(auto_now_add=True)

class Alerte(models.Model):
    """Notifie un utilisateur lorsqu'un élément nécessite son attention."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    utilisateur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="alertes")
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,null=True,blank=True,related_name="alertes")
    type_alerte=models.CharField(max_length=80)
    message=models.TextField()
    niveau=models.CharField(max_length=30,default="INFO")
    est_lue=models.BooleanField(default=False)
    date_creation=models.DateTimeField(auto_now_add=True)
