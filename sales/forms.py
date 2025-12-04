from django import forms
from .models import Reservation, Paiement, Client, Financement, Contrat, ReservationDocument


class ReservationForm(forms.ModelForm):
    """Formulaire simple de réservation - SEULEMENT acompte"""
    class Meta:
        model = Reservation
        fields = ['acompte']
        widgets = {
            'acompte': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant de l\'acompte',
                'step': '0.01',
                'min': '0'
            }),
        }
        labels = {
            'acompte': 'Acompte à verser (FCFA)'
        }


class PaymentModeForm(forms.Form):
    """Formulaire pour choisir le mode de paiement APRÈS confirmation"""
    PAYMENT_MODE_CHOICES = (
        ('direct', 'Paiement Direct (Comptant)'),
        ('financing', 'Demander Financement Bancaire'),
    )
    
    payment_mode = forms.ChoiceField(
        choices=PAYMENT_MODE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Comment souhaitez-vous payer ?',
        required=True
    )


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['montant', 'moyen', 'source']
        widgets = {
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'moyen': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro compte, chèque, etc'}),
        }


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


class FinancingRequestForm(forms.ModelForm):
    """Formulaire pour le client demander un financement APRÈS confirmation"""
    class Meta:
        model = Financement
        fields = ['banque', 'montant']
        widgets = {
            'banque': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Montant souhaité'
            }),
        }
        labels = {
            'banque': 'Banque partenaire',
            'montant': 'Montant de financement (FCFA)'
        }


class ReservationDocumentForm(forms.ModelForm):
    """Formulaire pour uploader un document de réservation"""
    class Meta:
        model = ReservationDocument
        fields = ['document_type', 'fichier']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'required': True
            }),
        }
        labels = {
            'document_type': 'Type de document',
            'fichier': 'Sélectionner fichier (PDF/JPG/PNG max 5MB)'
        }

    def clean_fichier(self):
        """Valider fichier uploadé"""
        fichier = self.cleaned_data.get('fichier')
        
        if not fichier:
            raise forms.ValidationError('Fichier requis')
        
        # Vérifier taille (max 5MB)
        if fichier.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Fichier trop volumineux (maximum 5MB)')
        
        # Vérifier format
        allowed_formats = ['application/pdf', 'image/jpeg', 'image/png']
        if fichier.content_type not in allowed_formats:
            raise forms.ValidationError('Format non autorisé. Accepté: PDF, JPG, PNG')
        
        return fichier
