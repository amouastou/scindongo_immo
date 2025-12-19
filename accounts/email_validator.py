"""
Validation avancée des emails avant envoi.
"""
import smtplib
import dns.resolver
import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_email_domain(email):
    """
    Vérifie que le domaine de l'email a un enregistrement MX (serveur mail).
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    try:
        # Validation du format de base
        validate_email(email)
        
        # Extraire le domaine
        domain = email.split('@')[1]
        
        # Vérifier l'enregistrement MX
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                logger.warning(f"Domaine {domain} n'a pas d'enregistrement MX")
                return False, "domaine_sans_mx"
            
            logger.info(f"Domaine {domain} valide avec {len(mx_records)} serveurs MX")
            return True, None
            
        except dns.resolver.NXDOMAIN:
            # Domaine n'existe pas
            logger.warning(f"Domaine {domain} n'existe pas (NXDOMAIN)")
            return False, "domaine_inexistant"
            
        except dns.resolver.NoAnswer:
            # Pas de réponse MX (domaine existe mais pas de serveur mail)
            logger.warning(f"Domaine {domain} n'a pas de serveur mail (NoAnswer)")
            return False, "domaine_sans_mx"
            
        except dns.resolver.Timeout:
            # Timeout DNS - on laisse passer (évite les faux négatifs)
            logger.warning(f"Timeout DNS pour {domain}, email accepté par défaut")
            return True, None
            
        except Exception as e:
            # Autre erreur DNS - on laisse passer
            logger.error(f"Erreur DNS pour {domain}: {e}")
            return True, None
        
    except ValidationError:
        # Format email invalide
        return False, "format_invalide"
    
    except IndexError:
        # Pas de @
        return False, "format_invalide"
    
    except Exception as e:
        # Erreur inattendue - on laisse passer
        logger.error(f"Erreur validation email {email}: {e}")
        return True, None


def verify_email_smtp(email):
    """
    Vérifie si une adresse email spécifique existe en utilisant SMTP RCPT TO.
    Cette méthode se connecte au serveur mail du domaine et vérifie si l'adresse existe.
    
    Args:
        email (str): L'adresse email à vérifier
        
    Returns:
        tuple: (exists: bool, error_code: str or None)
        
    Error codes:
        - "email_inexistant": L'adresse email n'existe pas
        - "domaine_non_verifiable": Le domaine bloque les vérifications SMTP
        - None: L'email existe ou vérification non concluante
        
    Note:
        Certains serveurs désactivent la vérification SMTP pour des raisons de sécurité.
        Les domaines connus pour bloquer sont rejetés par défaut.
    """
    domain = email.split('@')[1]
    
    # Liste des domaines qui bloquent activement la vérification SMTP
    # Ces domaines coupent la connexion sans répondre
    BLOCKED_DOMAINS = [
        'mail.com', 'email.com', 'usa.com', 'myself.com',  # Réseau mail.com
        'hotmail.com', 'outlook.com', 'live.com',  # Microsoft
        'icloud.com', 'me.com', 'mac.com',  # Apple
    ]
    
    # Si le domaine est dans la liste bloquée, on rejette
    if domain.lower() in BLOCKED_DOMAINS:
        logger.warning(f"Domaine {domain} dans la liste des domaines non vérifiables")
        return False, "domaine_non_verifiable"
    
    try:
        # Obtenir le serveur MX du domaine
        mx_records = dns.resolver.resolve(domain, 'MX', lifetime=3)  # Timeout DNS 3s
        # Trier par priorité (plus petit = prioritaire)
        mx_records = sorted(mx_records, key=lambda x: x.preference)
        mx_host = str(mx_records[0].exchange).rstrip('.')
        
        logger.info(f"Vérification SMTP de {email} via {mx_host}")
        
        # Se connecter au serveur SMTP avec timeout réduit
        server = smtplib.SMTP(timeout=5)  # Réduit de 10s à 5s
        server.set_debuglevel(0)
        server.connect(mx_host)
        server.helo('scindongo-immo.com')
        
        # Définir l'expéditeur
        server.mail('noreply@scindongo-immo.com')
        
        # Vérifier le destinataire avec RCPT TO
        code, message = server.rcpt(email)
        server.quit()
        
        logger.info(f"SMTP code {code} pour {email}: {message.decode()}")
        
        # Codes SMTP standards
        if code == 250:
            # 250 = Adresse acceptée
            return True, None
        elif code in [550, 551, 553]:
            # 550 = Adresse n'existe pas
            # 551 = Utilisateur pas sur ce serveur
            # 553 = Adresse non autorisée
            logger.warning(f"Email {email} n'existe pas (code {code})")
            return False, "email_inexistant"
        elif code in [450, 451, 452]:
            # Erreurs temporaires - on laisse passer
            logger.warning(f"Erreur temporaire pour {email} (code {code})")
            return True, None
        else:
            # Autres codes - bénéfice du doute
            logger.warning(f"Code SMTP inconnu {code} pour {email}")
            return True, None
            
    except smtplib.SMTPServerDisconnected:
        # Serveur a coupé la connexion - certains serveurs bloquent VRFY
        logger.warning(f"Serveur {mx_host} a refusé la vérification SMTP pour {email}")
        return True, None  # Bénéfice du doute
        
    except smtplib.SMTPConnectError:
        logger.error(f"Impossible de se connecter à {mx_host}")
        return True, None  # Bénéfice du doute
        
    except Exception as e:
        logger.error(f"Erreur SMTP pour {email}: {e}")
        return True, None  # Bénéfice du doute
        
    finally:
        try:
            server.quit()
        except:
            pass
