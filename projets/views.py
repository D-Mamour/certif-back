"""API des projets, étapes et avancements."""
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from comptes.models import Utilisateur
from .models import Projet,Etape,Avancement
from .serializers import ProjetSerializer,EtapeSerializer,AvancementSerializer

def projets_accessibles(utilisateur):
    """Construit le queryset des projets visibles selon le rôle."""
    if utilisateur.role==Utilisateur.Role.ENTREPRENEUR:
        return Projet.objects.filter(entrepreneur=utilisateur)
    if utilisateur.role==Utilisateur.Role.BAILLEUR:
        return Projet.objects.filter(bailleur=utilisateur)
    return Projet.objects.all()

class ProjetViewSet(viewsets.ModelViewSet):
    """CRUD des projets avec isolation des données."""
    serializer_class=ProjetSerializer
    def get_queryset(self):
        """Retourne les projets autorisés."""
        return projets_accessibles(self.request.user)
    def perform_create(self,serializer):
        """Crée un projet uniquement pour un entrepreneur et vérifie le bailleur."""
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR:
            raise PermissionDenied("Seul un entrepreneur peut créer un projet.")
        bailleur = serializer.validated_data.get("bailleur")
        if not bailleur or bailleur.role != Utilisateur.Role.BAILLEUR or bailleur.statut != Utilisateur.Statut.ACTIF:
            raise ValidationError({"bailleur":"Sélectionnez un bailleur actif."})
        serializer.save(entrepreneur=self.request.user)
    def perform_update(self, serializer):
        projet = self.get_object()
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        serializer.save()
    def perform_destroy(self, instance):
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or instance.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        instance.delete()

class EtapeViewSet(viewsets.ModelViewSet):
    """CRUD des étapes accessibles."""
    serializer_class=EtapeSerializer
    def get_queryset(self):
        """Filtre les étapes par projet accessible."""
        return Etape.objects.filter(projet__in=projets_accessibles(self.request.user))
    def perform_create(self, serializer):
        """Réserve la déclaration des étapes à l'entrepreneur propriétaire."""
        projet=serializer.validated_data.get("projet")
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        serializer.save()
    def perform_update(self, serializer):
        etape = self.get_object()
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or etape.projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        serializer.save()
    def perform_destroy(self, instance):
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or instance.projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        instance.delete()

class AvancementViewSet(viewsets.ModelViewSet):
    """CRUD de l'historique d'avancement."""
    serializer_class=AvancementSerializer
    def get_queryset(self):
        """Filtre les avancements par projet accessible."""
        return Avancement.objects.filter(etape__projet__in=projets_accessibles(self.request.user))
    def perform_create(self,serializer):
        """Enregistre l'entrepreneur propriétaire comme auteur."""
        etape=serializer.validated_data.get("etape")
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or etape.projet.entrepreneur_id != self.request.user.id:
            raise PermissionDenied("Action réservée à l'entrepreneur du projet.")
        serializer.save(auteur=self.request.user)

from rest_framework import decorators, status
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
from .models import Avenant, JournalChantier
from .serializers import AvenantSerializer, JournalChantierSerializer
from .services import decider_avenant, hacher_preuve
from audit.services import ServiceAudit
from rapports.services import generer_rapport_pdf
from intelligence.services.controle_financier import ServiceControleFinancier

class AvenantViewSet(viewsets.ModelViewSet):
    serializer_class=AvenantSerializer
    def get_queryset(self): return Avenant.objects.filter(projet__in=projets_accessibles(self.request.user))
    def perform_create(self,serializer):
        projet=serializer.validated_data['projet']
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or projet.entrepreneur_id != self.request.user.id: raise PermissionDenied('Action réservée à l’entrepreneur du projet.')
        obj=serializer.save(auteur=self.request.user)
        ServiceAudit.enregistrer('AVENANT_CREE',self.request.user,projet,'Avenant créé',{'avenant':str(obj.id),'montant':str(obj.montant)})
    @decorators.action(detail=True,methods=['post'])
    def soumettre(self,request,pk=None):
        a=self.get_object()
        if request.user != a.projet.entrepreneur: raise PermissionDenied('Action réservée à l’entrepreneur.')
        a.statut='SOUMIS'; a.save(update_fields=['statut']); ServiceAudit.enregistrer('AVENANT_SOUMIS',request.user,a.projet,'Avenant soumis',{'avenant':str(a.id)}); return Response(self.get_serializer(a).data)
    @decorators.action(detail=True,methods=['post'])
    def approuver(self,request,pk=None):
        a=self.get_object()
        if request.user != a.projet.bailleur: raise PermissionDenied('Action réservée au bailleur.')
        if a.statut!='SOUMIS': return Response({'detail':'Seul un avenant soumis peut être approuvé.'},status=400)
        return Response(self.get_serializer(decider_avenant(a,request.user,True,request.data.get('commentaire',''))).data)
    @decorators.action(detail=True,methods=['post'])
    def rejeter(self,request,pk=None):
        a=self.get_object()
        if request.user != a.projet.bailleur: raise PermissionDenied('Action réservée au bailleur.')
        return Response(self.get_serializer(decider_avenant(a,request.user,False,request.data.get('commentaire',''))).data)

