"""Routes de l'application projets."""
from rest_framework.routers import DefaultRouter
from .views import (ProjetViewSet, EtapeViewSet, AvancementViewSet, AvenantViewSet,
                    JournalChantierViewSet, PilotageProjetViewSet, RapportChantierViewSet,
                    SituationTravauxViewSet)
router=DefaultRouter()
router.register(r"projets",ProjetViewSet,basename="projets")
router.register(r"etapes",EtapeViewSet,basename="etapes")
router.register(r"avancements",AvancementViewSet,basename="avancements")
router.register(r"avenants",AvenantViewSet,basename="avenants")
router.register(r"journal-chantier",JournalChantierViewSet,basename="journal-chantier")
router.register(r"pilotage",PilotageProjetViewSet,basename="pilotage")
router.register(r"rapports",RapportChantierViewSet,basename="rapports")
router.register(r"situations-travaux",SituationTravauxViewSet,basename="situations-travaux")
urlpatterns=router.urls
