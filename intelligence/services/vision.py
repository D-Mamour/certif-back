"""Analyse visuelle optionnelle : indice de cohérence, jamais validation automatique d'une étape."""
import os, requests
class ServiceVisionChantier:
    def analyser(self, preuve):
        token=os.getenv('HF_TOKEN',''); model=os.getenv('HF_VISION_MODEL','')
        if not token or not model:
            return {'statut':'NON_CONFIGURE','message':'Analyse visuelle non configurée. La photo reste une preuve terrain horodatée.'}
        labels=['fondations','murs et gros oeuvre','toiture','electricite et plomberie','revetement','finitions','chantier non identifiable']
        preuve.fichier.open('rb')
        try: data=preuve.fichier.read()
        finally: preuve.fichier.close()
        url=f'https://router.huggingface.co/hf-inference/models/{model}'
        r=requests.post(url,headers={'Authorization':f'Bearer {token}'},data=data,timeout=45)
        if not r.ok: return {'statut':'INDISPONIBLE','message':f'Analyse visuelle indisponible (HTTP {r.status_code}).'}
        brut=r.json()
        return {'statut':'ANALYSE','resultat':brut,'avertissement':'Indice visuel uniquement : une photo ne valide pas à elle seule le pourcentage d’avancement.'}
