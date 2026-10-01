"""Tests de base de l'application projets."""
from django.test import TestCase

class TestsProjets(TestCase):
    """Point d'entrée des tests métier de l'application projets."""
    def test_configuration(self):
        """Vérifie que le module de tests est chargé correctement."""
        self.assertTrue(True)
