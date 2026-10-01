"""Règles métier, contrôles OCR et orchestration RAG de Chantial."""
from decimal import Decimal
from django.utils import timezone
from intelligence.models import Analyse, Anomalie, Recommandation
from interactions.models import Alerte
from .recommandations import ServiceRecommandation
from .rag import ServiceRAG
from .controle_financier import ServiceControleFinancier


class ServiceAnalyse:
    """Combine des contrôles déterministes et une analyse documentaire RAG."""

    def __init__(self, rag=None):
        self.rag = rag or ServiceRAG()

    @staticmethod
    def _anomalie(projet, type_anomalie, niveau, description, depense=None):
        """Crée ou actualise une anomalie sans la dupliquer à chaque analyse."""
        objet, _ = Anomalie.objects.update_or_create(
            projet=projet,
            depense=depense,
            type_anomalie=type_anomalie,
            statut="OUVERTE",
            defaults={"niveau": niveau, "description": description},
        )
        return objet

    def detecter_anomalies(self, projet):
        """Contrôle budget, justificatifs et cohérence déclaration ↔ OCR."""
        anomalies = []
        for etape in projet.etapes.prefetch_related("depenses__justificatifs__extraction_ocr"):
            total = sum((d.montant for d in etape.depenses.all()), Decimal("0"))
            if total > etape.budget_previsionnel:
                anomalies.append(self._anomalie(
                    projet, "DEPASSEMENT_BUDGET", "ELEVE",
                    f"Les dépenses de l'étape {etape.nom} dépassent son budget prévisionnel."
                ))

            for depense in etape.depenses.all():
                justificatif = depense.justificatifs.first()
                if not justificatif:
                    anomalies.append(self._anomalie(
                        projet, "JUSTIFICATIF_MANQUANT", "MODERE",
                        "Vérification recommandée : justificatif manquant.", depense
                    ))
                    continue

                try:
                    ocr = justificatif.extraction_ocr
                except Exception:
                    anomalies.append(self._anomalie(
                        projet, "OCR_INDISPONIBLE", "MODERE",
                        "Le justificatif existe mais aucune extraction OCR exploitable n'est disponible.", depense
                    ))
                    continue

                if ocr.montant_extrait is None:
                    anomalies.append(self._anomalie(
                        projet, "MONTANT_OCR_MANQUANT", "MODERE",
                        "Le montant TTC n'a pas été identifié automatiquement. Vérification du document recommandée.", depense
                    ))
                elif abs(depense.montant - ocr.montant_extrait) > Decimal("0.01"):
                    ecart = depense.montant - ocr.montant_extrait
                    anomalies.append(self._anomalie(
                        projet, "ECART_MONTANT_OCR", "ELEVE",
                        f"Écart de {abs(ecart):,.2f} FCFA entre le montant déclaré et le montant TTC extrait.", depense
                    ))

                if ocr.date_document and depense.date_depense != ocr.date_document:
                    anomalies.append(self._anomalie(
                        projet, "ECART_DATE_OCR", "MODERE",
                        "La date déclarée diffère de la date d'émission extraite du justificatif.", depense
                    ))

                f_decl = (depense.fournisseur or "").strip().casefold()
                f_ocr = (ocr.fournisseur or "").strip().casefold()
                if f_decl and f_ocr and f_decl != f_ocr:
                    anomalies.append(self._anomalie(
                        projet, "ECART_FOURNISSEUR_OCR", "MODERE",
                        "Le fournisseur déclaré diffère du fournisseur identifié sur le justificatif.", depense
                    ))
        controle = ServiceControleFinancier()
        # Doublons exacts ou très similaires.
        for etape in projet.etapes.all():
            for depense in etape.depenses.all():
                for justificatif in depense.justificatifs.all():
                    for autre, score, raison in controle.detecter_doublons(justificatif):
                        anomalies.append(self._anomalie(projet, "DOUBLON_FACTURE", "CRITIQUE", f"Justificatif potentiellement déjà soumis ({raison}, similarité {float(score)*100:.0f} %). Vérification humaine recommandée.", depense))
        # Prix unitaires comparés uniquement à un référentiel explicite (devis validé / source marché datée).
        for depense, ligne, ref, ecart in controle.anomalies_prix(projet):
            anomalies.append(self._anomalie(projet, "ANOMALIE_PRIX", "ELEVE", f"Le prix unitaire de « {ligne.designation} » dépasse de {ecart:.1f} % la référence {ref.source}. Vérification recommandée.", depense))
        # Corrélation avancement physique / consommation budgétaire.
        ind = controle.indicateurs_evm(projet)
        if ind["alerte_critique"]:
            anomalies.append(self._anomalie(projet, "SURCONSOMMATION_BUDGETAIRE", "CRITIQUE", f"Avancement physique {ind['avancement_physique']:.1f} % contre consommation budgétaire {ind['consommation_budgetaire']:.1f} % (écart {ind['ecart_points']:.1f} points)."))
        return anomalies

    def evaluer_risque_retard(self, projet):
        """Évalue le retard à partir des dates prévues et des derniers avancements."""
        aujourd_hui = timezone.localdate()
        retard = sum(1 for e in projet.etapes.all() if e.date_fin_prevue < aujourd_hui and e.avancement_actuel < 100)
        return (("ELEVE", Decimal("80")) if retard >= 2 else
                ("MODERE", Decimal("50")) if retard == 1 else
                ("FAIBLE", Decimal("20")))

    def analyser_projet(self, projet):
        """Produit anomalies, risque, RAG et recommandations explicables."""
        anomalies = self.detecter_anomalies(projet)
        niveau, score = self.evaluer_risque_retard(projet)
        # Le RAG enrichit l'analyse mais ne doit pas bloquer les contrôles
        # déterministes lorsque le fournisseur IA est temporairement indisponible.
        try:
            rag = self.rag.analyser(
                projet,
                "Analyse les écarts du chantier à partir des documents disponibles.",
            )
        except Exception as exc:
            rag = {
                "reponse": "Analyse documentaire RAG temporairement indisponible.",
                "sources": [],
                "erreur_technique": str(exc),
            }

        analyse = Analyse.objects.create(
            projet=projet, niveau_risque=niveau, score_risque=score,
            resume=f"{len(anomalies)} anomalie(s) ouverte(s), niveau de risque {niveau}."
        )

        # Les recommandations précédentes restent historisées ; on rattache les nouvelles à cette analyse.
        if anomalies:
            ServiceRecommandation.creer(
                projet=projet, analyse=analyse, titre="Vérifier les écarts détectés",
                description="Comparer les données déclarées aux justificatifs OCR avant validation.", priorite="HAUTE"
            )
        if niveau in {"MODERE", "ELEVE"}:
            ServiceRecommandation.creer(
                projet=projet, analyse=analyse, titre="Surveiller le calendrier du chantier",
                description="Vérifier les étapes en retard et actualiser l'avancement avec l'entrepreneur.", priorite="HAUTE"
            )

        if anomalies or niveau in {"MODERE", "ELEVE"}:
            Alerte.objects.create(
                utilisateur=projet.bailleur, projet=projet, type_alerte="ANALYSE_PROJET",
                niveau=niveau, message=f"Analyse de {projet.nom} : {len(anomalies)} anomalie(s), risque {niveau}."
            )
        return analyse, rag
