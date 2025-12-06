from django import forms
from django.contrib.auth import get_user_model
from .models import Programme, AvancementChantierUnite, PhotoChantierUnite

User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    """Widget personnalisé pour l'upload de plusieurs fichiers."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Champ de formulaire pour plusieurs fichiers."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ProgrammeForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier un programme.
    Le commercial est sélectionné via un dropdown parmi les utilisateurs avec rôle COMMERCIAL.
    """
    contact_commercial = forms.ModelChoiceField(
        queryset=User.objects.filter(roles__code="COMMERCIAL").distinct(),
        required=False,
        empty_label="--- Sélectionner un commercial ---",
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )

    class Meta:
        model = Programme
        fields = [
            'nom',
            'description',
            'image_principale',
            'adresse',
            'gps_lat',
            'gps_lng',
            'notaire_nom',
            'notaire_contact',
            'contact_commercial',
            'statut',
            'date_livraison_prevue',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image_principale': forms.FileInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'gps_lat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'gps_lng': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'notaire_nom': forms.TextInput(attrs={'class': 'form-control'}),
            'notaire_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'date_livraison_prevue': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


class AvancementChantierUniteForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier un avancement de chantier.
    Permet l'upload de plusieurs photos.
    """
    photos = MultipleFileField(
        required=False,
        label="Photos du chantier",
        help_text="Sélectionnez une ou plusieurs photos (formats: JPG, PNG)",
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = AvancementChantierUnite
        fields = ['unite', 'reservation', 'etape', 'date_pointage', 'pourcentage', 'commentaire']
        widgets = {
            'unite': forms.Select(attrs={'class': 'form-select'}),
            'reservation': forms.Select(attrs={'class': 'form-select'}),
            'etape': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Fondations, Gros œuvre, Finitions, Livraison'
            }),
            'date_pointage': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'pourcentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 1
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observations, notes importantes, etc.'
            }),
        }
        labels = {
            'unite': 'Unité',
            'reservation': 'Réservation (Optionnel)',
            'etape': 'Étape',
            'date_pointage': 'Date de Pointage',
            'pourcentage': 'Pourcentage (%)',
            'commentaire': 'Commentaires',
        }

