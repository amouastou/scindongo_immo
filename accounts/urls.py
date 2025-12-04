from django.urls import path
from .views import (
    UserLoginView, 
    UserLogoutView, 
    RegisterView,
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView
)

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('utilisateurs/', UserListView.as_view(), name='user_list'),
    path('utilisateurs/nouveau/', UserCreateView.as_view(), name='user_create'),
    path('utilisateurs/<uuid:pk>/modifier/', UserUpdateView.as_view(), name='user_edit'),
    path('utilisateurs/<uuid:pk>/supprimer/', UserDeleteView.as_view(), name='user_delete'),
]
