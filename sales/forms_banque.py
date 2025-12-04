from django import forms
from .models import BanquePartenaire

class BanquePartenaireForm(forms.ModelForm):
    class Meta:
        model = BanquePartenaire
        fields = ["nom", "code_banque", "contact"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "code_banque": forms.TextInput(attrs={"class": "form-control"}),
            "contact": forms.TextInput(attrs={"class": "form-control"}),
        }
