"""Extraction et normalisation du contenu des documents."""
from pathlib import Path
from pypdf import PdfReader


class ServiceExtraction:
    """Transforme les documents pris en charge en texte exploitable par le RAG."""

    @staticmethod
    def extraire_pdf(chemin):
        """Extrait le texte d'un fichier PDF page par page."""
        lecteur = PdfReader(str(chemin))
        return "\n".join((page.extract_text() or "") for page in lecteur.pages).strip()

    def extraire_texte(self, document):
        """Choisit la méthode d'extraction selon le type du fichier."""
        chemin = Path(document.fichier.path)
        extension = chemin.suffix.lower()
        if extension == ".pdf":
            return self.extraire_pdf(chemin)
        if extension in {".txt", ".md"}:
            return chemin.read_text(encoding="utf-8", errors="ignore")
        # Les images sont traitées par ServiceOCR, pas par cette classe.
        return ""
