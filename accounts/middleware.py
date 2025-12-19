"""
Middleware pour gérer le Rate Limiting
Capture l'exception Ratelimited et affiche une page d'erreur personnalisée
"""
from django.shortcuts import render
from django_ratelimit.exceptions import Ratelimited


class RateLimitMiddleware:
    """
    Middleware qui capture les exceptions de rate limiting
    et affiche une page d'erreur conviviale au lieu d'une 403
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Intercepte les exceptions Ratelimited"""
        if isinstance(exception, Ratelimited):
            # Logger l'événement pour détecter les attaques potentielles
            from core.utils import audit_log
            audit_log(
                request.user if request.user.is_authenticated else None,
                None,
                "rate_limit_exceeded",
                {
                    "path": request.path,
                    "method": request.method,
                },
                request,
                categorie="security",
                resultat="blocked"
            )
            
            # Afficher la page d'erreur personnalisée
            return render(
                request,
                'accounts/rate_limited.html',
                status=429  # HTTP 429 Too Many Requests
            )
        
        return None
