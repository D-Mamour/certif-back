"""Service OCR réel des justificatifs Chantial.

Le moteur lit d'abord la couche texte d'un PDF. Pour une image ou un PDF scanné,
il utilise Tesseract via ``pytesseract``. La résolution du binaire Tesseract couvre
PATH, la variable ``TESSERACT_CMD`` et les emplacements Homebrew courants sur macOS.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import os
import re
import shutil

from pypdf import PdfReader


class ServiceOCR:
    """Extrait le texte d'un justificatif puis identifie ses champs principaux."""

    @staticmethod
    def _configurer_tesseract():
        """Configure pytesseract et retourne le chemin du moteur OCR installé."""
        try:
            import pytesseract
        except ImportError as exc:
            raise RuntimeError("pytesseract n'est pas installé. Exécutez pip install -r requirements.txt.") from exc

        candidats = [
            os.getenv("TESSERACT_CMD", "").strip(),
            shutil.which("tesseract") or "",
            "/usr/local/bin/tesseract",      # Homebrew Mac Intel
            "/opt/homebrew/bin/tesseract",  # Homebrew Apple Silicon
        ]
        executable = next((c for c in candidats if c and Path(c).is_file()), None)
        if not executable:
            raise RuntimeError(
                "Tesseract est introuvable. Sur macOS : brew install tesseract tesseract-lang. "
                "Vous pouvez aussi définir TESSERACT_CMD dans .env."
            )
        pytesseract.pytesseract.tesseract_cmd = executable
        return pytesseract

    @classmethod
    def etat_moteur(cls):
        """Retourne un diagnostic exploitable par l'API et la démonstration."""
        try:
            pytesseract = cls._configurer_tesseract()
            return {"disponible": True, "version": str(pytesseract.get_tesseract_version())}
        except Exception as exc:
            return {"disponible": False, "detail": str(exc)}

    @staticmethod
    def normaliser_montant(valeur):
        """Transforme une représentation française/anglaise de montant en Decimal."""
        if valeur is None:
            return None
        brut = re.sub(r"[^\d,.-]", "", str(valeur)).strip()
        if not brut:
            return None
        if "," in brut and "." in brut:
            if brut.rfind(",") > brut.rfind("."):
                brut = brut.replace(".", "").replace(",", ".")
            else:
                brut = brut.replace(",", "")
        elif "," in brut:
            partie = brut.split(",")[-1]
            brut = brut.replace(",", ".") if len(partie) <= 2 else brut.replace(",", "")
        elif brut.count(".") > 1:
            brut = brut.replace(".", "")
        try:
            return Decimal(brut)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _texte_pdf(chemin: Path) -> str:
        """Récupère la couche texte d'un PDF lorsqu'elle existe."""
        lecteur = PdfReader(str(chemin))
        return "\n".join((page.extract_text() or "") for page in lecteur.pages).strip()

    @classmethod
    def _ocr_image_pil(cls, image) -> str:
        """Prétraite une image pour améliorer la lecture de factures et reçus."""
        pytesseract = cls._configurer_tesseract()
        from PIL import ImageOps
        image = ImageOps.exif_transpose(image).convert("L")
        # Agrandissement des petites images : Tesseract est plus stable autour de 300 dpi.
        if image.width < 1600:
            ratio = 1600 / max(image.width, 1)
            image = image.resize((1600, max(1, int(image.height * ratio))))
        image = ImageOps.autocontrast(image)
        config = "--oem 3 --psm 6"
        for langue in ("fra+eng", "eng", None):
            try:
                kwargs = {"config": config}
                if langue:
                    kwargs["lang"] = langue
                texte = pytesseract.image_to_string(image, **kwargs).strip()
                if texte:
                    return texte
            except pytesseract.TesseractError:
                continue
        return ""

    @classmethod
    def _texte_pdf_scane(cls, chemin: Path) -> str:
        """Rasterise les pages d'un PDF scanné puis applique Tesseract."""
        try:
            import fitz
            from PIL import Image
            import io
        except ImportError as exc:
            raise RuntimeError("PyMuPDF et Pillow sont requis pour lire un PDF scanné.") from exc
        textes = []
        with fitz.open(str(chemin)) as document:
            for page in document:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                texte = cls._ocr_image_pil(image)
                if texte:
                    textes.append(texte)
        return "\n".join(textes).strip()

    @classmethod
    def _texte_image(cls, chemin: Path) -> str:
        """Exécute Tesseract sur une image locale après prétraitement."""
        try:
            from PIL import Image
            with Image.open(chemin) as image:
                texte = cls._ocr_image_pil(image)
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"Lecture OCR impossible : {exc}") from exc
        if not texte:
            raise RuntimeError("Tesseract n'a détecté aucun texte exploitable dans l'image.")
        return texte

    def extraire_texte(self, fichier) -> str:
        """Extrait le texte selon le format du justificatif stocké par Django."""
        try:
            chemin = Path(fichier.path)
        except (AttributeError, NotImplementedError) as exc:
            raise RuntimeError("Le stockage du fichier ne fournit pas de chemin local exploitable par l'OCR.") from exc
        if not chemin.exists():
            raise RuntimeError("Le fichier du justificatif est introuvable sur le serveur.")
        extension = chemin.suffix.lower()
        if extension == ".pdf":
            try:
                texte = self._texte_pdf(chemin)
            except Exception:
                texte = ""
            if texte:
                return texte
            texte = self._texte_pdf_scane(chemin)
            if texte:
                return texte
            raise RuntimeError("Aucun texte n'a pu être extrait du PDF.")
        if extension in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}:
            return self._texte_image(chemin)
        if extension in {".txt", ".md"}:
            return chemin.read_text(encoding="utf-8", errors="ignore")
        raise RuntimeError(f"Format OCR non pris en charge : {extension or 'inconnu'}")

    @staticmethod
    def _extraire_numero(texte: str) -> str:
        motifs = [
            r"(?:facture|invoice)\s*(?:n[°oº]?|num(?:éro)?)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{2,})",
            r"(?:n[°oº]?|num(?:éro)?)\s*(?:facture)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{2,})",
        ]
        for motif in motifs:
            m = re.search(motif, texte, re.I)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _extraire_date(texte: str):
        m = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b", texte)
        if not m:
            return None
        valeur = m.group(1)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(valeur, fmt).date()
            except ValueError:
                continue
        return None

    def _extraire_montant(self, texte: str):
        """Cherche d'abord le total TTC/net à payer, puis un total générique."""
        motifs = [
            r"(?:total\s*ttc|net\s*[àa]\s*payer|montant\s*ttc|grand\s*total)\s*[:\-]?\s*([\d\s.,]+)",
            r"(?:total|montant)\s*[:\-]?\s*([\d\s.,]+)",
        ]
        for motif in motifs:
            matches = re.findall(motif, texte, re.I)
            if matches:
                montant = self.normaliser_montant(matches[-1])
                if montant is not None and montant >= 0:
                    return montant
        return None

    @staticmethod
    def _extraire_fournisseur(texte: str) -> str:
        m = re.search(r"(?:fournisseur|supplier|vendeur)\s*[:\-]\s*([^\n\r]{2,100})", texte, re.I)
        if m:
            return m.group(1).strip()
        for ligne in (x.strip() for x in texte.splitlines()):
            if len(ligne) >= 3 and not re.search(r"facture|invoice|reçu|receipt", ligne, re.I):
                return ligne[:180]
        return ""

    def extraire(self, fichier):
        """Retourne les champs normalisés attendus par ``ExtractionOCR``."""
        texte = self.extraire_texte(fichier)
        return {
            "numero_document": self._extraire_numero(texte),
            "fournisseur": self._extraire_fournisseur(texte),
            "date_document": self._extraire_date(texte),
            "montant_extrait": self._extraire_montant(texte),
            "texte_extrait": texte,
        }
