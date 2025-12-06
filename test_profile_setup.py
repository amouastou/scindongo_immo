#!/usr/bin/env python
"""
Test complet du système de profil et téléphone
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scindongo_immo.settings')
django.setup()

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from accounts.forms import ClientProfileForm, RegisterForm, UserManagementForm, ClientChangePasswordForm
from accounts.models import Role
from django.urls import reverse

User = get_user_model()

def test_user_telephone_field():
    """Test que le champ telephone existe dans User"""
    print("\n" + "="*60)
    print("TEST 1: Champ téléphone dans le modèle User")
    print("="*60)
    
    user = User.objects.create_user(
        username='test_telephone@example.com',
        email='test_telephone@example.com',
        password='TestPass123!',
        first_name='Jean',
        last_name='Dupont',
        telephone='+221 77 123 4567'
    )
    
    assert hasattr(user, 'telephone'), "Le champ telephone n'existe pas"
    assert user.telephone == '+221 77 123 4567', "La valeur du telephone n'est pas correcte"
    
    print("✅ Le champ telephone existe et fonctionne")
    user.delete()

def test_forms_have_telephone():
    """Test que tous les formulaires ont le champ telephone"""
    print("\n" + "="*60)
    print("TEST 2: Champ téléphone dans les formulaires")
    print("="*60)
    
    # ClientProfileForm
    form = ClientProfileForm()
    assert 'telephone' in form.fields, "Telephone manquant dans ClientProfileForm"
    print("✅ ClientProfileForm contient le champ telephone")
    
    # RegisterForm
    form = RegisterForm()
    assert 'telephone' in form.fields, "Telephone manquant dans RegisterForm"
    print("✅ RegisterForm contient le champ telephone")
    
    # UserManagementForm
    form = UserManagementForm()
    assert 'telephone' in form.fields, "Telephone manquant dans UserManagementForm"
    print("✅ UserManagementForm contient le champ telephone")
    
    # ClientChangePasswordForm
    user = User.objects.create_user(
        username='test_pwd@example.com',
        email='test_pwd@example.com',
        password='OldPass123!'
    )
    form = ClientChangePasswordForm(user)
    assert 'old_password' in form.fields, "old_password manquant"
    print("✅ ClientChangePasswordForm est correcte")
    user.delete()

def test_views_exist():
    """Test que les vues existent"""
    print("\n" + "="*60)
    print("TEST 3: Vues de profil et changement de mot de passe")
    print("="*60)
    
    from accounts.views import ClientProfileUpdateView, ClientChangePasswordView
    
    assert hasattr(ClientProfileUpdateView, 'model'), "ClientProfileUpdateView sans model"
    assert hasattr(ClientProfileUpdateView, 'form_class'), "ClientProfileUpdateView sans form_class"
    print("✅ ClientProfileUpdateView existe et est configurée")
    
    assert hasattr(ClientChangePasswordView, 'form_class'), "ClientChangePasswordView sans form_class"
    print("✅ ClientChangePasswordView existe et est configurée")

def test_urls_exist():
    """Test que les URLs existent"""
    print("\n" + "="*60)
    print("TEST 4: URLs de profil")
    print("="*60)
    
    try:
        url = reverse('edit_profile')
        assert url == '/auth/profil/modifier/', f"URL incorrecte: {url}"
        print(f"✅ edit_profile URL: {url}")
    except Exception as e:
        print(f"❌ edit_profile: {e}")
        raise
    
    try:
        url = reverse('change_password')
        assert url == '/auth/profil/changer-mot-de-passe/', f"URL incorrecte: {url}"
        print(f"✅ change_password URL: {url}")
    except Exception as e:
        print(f"❌ change_password: {e}")
        raise

def test_profile_form_save():
    """Test que le formulaire de profil sauvegarde correctement"""
    print("\n" + "="*60)
    print("TEST 5: Sauvegarde du formulaire de profil")
    print("="*60)
    
    user = User.objects.create_user(
        username='test_form@example.com',
        email='test_form@example.com',
        password='TestPass123!',
        first_name='Jean',
        last_name='Dupont'
    )
    
    form_data = {
        'first_name': 'Jean-Pierre',
        'last_name': 'Martin',
        'telephone': '+221 77 999 8888'
    }
    
    form = ClientProfileForm(form_data, instance=user)
    assert form.is_valid(), f"Formulaire invalide: {form.errors}"
    form.save()
    
    user.refresh_from_db()
    assert user.first_name == 'Jean-Pierre', "first_name non mis à jour"
    assert user.last_name == 'Martin', "last_name non mis à jour"
    assert user.telephone == '+221 77 999 8888', "telephone non mis à jour"
    
    print("✅ Le formulaire sauvegarde correctement")
    user.delete()

def test_admin_has_telephone():
    """Test que l'admin Django a le champ telephone"""
    print("\n" + "="*60)
    print("TEST 6: Django Admin avec telephone")
    print("="*60)
    
    from accounts.admin import UserAdmin
    from django.contrib import admin
    
    # Vérifier que UserAdmin a les bons fieldsets
    fieldsets_str = str(UserAdmin.fieldsets)
    assert 'telephone' in fieldsets_str, "telephone manquant dans les fieldsets"
    print("✅ Django Admin contient le champ telephone")
    
    # Vérifier list_display
    assert 'telephone' in UserAdmin.list_display, "telephone manquant dans list_display"
    print("✅ telephone visible dans la liste des utilisateurs")

def test_register_form_with_telephone():
    """Test l'inscription avec téléphone"""
    print("\n" + "="*60)
    print("TEST 7: Inscription avec téléphone")
    print("="*60)
    
    form_data = {
        'email': 'newuser@example.com',
        'first_name': 'Alice',
        'last_name': 'Wonder',
        'telephone': '+221 77 111 2222',
        'password1': 'SecurePass123!',
        'password2': 'SecurePass123!'
    }
    
    form = RegisterForm(form_data)
    assert form.is_valid(), f"Formulaire d'inscription invalide: {form.errors}"
    user = form.save()
    
    assert user.telephone == '+221 77 111 2222', "telephone non sauvegardé"
    print("✅ L'inscription avec téléphone fonctionne")
    user.delete()

if __name__ == '__main__':
    print("\n" + "🧪 "*30)
    print("SUITE DE TESTS COMPLETS - SYSTÈME DE PROFIL ET TÉLÉPHONE")
    print("🧪 "*30)
    
    try:
        test_user_telephone_field()
        test_forms_have_telephone()
        test_views_exist()
        test_urls_exist()
        test_profile_form_save()
        test_admin_has_telephone()
        test_register_form_with_telephone()
        
        print("\n" + "="*60)
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS !")
        print("="*60)
        print("\n🎉 Le système de profil et téléphone fonctionne parfaitement !\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST ÉCHOUÉ: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
