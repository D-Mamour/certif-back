"""En-têtes défensifs communs à toutes les réponses HTTP de Chantial."""

class SecurityHeadersMiddleware:
    """Ajoute des en-têtes simples de durcissement sans dépendance externe.

    La CSP doit être adaptée au domaine final si des ressources tierces sont ajoutées.
    """
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        return response
