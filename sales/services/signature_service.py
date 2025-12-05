"""
Service pour gérer la génération et vérification des OTP de signature de contrat.

Ce service gère:
- Génération des codes OTP (6 chiffres)
- Stockage en cache Django (expiration 5 minutes)
- Vérification avec rate limiting (3 tentatives max, 15 min de blocage)
- Gestion du cache pour OTP, tentatives et blocages
"""

import random
import string
from django.core.cache import cache
from django.utils import timezone


class SignatureService:
    """Service pour la gestion des OTP de contrat."""
    
    OTP_EXPIRY = 300  # 5 minutes
    OTP_MAX_ATTEMPTS = 3
    OTP_BLOCK_DURATION = 900  # 15 minutes
    
    @staticmethod
    def generate_otp(contrat):
        """
        Générer un OTP 6 chiffres et le stocker en cache.
        
        Args:
            contrat: Instance du modèle Contrat
            
        Returns:
            str: OTP généré (6 chiffres)
        """
        # Générer 6 chiffres aléatoires
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Stocker en cache avec expiration 5 minutes
        cache_key = f'otp_{contrat.id}'
        cache.set(cache_key, otp, SignatureService.OTP_EXPIRY)
        
        return otp
    
    @staticmethod
    def otp_exists(contrat):
        """
        Vérifier si un OTP existe et est valide en cache.
        
        Args:
            contrat: Instance du modèle Contrat
            
        Returns:
            bool: True si OTP existe, False sinon
        """
        cache_key = f'otp_{contrat.id}'
        return cache.get(cache_key) is not None
    
    @staticmethod
    def get_otp_remaining_time(contrat):
        """
        Obtenir le temps restant (en secondes) avant expiration de l'OTP.
        
        Args:
            contrat: Instance du modèle Contrat
            
        Returns:
            int or None: Secondes restantes, None si OTP n'existe pas
        """
        cache_key = f'otp_{contrat.id}'
        
        # Vérifier si OTP existe
        if cache.get(cache_key) is None:
            return None
        
        # Avec Redis (django-redis), on peut obtenir le TTL réel
        try:
            # django-redis expose ttl() sur le backend
            ttl = cache.ttl(cache_key)
            if ttl is not None and ttl > 0:
                return ttl
            else:
                return 300  # Fallback si TTL non disponible
        except (AttributeError, NotImplementedError):
            # Fallback si cache ne supporte pas ttl()
            return 300
    
    @staticmethod
    def verify_otp(contrat, otp_provided):
        """
        Vérifier l'OTP fourni avec rate limiting.
        
        Args:
            contrat: Instance du modèle Contrat
            otp_provided: OTP fourni par l'utilisateur (string)
            
        Returns:
            tuple: (bool: valide, str: message)
        """
        cache_key = f'otp_{contrat.id}'
        attempts_key = f'otp_attempts_{contrat.id}'
        blocked_key = f'otp_blocked_{contrat.id}'
        
        # Vérifier si contrat est bloqué
        if cache.get(blocked_key):
            return (False, 'Bloqué - trop de tentatives (15 min)')
        
        # Récupérer OTP stocké
        otp_stored = cache.get(cache_key)
        
        if otp_stored is None:
            return (False, 'OTP expiré')
        
        # Vérifier l'OTP
        if otp_provided != otp_stored:
            # Incrémenter les tentatives
            attempts = cache.get(attempts_key) or 0
            attempts += 1
            cache.set(attempts_key, attempts, SignatureService.OTP_BLOCK_DURATION)
            
            # Vérifier si on dépasse le max
            if attempts >= SignatureService.OTP_MAX_ATTEMPTS:
                # Bloquer le contrat
                cache.set(blocked_key, True, SignatureService.OTP_BLOCK_DURATION)
                # Supprimer l'OTP
                cache.delete(cache_key)
                return (False, f'Bloqué - trop de tentatives (max {SignatureService.OTP_MAX_ATTEMPTS})')
            
            return (False, f'OTP incorrect ({attempts}/{SignatureService.OTP_MAX_ATTEMPTS})')
        
        # OTP correct - supprimer OTP et compteur
        cache.delete(cache_key)
        cache.delete(attempts_key)
        
        return (True, 'OTP valide')
    
    @staticmethod
    def is_contrat_blocked(contrat):
        """
        Vérifier si le contrat est bloqué après trop de tentatives.
        
        Args:
            contrat: Instance du modèle Contrat
            
        Returns:
            bool: True si bloqué, False sinon
        """
        blocked_key = f'otp_blocked_{contrat.id}'
        return cache.get(blocked_key) is not None
    
    @staticmethod
    def reset_otp_attempts(contrat):
        """
        Réinitialiser les tentatives et déverrouiller le contrat.
        
        Args:
            contrat: Instance du modèle Contrat
        """
        attempts_key = f'otp_attempts_{contrat.id}'
        blocked_key = f'otp_blocked_{contrat.id}'
        
        cache.delete(attempts_key)
        cache.delete(blocked_key)
    
    @staticmethod
    def get_otp(contrat):
        """
        Récupérer l'OTP actuel du contrat (si existe).
        
        Args:
            contrat: Instance du modèle Contrat
            
        Returns:
            str or None: OTP actuel ou None
        """
        cache_key = f'otp_{contrat.id}'
        return cache.get(cache_key)
