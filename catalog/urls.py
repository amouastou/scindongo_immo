from django.urls import path
from .views import (
    ProgrammeListView, 
    ProgrammeDetailView, 
    UniteDetailView,
    BiensListView,
    ProgrammeCreateView,
    ProgrammeUpdateView,
    ProgrammeDeleteView,
    TypeBienListView,
    TypeBienCreateView,
    TypeBienUpdateView,
    TypeBienDeleteView,
    ModeleBienListView,
    ModeleBienCreateView,
    ModeleBienUpdateView,
    ModeleBienDeleteView,
    UniteListView,
    UniteCreateView,
    UniteUpdateView,
    UniteDeleteView,
)

urlpatterns = [
    # Biens disponibles (page publique)
    path('biens/', BiensListView.as_view(), name='biens_list'),
    
    # Programmes
    path('programmes/', ProgrammeListView.as_view(), name='programme_list'),
    path('programmes/nouveau/', ProgrammeCreateView.as_view(), name='programme_create'),
    path('programmes/<uuid:pk>/', ProgrammeDetailView.as_view(), name='programme_detail'),
    path('programmes/<uuid:pk>/modifier/', ProgrammeUpdateView.as_view(), name='programme_edit'),
    path('programmes/<uuid:pk>/supprimer/', ProgrammeDeleteView.as_view(), name='programme_delete'),
    
    # Types de biens
    path('types-biens/', TypeBienListView.as_view(), name='typebien_list'),
    path('types-biens/nouveau/', TypeBienCreateView.as_view(), name='typebien_create'),
    path('types-biens/<uuid:pk>/modifier/', TypeBienUpdateView.as_view(), name='typebien_edit'),
    path('types-biens/<uuid:pk>/supprimer/', TypeBienDeleteView.as_view(), name='typebien_delete'),
    
    # Modèles de biens
    path('modeles-biens/', ModeleBienListView.as_view(), name='modelebien_list'),
    path('modeles-biens/nouveau/', ModeleBienCreateView.as_view(), name='modelebien_create'),
    path('modeles-biens/<uuid:pk>/modifier/', ModeleBienUpdateView.as_view(), name='modelebien_edit'),
    path('modeles-biens/<uuid:pk>/supprimer/', ModeleBienDeleteView.as_view(), name='modelebien_delete'),
    
    # Unités
    path('unites/', UniteListView.as_view(), name='unite_list'),
    path('unites/nouveau/', UniteCreateView.as_view(), name='unite_create'),
    path('unites/<uuid:pk>/', UniteDetailView.as_view(), name='unite_detail'),
    path('unites/<uuid:pk>/modifier/', UniteUpdateView.as_view(), name='unite_edit'),
    path('unites/<uuid:pk>/supprimer/', UniteDeleteView.as_view(), name='unite_delete'),
]
