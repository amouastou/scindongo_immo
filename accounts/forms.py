from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        # On met le username interne = email pour compatibilité éventuelle
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
