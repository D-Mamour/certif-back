from django.core.management.base import BaseCommand
from django.utils import timezone
from projets.models import Projet
from rapports.services import archiver_rapport, envoyer_email_rapport, envoyer_whatsapp_rapport
from audit.services import ServiceAudit
class Command(BaseCommand):
    help='Génère et diffuse les rapports Chantial du mois précédent.'
    def add_arguments(self,p): p.add_argument('--periode',help='AAAA-MM'); p.add_argument('--sans-whatsapp',action='store_true')
    def handle(self,*args,**opts):
        now=timezone.localdate(); periode=opts.get('periode') or (f"{now.year-1}-12" if now.month==1 else f"{now.year}-{now.month-1:02d}")
        for projet in Projet.objects.select_related('bailleur').all():
            rapport,contenu=archiver_rapport(projet,periode)
            try: ok_email,msg_email=envoyer_email_rapport(projet,rapport,contenu)
            except Exception as e: ok_email,msg_email=False,str(e)
            ok_wa,msg_wa=(False,'désactivé') if opts['sans_whatsapp'] else envoyer_whatsapp_rapport(projet,rapport)
            ServiceAudit.enregistrer('RAPPORT_MENSUEL_DIFFUSE',None,projet,f'Rapport {periode}',{'email':ok_email,'whatsapp':ok_wa})
            self.stdout.write(f'{projet.nom}: {msg_email}; {msg_wa}')
