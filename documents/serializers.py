"""Sérialise les justificatifs, extractions OCR et documents projet."""
from rest_framework import serializers
from pathlib import Path
from .models import Justificatif, ExtractionOCR, DocumentProjet

class JustificatifSerializer(serializers.ModelSerializer):
    """Sérialise et valide un justificatif associé à une dépense."""
    class Meta:
        model=Justificatif
        fields="__all__"
        read_only_fields=["id","date_ajout","hash_sha256","empreinte_visuelle"]

    def validate_fichier(self, fichier):
        """Refuse proprement les fichiers vides, trop lourds ou non supportés."""
        if not fichier or getattr(fichier, "size", 0) <= 0:
            raise serializers.ValidationError("Le fichier est vide.")
        if fichier.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Le justificatif ne doit pas dépasser 10 Mo.")
        extension = Path(fichier.name).suffix.lower()
        if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
            raise serializers.ValidationError("Formats acceptés : PDF, PNG, JPG et JPEG.")
        return fichier

    def validate_type_document(self, valeur):
        return (valeur or "FACTURE").strip()[:80]

    def validate(self, attrs):
        """Vérifie que la dépense existe bien dans le contexte de l’utilisateur."""
        attrs = super().validate(attrs)
        depense = attrs.get("depense")
        request = self.context.get("request")
        if depense is not None and request is not None:
            utilisateur = request.user
            if not getattr(utilisateur, "is_authenticated", False):
                raise serializers.ValidationError("Authentification requise.")
            if depense.projet.entrepreneur_id != utilisateur.id:
                raise serializers.ValidationError({"depense": "Cette dépense ne vous appartient pas."})
        return attrs

class ExtractionOCRSerializer(serializers.ModelSerializer):
    """Expose les informations réellement extraites par OCR."""
    class Meta:
        model=ExtractionOCR
        fields="__all__"
        read_only_fields=["id","date_extraction"]

class DocumentProjetSerializer(serializers.ModelSerializer):
    """Sérialise un document utilisé comme source documentaire du projet."""
    class Meta:
        model=DocumentProjet
        fields="__all__"
        read_only_fields=["id","ajoute_par","texte_extrait","est_indexe","date_ajout"]

from .models import LigneFacture, PrixReference
class LigneFactureSerializer(serializers.ModelSerializer):
    class Meta: model=LigneFacture; fields='__all__'; read_only_fields=['id']
class PrixReferenceSerializer(serializers.ModelSerializer):
    class Meta: model=PrixReference; fields='__all__'; read_only_fields=['id','date_creation']
