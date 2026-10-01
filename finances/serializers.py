"""Sérialise et valide les dépenses de Chantial."""
from decimal import Decimal
from rest_framework import serializers
from .models import Depense


class DepenseSerializer(serializers.ModelSerializer):
    """Sérialise une dépense et protège les champs pilotés par le serveur."""

    class Meta:
        model = Depense
        fields = "__all__"
        # L'auteur et le statut sont décidés par le backend. Un entrepreneur ne
        # peut donc pas créer lui-même une dépense déjà « validée ».
        read_only_fields = ["id", "auteur", "statut", "date_creation"]

    def validate_montant(self, valeur):
        """Une dépense réelle doit avoir un montant strictement positif."""
        if valeur is None or valeur <= Decimal("0"):
            raise serializers.ValidationError("Le montant doit être strictement supérieur à 0 FCFA.")
        return valeur

    def validate_libelle(self, valeur):
        valeur = (valeur or "").strip()
        if len(valeur) < 2:
            raise serializers.ValidationError("Le libellé doit contenir au moins 2 caractères.")
        return valeur

    def validate_fournisseur(self, valeur):
        return (valeur or "").strip()
