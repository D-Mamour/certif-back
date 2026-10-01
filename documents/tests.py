"""Tests de base de l'application documents."""
from django.test import TestCase

class TestsDocuments(TestCase):
    """Point d'entrée des tests métier de l'application documents."""
    def test_configuration(self):
        """Vérifie que le module de tests est chargé correctement."""
        self.assertTrue(True)
