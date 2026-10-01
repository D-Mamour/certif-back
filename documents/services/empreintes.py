"""Empreintes documentaires utilisées pour repérer les doublons exacts."""
from intelligence.services.controle_financier import ServiceControleFinancier

def calculer_empreintes(justificatif):
    sha=ServiceControleFinancier.empreinte_fichier(justificatif.fichier)
    justificatif.hash_sha256=sha
    justificatif.save(update_fields=['hash_sha256'])
    return sha
