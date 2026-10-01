"""Embeddings Hugging Face pour Chantial."""
import os
from functools import lru_cache
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def charger_modele():
    """Charge une seule fois le modèle multilingue."""
    return SentenceTransformer(os.getenv(
        "HF_EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ))

class ServiceEmbeddings:
    """Encode les textes en vecteurs sémantiques."""
    def __init__(self):
        """Initialise le modèle."""
        self.modele = charger_modele()

    def encoder(self, texte):
        """Encode un texte unique."""
        if not texte or not texte.strip():
            return []
        return self.modele.encode(
            texte, normalize_embeddings=True, convert_to_numpy=True
        ).tolist()

    def encoder_lot(self, textes):
        """Encode plusieurs fragments."""
        textes = [t for t in textes if t and t.strip()]
        if not textes:
            return []
        return self.modele.encode(
            textes, normalize_embeddings=True, convert_to_numpy=True
        ).tolist()
