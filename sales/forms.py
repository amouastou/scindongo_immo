from django import forms
from .models import Reservation, Paiement, Client, Financement, Contrat


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['acompte']


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['montant', 'moyen', 'source']


class ClientForm(forms.ModelForm):
    """Formulaire pour créer/modifier un client"""
    class Meta:
        model = Client
        fields = ['nom', 'prenom', 'telephone', 'email', 'kyc_statut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+221 77 XXX XX XX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'kyc_statut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'KYC Statut (vérifiée, en attente, etc)'}),
        }


class FinancementForm(forms.ModelForm):
    """Formulaire pour créer/modifier un financement"""
    class Meta:
        model = Financement
        fields = ['banque', 'type', 'montant']
        widgets = {
            'banque': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type de financement (crédit, emprunt, etc)'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Montant', 'step': '0.01'}),
        }


class ContratForm(forms.ModelForm):
    """Formulaire pour créer/modifier un contrat"""
    class Meta:
        model = Contrat
        fields = ['pdf']
        widgets = {
            'pdf': forms.FileInput(attrs={'class': 'form-control', 'accept': 'application/pdf'}),
        }
