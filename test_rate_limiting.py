#!/usr/bin/env python3
"""
Script de test du Rate Limiting
Teste les limites de connexion et d'inscription
"""
import requests
import time
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://localhost:8000"

def test_login_rate_limit():
    """Test du rate limiting sur la connexion (5 tentatives max)"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 1: Rate Limiting sur la CONNEXION")
    print(f"{Fore.CYAN}Limite: 5 tentatives par IP toutes les 15 minutes")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    login_url = f"{BASE_URL}/comptes/login/"
    
    # Obtenir le CSRF token
    session = requests.Session()
    response = session.get(login_url)
    csrf_token = session.cookies.get('csrftoken')
    
    for i in range(1, 8):  # On teste jusqu'à 7 tentatives
        print(f"{Fore.YELLOW}Tentative {i}/7...")
        
        data = {
            'username': 'test@test.com',
            'password': 'wrongpassword',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(
            login_url,
            data=data,
            headers={'Referer': login_url}
        )
        
        if response.status_code == 429:
            print(f"{Fore.RED}❌ BLOQUÉ ! Rate limit atteint au bout de {i} tentatives")
            print(f"{Fore.GREEN}✅ Protection activée correctement!")
            return True
        elif response.status_code == 200:
            print(f"{Fore.YELLOW}   → Tentative {i} autorisée (code 200)")
        
        time.sleep(0.5)  # Petit délai entre les requêtes
    
    print(f"{Fore.RED}❌ ÉCHEC : Rate limit pas activé après 7 tentatives")
    return False


def test_register_rate_limit():
    """Test du rate limiting sur l'inscription (3 tentatives max)"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 2: Rate Limiting sur l'INSCRIPTION")
    print(f"{Fore.CYAN}Limite: 3 tentatives par IP toutes les 15 minutes")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    register_url = f"{BASE_URL}/comptes/register/"
    
    # Obtenir le CSRF token
    session = requests.Session()
    response = session.get(register_url)
    csrf_token = session.cookies.get('csrftoken')
    
    for i in range(1, 6):  # On teste jusqu'à 5 tentatives
        print(f"{Fore.YELLOW}Tentative {i}/5...")
        
        data = {
            'nom': 'Test',
            'prenom': 'User',
            'email': f'testuser{i}@test.com',  # Email différent à chaque fois
            'telephone': '771234567',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(
            register_url,
            data=data,
            headers={'Referer': register_url}
        )
        
        if response.status_code == 429:
            print(f"{Fore.RED}❌ BLOQUÉ ! Rate limit atteint au bout de {i} tentatives")
            print(f"{Fore.GREEN}✅ Protection activée correctement!")
            return True
        elif response.status_code == 200:
            print(f"{Fore.YELLOW}   → Tentative {i} autorisée (code 200)")
        
        time.sleep(0.5)
    
    print(f"{Fore.RED}❌ ÉCHEC : Rate limit pas activé après 5 tentatives")
    return False


def test_resend_email_rate_limit():
    """Test du rate limiting sur le renvoi d'email (2 tentatives max)"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}TEST 3: Rate Limiting sur le RENVOI D'EMAIL")
    print(f"{Fore.CYAN}Limite: 2 tentatives par IP toutes les 10 minutes")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    resend_url = f"{BASE_URL}/comptes/resend-verification/"
    
    # Obtenir le CSRF token
    session = requests.Session()
    response = session.get(f"{BASE_URL}/comptes/registration-pending/")
    csrf_token = session.cookies.get('csrftoken')
    
    for i in range(1, 5):  # On teste jusqu'à 4 tentatives
        print(f"{Fore.YELLOW}Tentative {i}/4...")
        
        data = {
            'email': 'test@example.com',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(
            resend_url,
            data=data,
            headers={'Referer': f"{BASE_URL}/comptes/registration-pending/"}
        )
        
        if response.status_code == 429:
            print(f"{Fore.RED}❌ BLOQUÉ ! Rate limit atteint au bout de {i} tentatives")
            print(f"{Fore.GREEN}✅ Protection activée correctement!")
            return True
        elif response.status_code == 200 or response.status_code == 302:
            print(f"{Fore.YELLOW}   → Tentative {i} autorisée (code {response.status_code})")
        
        time.sleep(0.5)
    
    print(f"{Fore.RED}❌ ÉCHEC : Rate limit pas activé après 4 tentatives")
    return False


if __name__ == "__main__":
    print(f"\n{Fore.GREEN}{Style.BRIGHT}{'='*60}")
    print(f"{Fore.GREEN}{Style.BRIGHT}🔒 TEST DU RATE LIMITING - SCINDONGO IMMO")
    print(f"{Fore.GREEN}{Style.BRIGHT}{'='*60}\n")
    
    results = []
    
    # Test 1: Connexion
    results.append(("Connexion", test_login_rate_limit()))
    time.sleep(2)
    
    # Test 2: Inscription
    results.append(("Inscription", test_register_rate_limit()))
    time.sleep(2)
    
    # Test 3: Renvoi email
    results.append(("Renvoi Email", test_resend_email_rate_limit()))
    
    # Résumé
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}RÉSUMÉ DES TESTS")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    for name, result in results:
        status = f"{Fore.GREEN}✅ RÉUSSI" if result else f"{Fore.RED}❌ ÉCHEC"
        print(f"{name:20} : {status}")
    
    total_passed = sum(1 for _, r in results if r)
    print(f"\n{Fore.CYAN}Score: {total_passed}/{len(results)} tests réussis\n")
    
    if total_passed == len(results):
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 Tous les tests de rate limiting fonctionnent !")
    else:
        print(f"{Fore.RED}{Style.BRIGHT}⚠️  Certains tests ont échoué, vérifiez la configuration.")
