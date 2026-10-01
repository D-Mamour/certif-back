"""Sérialise les modèles de l’application projets."""
from rest_framework import serializers
from .models import Projet, Etape, Avancement

class ProjetSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Projet."""
    class Meta:
        model=Projet
        fields="__all__"
        read_only_fields=["id","entrepreneur"]

    def validate(self, attrs):
        debut=attrs.get("date_debut", getattr(self.instance,"date_debut",None))
        fin=attrs.get("date_fin_prevue", getattr(self.instance,"date_fin_prevue",None))
        if debut and fin and fin < debut:
            raise serializers.ValidationError({"date_fin_prevue":"La date de fin doit être postérieure ou égale à la date de début."})
        return attrs

class EtapeSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Etape."""
    class Meta:
        model=Etape
        fields="__all__"
        read_only_fields=["id"]

    def validate(self, attrs):
        debut=attrs.get("date_debut_prevue", getattr(self.instance,"date_debut_prevue",None))
        fin=attrs.get("date_fin_prevue", getattr(self.instance,"date_fin_prevue",None))
        if debut and fin and fin < debut:
            raise serializers.ValidationError({"date_fin_prevue":"La date de fin de l’étape doit être postérieure ou égale à sa date de début."})
        projet=attrs.get("projet", getattr(self.instance,"projet",None))
        if projet and debut and fin and (debut < projet.date_debut or fin > projet.date_fin_prevue):
            raise serializers.ValidationError("Les dates de l’étape doivent rester dans la période prévue du projet.")
        return attrs

class AvancementSerializer(serializers.ModelSerializer):
    """Sérialise l’avancement et empêche une régression accidentelle."""
    class Meta:
        model=Avancement
        fields="__all__"
        read_only_fields=["id","auteur","date_declaration"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        etape = attrs.get("etape", getattr(self.instance, "etape", None))
        nouveau = attrs.get("pourcentage", getattr(self.instance, "pourcentage", None))
        if etape is not None and nouveau is not None and self.instance is None:
            dernier = etape.avancements.order_by("-date_declaration").first()
            if dernier is not None and nouveau < dernier.pourcentage:
                raise serializers.ValidationError({
                    "pourcentage": f"L’avancement ne peut pas être inférieur au dernier avancement déclaré ({dernier.pourcentage} %)."
                })
        return attrs


from .models import Avenant, JournalChantier
class AvenantSerializer(serializers.ModelSerializer):
    class Meta:
        model=Avenant; fields='__all__'; read_only_fields=['id','auteur','date_creation','date_decision','commentaire_decision']
class JournalChantierSerializer(serializers.ModelSerializer):
    class Meta:
        model=JournalChantier; fields='__all__'; read_only_fields=['id','auteur','hash_fichier','analyse_visuelle','date_ajout']
from .models import RapportChantier
class RapportChantierSerializer(serializers.ModelSerializer):
    class Meta:
        model=RapportChantier; fields='__all__'; read_only_fields=['id','genere_par','date_generation','envoye_email','envoye_whatsapp','fichier']
from .models import SituationTravaux
class SituationTravauxSerializer(serializers.ModelSerializer):
    class Meta:
        model=SituationTravaux; fields='__all__'; read_only_fields=['id','auteur','decide_par','statut','date_soumission','date_decision','commentaire_decision']
