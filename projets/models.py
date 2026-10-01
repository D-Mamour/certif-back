"""Modèles de gestion des chantiers."""
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Sum

class Projet(models.Model):
    """Représente un chantier géré par un entrepreneur pour un bailleur."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    entrepreneur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="projets_entrepreneur")
    bailleur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="projets_bailleur")
    nom=models.CharField(max_length=180)
    description=models.TextField(blank=True)
    localisation=models.CharField(max_length=255,blank=True)
    budget_previsionnel=models.DecimalField(max_digits=16,decimal_places=2,validators=[MinValueValidator(Decimal("0"))])
    date_debut=models.DateField()
    date_fin_prevue=models.DateField()
    statut=models.CharField(max_length=20,default="PLANIFIE")
    date_creation=models.DateTimeField(auto_now_add=True)

    @property
    def montant_depense(self):
        """Additionne toutes les dépenses rattachées aux étapes."""
        return self.etapes.aggregate(total=Sum("depenses__montant"))["total"] or Decimal("0")

    @property
    def budget_restant(self):
        """Retourne la différence entre budget prévu et dépenses."""
        return self.budget_previsionnel-self.montant_depense

    @property
    def avancement_global(self):
        """Calcule la moyenne du dernier avancement de chaque étape."""
        vals=[e.avancement_actuel for e in self.etapes.all()]
        return sum(vals,Decimal("0"))/len(vals) if vals else Decimal("0")

class Etape(models.Model):
    """Représente une phase du chantier."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="etapes")
    nom=models.CharField(max_length=150)
    description=models.TextField(blank=True)
    ordre=models.PositiveIntegerField()
    budget_previsionnel=models.DecimalField(max_digits=16,decimal_places=2,validators=[MinValueValidator(Decimal("0"))])
    date_debut_prevue=models.DateField()
    date_fin_prevue=models.DateField()

    class Meta:
        ordering=["ordre"]
        unique_together=("projet","ordre")

    @property
    def avancement_actuel(self):
        """Retourne le dernier pourcentage déclaré."""
        dernier=self.avancements.order_by("-date_declaration").first()
        return dernier.pourcentage if dernier else Decimal("0")

class Avancement(models.Model):
    """Historise l'évolution d'une étape."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    etape=models.ForeignKey(Etape,on_delete=models.CASCADE,related_name="avancements")
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="avancements_declares")
    pourcentage=models.DecimalField(max_digits=5,decimal_places=2,validators=[MinValueValidator(0),MaxValueValidator(100)])
    commentaire=models.TextField(blank=True)
    date_declaration=models.DateTimeField(auto_now_add=True)


class Avenant(models.Model):
    """Modification contractuelle soumise par l'entrepreneur et décidée par le bailleur."""
    class Statut(models.TextChoices):
        BROUILLON="BROUILLON","Brouillon"
        SOUMIS="SOUMIS","Soumis"
        APPROUVE="APPROUVE","Approuvé"
        REJETE="REJETE","Rejeté"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="avenants")
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="avenants_soumis")
    titre=models.CharField(max_length=180)
    motif=models.TextField()
    montant=models.DecimalField(max_digits=16,decimal_places=2,default=0,validators=[MinValueValidator(Decimal("0"))])
    impact_delai_jours=models.PositiveIntegerField(default=0)
    document=models.FileField(upload_to="avenants/%Y/%m/",blank=True)
    statut=models.CharField(max_length=15,choices=Statut.choices,default=Statut.BROUILLON)
    commentaire_decision=models.TextField(blank=True)
    date_creation=models.DateTimeField(auto_now_add=True)
    date_decision=models.DateTimeField(null=True,blank=True)

class JournalChantier(models.Model):
    """Preuve terrain multimédia horodatée ; la géolocalisation reste un indice, pas une preuve absolue."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="journal_chantier")
    etape=models.ForeignKey(Etape,on_delete=models.SET_NULL,null=True,blank=True,related_name="preuves_terrain")
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="preuves_terrain")
    fichier=models.FileField(upload_to="journal_chantier/%Y/%m/")
    commentaire=models.TextField(blank=True)
    latitude=models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True)
    longitude=models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True)
    hash_fichier=models.CharField(max_length=64,blank=True,editable=False)
    analyse_visuelle=models.JSONField(default=dict,blank=True)
    date_capture=models.DateTimeField(null=True,blank=True)
    date_ajout=models.DateTimeField(auto_now_add=True)

class RapportChantier(models.Model):
    """Archive un rapport généré et son statut de diffusion."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name="rapports")
    genere_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="rapports_generes")
    periode=models.CharField(max_length=7,help_text="AAAA-MM")
    fichier=models.FileField(upload_to="rapports/%Y/%m/",blank=True)
    envoye_email=models.BooleanField(default=False)
    envoye_whatsapp=models.BooleanField(default=False)
    date_generation=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["-date_generation"]
        unique_together=("projet","periode")

class SituationTravaux(models.Model):
    """Situation d'avancement soumise par l'entrepreneur et validée/rejetée par le bailleur."""
    class Statut(models.TextChoices):
        SOUMISE='SOUMISE','Soumise'; VALIDEE='VALIDEE','Validée'; REJETEE='REJETEE','Rejetée'
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    projet=models.ForeignKey(Projet,on_delete=models.CASCADE,related_name='situations_travaux')
    etape=models.ForeignKey(Etape,on_delete=models.PROTECT,related_name='situations_travaux')
    auteur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='situations_soumises')
    pourcentage=models.DecimalField(max_digits=5,decimal_places=2,validators=[MinValueValidator(0),MaxValueValidator(100)])
    montant_situation=models.DecimalField(max_digits=16,decimal_places=2,default=0,validators=[MinValueValidator(Decimal("0"))])
    commentaire=models.TextField(blank=True)
    statut=models.CharField(max_length=10,choices=Statut.choices,default=Statut.SOUMISE)
    decide_par=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='situations_decidees')
    commentaire_decision=models.TextField(blank=True)
    date_soumission=models.DateTimeField(auto_now_add=True)
    date_decision=models.DateTimeField(null=True,blank=True)
