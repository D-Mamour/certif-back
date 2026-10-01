"""API d'analyse intelligente."""
from rest_framework import viewsets,decorators
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from projets.views import projets_accessibles
from .models import Analyse,Anomalie,Recommandation
from .serializers import AnalyseSerializer,AnomalieSerializer,RecommandationSerializer
from .services.analyse import ServiceAnalyse

class AnalyseViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose et déclenche les analyses."""
    serializer_class=AnalyseSerializer
    def get_queryset(self):
        """Filtre les analyses par projets accessibles."""
        return Analyse.objects.filter(projet__in=projets_accessibles(self.request.user))
    @decorators.action(detail=False,methods=["post"])
    def lancer(self,request):
        """Lance règles métier et préparation RAG."""
        projet=get_object_or_404(projets_accessibles(request.user),pk=request.data.get("projet"))
        analyse,rag=ServiceAnalyse().analyser_projet(projet)
        return Response({"analyse":self.get_serializer(analyse).data,"rag":rag})

class AnomalieViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose les anomalies accessibles."""
    serializer_class=AnomalieSerializer
    def get_queryset(self):
        """Filtre par projet accessible."""
        return Anomalie.objects.filter(projet__in=projets_accessibles(self.request.user))

class RecommandationViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose les recommandations accessibles."""
    serializer_class=RecommandationSerializer
    def get_queryset(self):
        """Filtre par projet accessible."""
        return Recommandation.objects.filter(projet__in=projets_accessibles(self.request.user))

from rest_framework import permissions, status
from rest_framework.views import APIView
from .serializers_assistant import AssistantQuestionSerializer
from .services.rag import ServiceRAG


class AssistantChantialView(APIView):
    """Chatbot sécurisé : répond uniquement à partir d'un projet accessible."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Valide la question, contrôle le projet puis interroge le RAG."""
        serializer = AssistantQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        projets = projets_accessibles(request.user)
        projet_id = serializer.validated_data.get("projet")
        if projet_id:
            projet = get_object_or_404(projets, pk=projet_id)
        else:
            projet = projets.order_by("-date_creation").first()
            if projet is None:
                return Response(
                    {"detail": "Aucun projet accessible pour utiliser l'assistant."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        resultat = ServiceRAG().assister(
            projet=projet,
            question=serializer.validated_data["question"],
            utilisateur=request.user,
        )
        return Response(resultat)
