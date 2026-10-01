"""Tests de base de l'application audit."""
from django.test import TestCase

class TestsAudit(TestCase):
    """Point d'entrée des tests métier de l'application audit."""
    def test_configuration(self):
        """Vérifie que le module de tests est chargé correctement."""
        self.assertTrue(True)
