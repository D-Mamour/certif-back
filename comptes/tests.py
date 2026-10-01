"""Tests essentiels de l'authentification."""
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Utilisateur

class TestsAuthentification(TestCase):
    """Vérifie les scénarios critiques des comptes."""
    def setUp(self):
        """Prépare le client API."""
        self.client=APIClient()

    def test_creation_utilisateur(self):
        """Vérifie le hachage du mot de passe."""
        u=Utilisateur.objects.create_user(email="entrepreneur@test.sn",password="Demo12345!",
            role=Utilisateur.Role.ENTREPRENEUR)
        self.assertTrue(u.check_password("Demo12345!"))
