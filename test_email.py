#!/usr/bin/env python
"""
Script de test pour vérifier la configuration SMTP
Usage: docker-compose exec web python test_email.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scindongo_immo.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    """Envoyer un email de test"""
    print("\n" + "="*60)
    print("🧪 TEST CONFIGURATION EMAIL SMTP")
    print("="*60)
    
    print("\n📋 Configuration actuelle :")
    print(f"  • Backend : {settings.EMAIL_BACKEND}")
    print(f"  • Host    : {settings.EMAIL_HOST}")
    print(f"  • Port    : {settings.EMAIL_PORT}")
    print(f"  • TLS     : {settings.EMAIL_USE_TLS}")
    print(f"  • User    : {settings.EMAIL_HOST_USER}")
    print(f"  • From    : {settings.DEFAULT_FROM_EMAIL}")
    
    # Demander l'email de destination
    destination = input("\n✉️  Entrez l'adresse email de destination : ").strip()
    
    if not destination:
        print("❌ Email de destination requis !")
        return
    
    print(f"\n📤 Envoi d'un email de test à : {destination}")
    print("⏳ Patientez...")
    
    try:
        result = send_mail(
            subject='🧪 Test SMTP - SCINDONGO Immo',
            message='Ceci est un email de test pour vérifier la configuration SMTP.\n\n'
                   'Si vous recevez cet email, la configuration est correcte ! ✅\n\n'
                   f'Backend : {settings.EMAIL_BACKEND}\n'
                   f'Host : {settings.EMAIL_HOST}\n'
                   f'Port : {settings.EMAIL_PORT}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destination],
            fail_silently=False,
        )
        
        if result == 1:
            print("\n" + "="*60)
            print("✅ EMAIL ENVOYÉ AVEC SUCCÈS !")
            print("="*60)
            print(f"\n📬 Vérifiez votre boîte mail : {destination}")
            print("💡 N'oubliez pas de vérifier le dossier Spam/Courrier indésirable")
            print("\n" + "="*60)
        else:
            print("\n❌ Échec de l'envoi (aucune exception levée)")
            
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERREUR LORS DE L'ENVOI")
        print("="*60)
        print(f"\nType d'erreur : {type(e).__name__}")
        print(f"Message : {str(e)}")
        print("\n📋 Solutions possibles :")
        print("  1. Vérifiez EMAIL_HOST_USER et EMAIL_HOST_PASSWORD dans .env")
        print("  2. Assurez-vous d'utiliser un mot de passe d'application Gmail")
        print("  3. Vérifiez que la validation en 2 étapes est activée")
        print("  4. Redémarrez Docker : docker-compose down && docker-compose up")
        print("\n" + "="*60)

if __name__ == '__main__':
    test_email()
