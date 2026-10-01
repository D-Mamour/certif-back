"""Sérialise les modèles de l’application interactions."""
from rest_framework import serializers
from .models import Demande, Alerte

class DemandeSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Demande."""
    class Meta:
        model=Demande
        fields="__all__"
        read_only_fields=["id","auteur","statut","reponse"]

class AlerteSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Alerte."""
    class Meta:
        model=Alerte
        fields="__all__"
        read_only_fields=["id"]

