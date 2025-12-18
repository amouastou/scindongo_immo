from django import forms
from .models import Reservation, Paiement, Client, Financement, Contrat, ReservationDocument, FinancementDocument
from .models import EcheanceLoyer


class ReservationForm(forms.ModelForm):
    """Formulaire simple de réservation - SEULEMENT acompte"""
    class Meta:
        model = Reservation
        fields = ['acompte', 'duree_bail_mois']
        widgets = {
            'acompte': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant de l\'acompte',
                'step': '0.01',
                'min': '0'
            }),
            'duree_bail_mois': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Durée du bail en mois (12, 24, 36...)',
                'min': '1',
                'value': '12'
            }),
        }
        labels = {
            'acompte': 'Acompte à verser (FCFA)',
            'duree_bail_mois': 'Durée du bail (mois)'
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
    """Formulaire complet pour composer ou modifier un contrat"""

    class Meta:
        model = Contrat
        fields = [
            'client_nom', 'client_email', 'client_telephone', 'client_adresse',
            'programme_nom', 'unite_reference', 'unite_description', 'montant_total',
            'date_signature', 'date_fin', 'lieu_signature',
            'commercial_nom', 'commercial_email',
            'conditions_generales', 'conditions_particulieres',
            'pdf', 'statut',
        ]
        widgets = {
            'client_nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet du client'}),
            'client_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@client.com'}),
            'client_telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+221 77 000 00 00'}),
            'client_adresse': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse postale'}),
            'programme_nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du programme'}),
            'unite_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Référence lot'}),
            'unite_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description du bien'}),
            'montant_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'date_signature': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'lieu_signature': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ville, pays'}),
            'commercial_nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du commercial'}),
            'commercial_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@scindongo.com'}),
            'conditions_generales': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'conditions_particulieres': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'pdf': forms.FileInput(attrs={'class': 'form-control', 'accept': 'application/pdf'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'client_nom': 'Nom du client (affichage sur le contrat)',
            'client_email': 'Email du client',
            'client_telephone': 'Téléphone',
            'client_adresse': 'Adresse du client',
            'programme_nom': 'Programme immobilier',
            'unite_reference': 'Référence du bien',
            'unite_description': 'Description / Modèle du bien',
            'montant_total': 'Montant total TTC',
            'date_signature': 'Date de signature',
            'date_fin': 'Date de fin',
            'lieu_signature': 'Lieu de signature',
            'commercial_nom': 'Nom du commercial / représentant',
            'commercial_email': 'Email du commercial',
            'conditions_generales': 'Conditions générales',
            'conditions_particulieres': 'Conditions particulières',
            'pdf': 'Document PDF du contrat (optionnel)',
            'statut': 'Statut du contrat',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre le PDF optionnel pour permettre la génération automatique
        self.fields['pdf'].required = False


class FinancingRequestForm(forms.ModelForm):
    """Formulaire pour uploader le justificatif de financement bancaire."""
    class Meta:
        model = Financement
        fields = ['banque', 'montant', 'justificatif_financement']
        widgets = {
            'banque': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Montant souhaité'
            }),
            'justificatif_financement': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'required': True,
            }),
        }
        labels = {
            'banque': 'Banque partenaire',
            'montant': 'Montant de financement (FCFA)'
            ,
            'justificatif_financement': 'Justificatif de financement bancaire'
        }

    def clean_justificatif_financement(self):
        fichier = self.cleaned_data.get('justificatif_financement')

        if not fichier:
            raise forms.ValidationError('Fichier requis')

        # Vérifier taille (max 5MB)
        if fichier.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Fichier trop volumineux (maximum 5MB)')

        # Vérifier format
        allowed_formats = ['application/pdf', 'image/jpeg', 'image/png']
        if getattr(fichier, 'content_type', None) not in allowed_formats:
            raise forms.ValidationError('Format non autorisé. Accepté: PDF, JPG, PNG')

        return fichier


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


