"""Journal d'audit append-only avec chaîne de hachage détectant les altérations."""
import hashlib, json
from django.db import transaction
from django.utils import timezone
from .models import Historique
class ServiceAudit:
    @staticmethod
    @transaction.atomic
    def enregistrer(action, utilisateur=None, projet=None, description="", donnees=None):
        dernier=Historique.objects.select_for_update().order_by("-date_action").first()
        precedent=(dernier.hash_evenement if dernier else "") or ""
        payload={"action":action,"utilisateur":str(getattr(utilisateur,"id","")),"projet":str(getattr(projet,"id","")),"description":description,"donnees":donnees or {},"horodatage":timezone.now().isoformat(),"precedent":precedent}
        empreinte=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
        return Historique.objects.create(utilisateur=utilisateur,projet_id=getattr(projet,"id",None),action=action,description=description,donnees={**(donnees or {}),"horodatage_serveur":payload["horodatage"]},hash_precedent=precedent,hash_evenement=empreinte)
    @staticmethod
    def verifier_integrite():
        precedent=""
        for h in Historique.objects.order_by("date_action"):
            if (h.hash_precedent or "") != precedent: return False, str(h.id)
            precedent=h.hash_evenement or ""
        return True, None
