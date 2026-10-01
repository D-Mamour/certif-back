"""Tests de base de l'application finances."""
from django.test import TestCase

class TestsFinances(TestCase):
    """Point d'entrée des tests métier de l'application finances."""
    def test_configuration(self):
        """Vérifie que le module de tests est chargé correctement."""
        self.assertTrue(True)
