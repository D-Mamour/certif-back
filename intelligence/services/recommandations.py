"""Génération des recommandations métier."""
from intelligence.models import Recommandation


class ServiceRecommandation:
    """Centralise la création de recommandations explicables."""

    @staticmethod
    def creer(projet, titre, description, analyse=None, priorite="NORMALE"):
        """Persiste une action recommandée sans exécuter de décision à la place du bailleur."""
        return Recommandation.objects.create(
            projet=projet,
            analyse=analyse,
            titre=titre,
            description=description,
            priorite=priorite,
        )
