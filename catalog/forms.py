from django import forms
from django.contrib.auth import get_user_model
from .models import Programme

User = get_user_model()


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
