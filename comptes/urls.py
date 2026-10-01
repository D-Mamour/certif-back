"""Routes d'authentification."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import InscriptionView, ConnexionView, ProfilView
urlpatterns = [
    path("inscription/",InscriptionView.as_view()),
    path("connexion/",ConnexionView.as_view()),
    path("rafraichir/",TokenRefreshView.as_view()),
    path("profil/",ProfilView.as_view()),
]
