"""Sérialise les modèles de l’application intelligence."""
from rest_framework import serializers
from .models import Analyse, Anomalie, Recommandation, FragmentDocument

class AnalyseSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Analyse."""
    class Meta:
        model=Analyse
        fields="__all__"
        read_only_fields=["id"]

class AnomalieSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Anomalie."""
    class Meta:
        model=Anomalie
        fields="__all__"
        read_only_fields=["id"]

class RecommandationSerializer(serializers.ModelSerializer):
    """Sérialise le modèle Recommandation."""
    class Meta:
        model=Recommandation
        fields="__all__"
        read_only_fields=["id"]



class FragmentDocumentSerializer(serializers.ModelSerializer):
    """Sérialise un fragment documentaire indexé."""

    class Meta:
        model = FragmentDocument
        fields = ["id", "document", "ordre", "contenu", "date_indexation"]
        read_only_fields = ["id", "date_indexation"]
