"""Contrôles financiers explicables : doublons, prix de référence et EVM simplifié."""
import hashlib, re
from decimal import Decimal
from difflib import SequenceMatcher
from documents.models import Justificatif, PrixReference

class ServiceControleFinancier:
    SEUIL_PRIX = Decimal("0.15")
    SEUIL_SURCONSOMMATION = Decimal("10")

    @staticmethod
    def empreinte_fichier(champ_fichier):
        h=hashlib.sha256(); champ_fichier.open('rb')
        try:
            for bloc in iter(lambda: champ_fichier.read(1024*1024), b''): h.update(bloc)
        finally: champ_fichier.close()
        return h.hexdigest()

    @staticmethod
    def normaliser(texte):
        return re.sub(r"[^a-z0-9]+", " ", (texte or "").casefold()).strip()

    def detecter_doublons(self, justificatif):
        resultats=[]
        if justificatif.hash_sha256:
            for autre in Justificatif.objects.filter(hash_sha256=justificatif.hash_sha256).exclude(pk=justificatif.pk):
                resultats.append((autre, Decimal("1.00"), "empreinte SHA-256 identique"))
        try: courant=justificatif.extraction_ocr
        except Exception: return resultats
        signature=self.normaliser(f"{courant.numero_document} {courant.fournisseur} {courant.date_document} {courant.montant_extrait} {courant.texte_extrait[:1200]}")
        if not signature: return resultats
        for autre in Justificatif.objects.filter(depense__etape__projet=justificatif.depense.projet).exclude(pk=justificatif.pk).select_related('extraction_ocr'):
            try: o=autre.extraction_ocr
            except Exception: continue
            sig2=self.normaliser(f"{o.numero_document} {o.fournisseur} {o.date_document} {o.montant_extrait} {o.texte_extrait[:1200]}")
            score=Decimal(str(round(SequenceMatcher(None,signature,sig2).ratio(),3)))
            if score >= Decimal("0.88") and not any(x[0].pk==autre.pk for x in resultats): resultats.append((autre,score,"forte similarité OCR"))
        return resultats

    def anomalies_prix(self, projet):
        ecarts=[]
        refs=list(PrixReference.objects.filter(projet__in=[projet,None]))
        for dep in projet.etapes.prefetch_related('depenses__justificatifs__extraction_ocr__lignes').all():
            for d in dep.depenses.all():
                for j in d.justificatifs.all():
                    try: lignes=j.extraction_ocr.lignes.all()
                    except Exception: continue
                    for ligne in lignes:
                        if ligne.prix_unitaire is None: continue
                        candidats=[r for r in refs if SequenceMatcher(None,self.normaliser(ligne.designation),self.normaliser(r.designation)).ratio()>=.72]
                        if not candidats: continue
                        ref=min(candidats,key=lambda r:abs(r.prix_unitaire-ligne.prix_unitaire))
                        if ref.prix_unitaire and ligne.prix_unitaire > ref.prix_unitaire*(Decimal('1')+self.SEUIL_PRIX):
                            ecarts.append((d,ligne,ref,(ligne.prix_unitaire/ref.prix_unitaire-1)*100))
        return ecarts

    def indicateurs_evm(self, projet):
        budget=Decimal(projet.budget_previsionnel or 0)
        avenants=sum((a.montant for a in projet.avenants.filter(statut='APPROUVE')),Decimal('0'))
        budget_rev=budget+avenants
        etapes=list(projet.etapes.all())
        total_poids=sum((e.budget_previsionnel for e in etapes),Decimal('0')) or Decimal('1')
        avancement=sum((Decimal(e.avancement_actuel)*e.budget_previsionnel for e in etapes),Decimal('0'))/total_poids if etapes else Decimal('0')
        depenses=sum((d.montant for e in etapes for d in e.depenses.filter(statut='VALIDEE')),Decimal('0'))
        consommation=(depenses/budget_rev*100) if budget_rev else Decimal('0')
        ecart=consommation-avancement
        ev=budget_rev*avancement/100; ac=depenses
        cpi=(ev/ac) if ac else None
        return {'budget_initial':budget,'avenants_approuves':avenants,'budget_reference':budget_rev,'depenses_validees':depenses,'avancement_physique':avancement,'consommation_budgetaire':consommation,'ecart_points':ecart,'EV':ev,'AC':ac,'CPI':cpi,'alerte_critique':ecart>=self.SEUIL_SURCONSOMMATION}
