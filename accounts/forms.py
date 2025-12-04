from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Role


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


class UserManagementForm(forms.ModelForm):
    """Formulaire pour créer/modifier un utilisateur"""
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Rôles"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'roles']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserCreationFormWithPassword(UserManagementForm):
    """Formulaire pour créer un utilisateur avec mot de passe"""
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    password2 = forms.CharField(
        label="Confirmation mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta(UserManagementForm.Meta):
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_active', 'is_staff', 'roles']
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            self.save_m2m()
        return user
