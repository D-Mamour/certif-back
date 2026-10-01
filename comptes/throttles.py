"""Limites de débit dédiées aux points d'entrée exposés aux robots."""
from rest_framework.throttling import AnonRateThrottle

class ConnexionRateThrottle(AnonRateThrottle):
    """Freine les tentatives répétées de connexion."""
    scope = 'login'

class InscriptionRateThrottle(AnonRateThrottle):
    """Freine la création automatisée de comptes."""
    scope = 'register'
