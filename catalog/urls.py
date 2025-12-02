from django.urls import path
from .views import ProgrammeListView, ProgrammeDetailView, UniteDetailView

urlpatterns = [
    path('programmes/', ProgrammeListView.as_view(), name='programme_list'),
    path('programmes/<uuid:pk>/', ProgrammeDetailView.as_view(), name='programme_detail'),
    path('unites/<uuid:pk>/', UniteDetailView.as_view(), name='unite_detail'),
]