class JournalChantierViewSet(viewsets.ModelViewSet):
    serializer_class=JournalChantierSerializer
    def get_queryset(self): return JournalChantier.objects.filter(projet__in=projets_accessibles(self.request.user))
    def perform_create(self,serializer):
        projet=serializer.validated_data['projet']
        if self.request.user.role != Utilisateur.Role.ENTREPRENEUR or projet.entrepreneur_id != self.request.user.id: raise PermissionDenied('Action réservée à l’entrepreneur du projet.')
        preuve=serializer.save(auteur=self.request.user); hacher_preuve(preuve)
        try:
            from intelligence.services.vision import ServiceVisionChantier
            preuve.analyse_visuelle=ServiceVisionChantier().analyser(preuve); preuve.save(update_fields=['analyse_visuelle'])
        except Exception as exc:
            preuve.analyse_visuelle={'statut':'INDISPONIBLE','message':str(exc)}; preuve.save(update_fields=['analyse_visuelle'])
        ServiceAudit.enregistrer('PREUVE_TERRAIN_AJOUTEE',self.request.user,projet,'Preuve terrain ajoutée',{'preuve':str(preuve.id),'hash':preuve.hash_fichier})

class PilotageProjetViewSet(viewsets.ViewSet):
    @decorators.action(detail=True,methods=['get'],url_path='indicateurs-financiers')
    def indicateurs(self,request,pk=None):
        projet=Projet.objects.filter(pk=pk).filter(pk__in=projets_accessibles(request.user)).first()
        if not projet: return Response({'detail':'Projet introuvable.'},status=404)
        d=ServiceControleFinancier().indicateurs_evm(projet); return Response({k:(str(v) if v is not None else None) for k,v in d.items()})
    @decorators.action(detail=True,methods=['get'],url_path='rapport-pdf')
    def rapport(self,request,pk=None):
        projet=Projet.objects.filter(pk=pk).filter(pk__in=projets_accessibles(request.user)).first()
        if not projet: return Response({'detail':'Projet introuvable.'},status=404)
        contenu=generer_rapport_pdf(projet); ServiceAudit.enregistrer('RAPPORT_PDF_GENERE',request.user,projet,'Rapport chantier généré')
        rep=HttpResponse(contenu,content_type='application/pdf'); rep['Content-Disposition']=f'attachment; filename="rapport-chantial-{projet.id}.pdf"'; return rep
    @decorators.action(detail=True,methods=['post'],url_path='diffuser-rapport')
    def diffuser_rapport(self,request,pk=None):
        projet=Projet.objects.filter(pk=pk).filter(pk__in=projets_accessibles(request.user)).first()
        if not projet: return Response({'detail':'Projet introuvable.'},status=404)
        periode=request.data.get('periode') or timezone.localdate().strftime('%Y-%m')
        rapport,contenu=archiver_rapport(projet,periode,request.user)
        result={'rapport':str(rapport.id),'periode':periode}
        if request.data.get('email',True):
            try: result['email']=envoyer_email_rapport(projet,rapport,contenu)
            except Exception as exc: result['email']=(False,str(exc))
        if request.data.get('whatsapp',False): result['whatsapp']=envoyer_whatsapp_rapport(projet,rapport)
        ServiceAudit.enregistrer('RAPPORT_DIFFUSE',request.user,projet,'Rapport diffusé',result)
        return Response(result)

from .models import RapportChantier
from .serializers import RapportChantierSerializer
from rapports.services import archiver_rapport, envoyer_email_rapport, envoyer_whatsapp_rapport
class RapportChantierViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=RapportChantierSerializer
    def get_queryset(self): return RapportChantier.objects.filter(projet__in=projets_accessibles(self.request.user))


from .models import SituationTravaux
from .serializers import SituationTravauxSerializer
class SituationTravauxViewSet(viewsets.ModelViewSet):
    serializer_class=SituationTravauxSerializer
    def get_queryset(self): return SituationTravaux.objects.filter(projet__in=projets_accessibles(self.request.user))
    def perform_create(self,serializer):
        projet=serializer.validated_data['projet']; etape=serializer.validated_data['etape']
        if self.request.user != projet.entrepreneur or etape.projet_id != projet.id: raise PermissionDenied('Situation invalide ou accès refusé.')
        obj=serializer.save(auteur=self.request.user)
        ServiceAudit.enregistrer('SITUATION_TRAVAUX_SOUMISE',self.request.user,projet,'Situation de travaux soumise',{'situation':str(obj.id),'etape':str(etape.id),'pourcentage':str(obj.pourcentage),'montant':str(obj.montant_situation)})
    @decorators.action(detail=True,methods=['post'])
    def valider(self,request,pk=None): return self._decider(request,True)
    @decorators.action(detail=True,methods=['post'])
    def rejeter(self,request,pk=None): return self._decider(request,False)
    def _decider(self,request,valider):
        obj=self.get_object()
        if request.user != obj.projet.bailleur: raise PermissionDenied('Action réservée au bailleur.')
        if obj.statut!='SOUMISE': return Response({'detail':'Cette situation a déjà été décidée.'},status=400)
        obj.statut='VALIDEE' if valider else 'REJETEE'; obj.decide_par=request.user; obj.commentaire_decision=request.data.get('commentaire',''); obj.date_decision=timezone.now(); obj.save(update_fields=['statut','decide_par','commentaire_decision','date_decision'])
        ServiceAudit.enregistrer('SITUATION_TRAVAUX_'+obj.statut,request.user,obj.projet,'Décision sur situation de travaux',{'situation':str(obj.id),'statut':obj.statut,'pourcentage':str(obj.pourcentage),'montant':str(obj.montant_situation)})
        return Response(self.get_serializer(obj).data)
