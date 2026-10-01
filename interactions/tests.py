"""Tests de base de l'application interactions."""
from django.test import TestCase

class TestsInteractions(TestCase):
    """Point d'entrée des tests métier de l'application interactions."""
    def test_configuration(self):
        """Vérifie que le module de tests est chargé correctement."""
        self.assertTrue(True)