class FinancementDocumentForm(forms.ModelForm):
    """Formulaire pour uploader un document de financement"""
    class Meta:
        model = FinancementDocument
        fields = ['document_type', 'fichier']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les champs optionnels sur le formulaire vierge (requis lors du clean/POST)
        self.fields['document_type'].required = False
        self.fields['fichier'].required = False
    
    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        
        # Seulement valider si fichier est fourni (lors de POST)
        if fichier:
            # Vérifier taille (max 60MB pour permettre les brochures volumineuses)
            if fichier.size > 60 * 1024 * 1024:
                raise forms.ValidationError('Fichier trop volumineux (maximum 60MB)')
            
            # Vérifier format
            allowed_formats = ['application/pdf', 'image/jpeg', 'image/png']
            if fichier.content_type not in allowed_formats:
                raise forms.ValidationError('Format non autorisé. Accepté: PDF, JPG, PNG')
        
        return fichier
    
    def clean(self):
        """Valider que les deux champs sont fournis lors de POST"""
        cleaned_data = super().clean()
        
        # Lors de POST, les deux champs sont requis
        if self.is_bound:
            document_type = cleaned_data.get('document_type')
            fichier = cleaned_data.get('fichier')
            
            if not document_type:
                self.add_error('document_type', 'Veuillez sélectionner un type de document')
            
            if not fichier:
                self.add_error('fichier', 'Fichier requis')
        
        return cleaned_data


class FinancementDocumentUpdateForm(forms.ModelForm):
    """Formulaire pour modifier uniquement le fichier d'un document de financement existant"""
    class Meta:
        model = FinancementDocument
        fields = ['fichier']
        widgets = {
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'required': True,
            }),
        }
        labels = {
            'fichier': 'Nouveau fichier (PDF/JPG/PNG max 60MB)'
        }

    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if not fichier:
            raise forms.ValidationError('Fichier requis')
        if fichier.size > 60 * 1024 * 1024:
            raise forms.ValidationError('Fichier trop volumineux (maximum 60MB)')
        allowed_formats = ['application/pdf', 'image/jpeg', 'image/png']
        if fichier.content_type not in allowed_formats:
            raise forms.ValidationError('Format non autorisé. Accepté: PDF, JPG, PNG')
        return fichier


class SignContratOTPForm(forms.Form):
    """Formulaire pour saisir le code OTP de signature de contrat"""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        label='Code OTP (6 chiffres)',
        widget=forms.TextInput(attrs={
            'placeholder': '000000',
            'maxlength': '6',
            'class': 'form-control text-center font-monospace',
            'style': 'font-size: 2rem; letter-spacing: 0.5rem;',
        }),
        help_text='Entrez les 6 chiffres du code OTP'
    )
    
    def clean_otp(self):
        """Valider que c'est 6 chiffres"""
        otp = self.cleaned_data.get('otp', '')
        
        if not otp.isdigit():
            raise forms.ValidationError('Le code doit contenir 6 chiffres')
        
        if len(otp) != 6:
            raise forms.ValidationError('Le code doit contenir exactement 6 chiffres')
        
        return otp


class EcheancePaiementForm(forms.Form):
    """Formulaire pour payer une échéance de loyer"""
    montant = forms.DecimalField(
        required=True,
        label='Montant',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'step': '0.01',
            'min': '0'
        })
    )
    moyen = forms.ChoiceField(
        choices=[
            ('virement', '🏦 Virement'),
            ('cheque', '📋 Chèque'),
            ('espece', '💵 Espèce'),
            ('carte', '💳 Carte'),
        ],
        required=True,
        label='Moyen de Paiement',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    source = forms.CharField(
        required=True,
        label='Référence de Paiement',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numéro de compte, numéro de chèque, etc.'
        })
    )
    notes = forms.CharField(
        required=False,
        label='Notes',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Remarques supplémentaires...'
        })
    )

