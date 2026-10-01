"""Services métier des avenants et preuves terrain."""
import hashlib
from django.db import transaction
from django.utils import timezone
from audit.services import ServiceAudit

@transaction.atomic
def decider_avenant(avenant, utilisateur, approuver, commentaire=''):
    avenant.statut='APPROUVE' if approuver else 'REJETE'; avenant.commentaire_decision=commentaire; avenant.date_decision=timezone.now(); avenant.save(update_fields=['statut','commentaire_decision','date_decision'])
    ServiceAudit.enregistrer('AVENANT_'+avenant.statut,utilisateur,avenant.projet,commentaire,{'avenant':str(avenant.id),'montant':str(avenant.montant),'impact_delai_jours':avenant.impact_delai_jours})
    return avenant

def hacher_preuve(preuve):
    h=hashlib.sha256(); preuve.fichier.open('rb')
    try:
        for bloc in iter(lambda:preuve.fichier.read(1024*1024),b''): h.update(bloc)
    finally: preuve.fichier.close()
    preuve.hash_fichier=h.hexdigest(); preuve.save(update_fields=['hash_fichier'])
