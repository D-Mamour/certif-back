"""Tests de base de l'application intelligence."""
from django.test import TestCase

class TestsIntelligence(TestCase):
    """Point d'entrée des tests métier de l'application intelligence."""
    def test_configuration(self):
        """Vérifie que le module de tests est chargé correctement."""
        self.assertTrue(True)
