from django.urls import path
from .views import (
    UserLoginView, 
    UserLogoutView, 
    RegisterView,
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
    ClientProfileUpdateView,
    ClientChangePasswordView,
    CommercialProfileUpdateView,
    CommercialChangePasswordView
)

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profil/modifier/', ClientProfileUpdateView.as_view(), name='edit_profile'),
    path('profil/changer-mot-de-passe/', ClientChangePasswordView.as_view(), name='change_password'),
    # Routes pour le commercial (profil local)
    path('commercial/profil/modifier/', CommercialProfileUpdateView.as_view(), name='commercial_edit_profile'),
    path('commercial/profil/changer-mot-de-passe/', CommercialChangePasswordView.as_view(), name='commercial_change_password'),
    path('utilisateurs/', UserListView.as_view(), name='user_list'),
    path('utilisateurs/nouveau/', UserCreateView.as_view(), name='user_create'),
    path('utilisateurs/<uuid:pk>/modifier/', UserUpdateView.as_view(), name='user_edit'),
    path('utilisateurs/<uuid:pk>/supprimer/', UserDeleteView.as_view(), name='user_delete'),
]
