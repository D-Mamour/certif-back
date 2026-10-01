"""Sérialise les comptes et l'authentification."""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Utilisateur

class UtilisateurSerializer(serializers.ModelSerializer):
    """Expose les données non sensibles du compte."""
    class Meta:
        model = Utilisateur
        fields = ["id","email","first_name","last_name","telephone","role","statut","date_creation"]
        read_only_fields = ["id","statut","date_creation"]

class InscriptionSerializer(serializers.ModelSerializer):
    """Crée un compte avec un mot de passe correctement haché."""
    mot_de_passe = serializers.CharField(write_only=True, min_length=10, max_length=128)
    class Meta:
        model = Utilisateur
        fields = ["email","mot_de_passe","first_name","last_name","telephone","role"]

    def validate_email(self, value):
        """Normalise l'adresse pour éviter les doublons dus à la casse/aux espaces."""
        return value.strip().lower()

    def validate_mot_de_passe(self, value):
        """Applique aussi côté serveur les règles de robustesse Django."""
        validate_password(value)
        return value

    def create(self, validated_data):
        """Délègue la création au gestionnaire utilisateur."""
        mdp = validated_data.pop("mot_de_passe")
        return Utilisateur.objects.create_user(password=mdp, **validated_data)

class ConnexionSerializer(serializers.Serializer):
    """Valide une tentative de connexion."""
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authentifie puis vérifie que le compte est actif."""
        email = attrs["email"].strip().lower()
        utilisateur = authenticate(email=email, password=attrs["mot_de_passe"])
        if not utilisateur:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        if utilisateur.statut != Utilisateur.Statut.ACTIF:
            raise serializers.ValidationError("Ce compte est désactivé.")
        attrs["utilisateur"] = utilisateur
        return attrs
