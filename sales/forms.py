from django import forms
from .models import Reservation, Paiement


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['acompte']


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['montant', 'moyen', 'source']
