from django.urls import path
from .views import (
    ProgrammeListView, 
    ProgrammeDetailView, 
    UniteDetailView,
    ProgrammeCreateView,
    ProgrammeUpdateView,
    ProgrammeDeleteView
)

urlpatterns = [
    path('programmes/', ProgrammeListView.as_view(), name='programme_list'),
    path('programmes/nouveau/', ProgrammeCreateView.as_view(), name='programme_create'),
    path('programmes/<uuid:pk>/', ProgrammeDetailView.as_view(), name='programme_detail'),
    path('programmes/<uuid:pk>/modifier/', ProgrammeUpdateView.as_view(), name='programme_edit'),
    path('programmes/<uuid:pk>/supprimer/', ProgrammeDeleteView.as_view(), name='programme_delete'),
    path('unites/<uuid:pk>/', UniteDetailView.as_view(), name='unite_detail'),
]
