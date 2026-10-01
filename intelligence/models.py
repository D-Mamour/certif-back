"""Résultats des contrôles et analyses intelligentes."""
import uuid
from django.db import models
from projets.models import Projet
from finances.models import Depense

class Analyse(models.Model):
    """Persiste la synthèse d'une analyse de projet."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="analyses")
    niveau_risque=models.CharField(max_length=30,blank=True)
    score_risque=models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True)
    resume=models.TextField()
    date_analyse=models.DateTimeField(auto_now_add=True)

class Anomalie(models.Model):
    """Représente un écart nécessitant éventuellement une vérification humaine."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="anomalies")
    depense=models.ForeignKey(Depense,on_delete=models.SET_NULL,null=True,blank=True,related_name="anomalies")
    type_anomalie=models.CharField(max_length=80)
    description=models.TextField()
    niveau=models.CharField(max_length=30)
    statut=models.CharField(max_length=30,default="OUVERTE")
    date_detection=models.DateTimeField(auto_now_add=True)

class Recommandation(models.Model):
    """Stocke une action recommandée ; elle ne remplace pas la décision du bailleur."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="recommandations")
    analyse=models.ForeignKey(Analyse,on_delete=models.CASCADE,null=True,blank=True,related_name="recommandations")
    titre=models.CharField(max_length=180)
    description=models.TextField()
    priorite=models.CharField(max_length=30,default="NORMALE")
    date_creation=models.DateTimeField(auto_now_add=True)

from documents.models import DocumentProjet


class FragmentDocument(models.Model):
    """Conserve un fragment textuel et son vecteur pour la recherche RAG."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        DocumentProjet, on_delete=models.CASCADE, related_name="fragments"
    )
    contenu = models.TextField()
    ordre = models.PositiveIntegerField()
    vecteur = models.JSONField(default=list, blank=True)
    date_indexation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "ordre"]
        unique_together = ("document", "ordre")
