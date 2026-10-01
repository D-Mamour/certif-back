"""Sérialise les modèles de l’application audit."""
from rest_framework import serializers
from .models import Historique

class HistoriqueSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Historique."""
    class Meta:
        model=Historique
        fields="__all__"
        read_only_fields=["id"]

