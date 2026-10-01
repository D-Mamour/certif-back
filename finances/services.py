"""Services de contrôle financier de Chantial."""
from decimal import Decimal


class ServiceFinance:
    """Regroupe les règles déterministes appliquées aux dépenses."""

    @staticmethod
    def total_depenses_etape(etape):
        """Additionne les dépenses enregistrées pour une étape."""
        return sum((depense.montant for depense in etape.depenses.all()), Decimal("0"))

    @staticmethod
    def verifier_depassement_budget(etape):
        """Indique si les dépenses d'une étape dépassent son budget prévu."""
        total = ServiceFinance.total_depenses_etape(etape)
        return {
            "depassement": total > etape.budget_previsionnel,
            "total_depenses": total,
            "budget_previsionnel": etape.budget_previsionnel,
            "ecart": total - etape.budget_previsionnel,
        }

    @staticmethod
    def verifier_justificatif(depense):
        """Indique si au moins un justificatif est associé à la dépense."""
        return depense.justificatifs.exists()
