from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views_stats import StatsOverview
from .views import (
    ProgrammeViewSet,
    UniteViewSet,
    ClientViewSet,
    ReservationViewSet,
    ReservationDocumentViewSet,
    TypeBienViewSet,
    ModeleBienViewSet,
    EtapeChantierViewSet,
    AvancementChantierViewSet,
    PhotoChantierViewSet,
    AvancementChantierUniteViewSet,
    PhotoChantierUniteViewSet,
    BanquePartenaireViewSet,
    FinancementViewSet,
    EcheanceViewSet,
    ContratViewSet,
    PaiementViewSet,
)

router = DefaultRouter()

# Catalogue
router.register("programmes", ProgrammeViewSet)
router.register("unites", UniteViewSet)
router.register("typesbien", TypeBienViewSet)
router.register("modelesbien", ModeleBienViewSet)
router.register("etapes-chantier", EtapeChantierViewSet)
router.register("avancements-chantier", AvancementChantierViewSet)
router.register("photos-chantier", PhotoChantierViewSet)
router.register("avancements-unites", AvancementChantierUniteViewSet, basename="avancement-unite")
router.register("photos-unites", PhotoChantierUniteViewSet, basename="photo-unite")

# Commercial
router.register("clients", ClientViewSet)
router.register("reservations", ReservationViewSet)
router.register("reservation-documents", ReservationDocumentViewSet)

# Banques / Financement / Contrats / Paiements
router.register("banques", BanquePartenaireViewSet)
router.register("financements", FinancementViewSet)
router.register("echeances", EcheanceViewSet)
router.register("contrats", ContratViewSet)
router.register("paiements", PaiementViewSet)

urlpatterns = [
    # Auth JWT
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("stats/overview/", StatsOverview.as_view(), name="stats-overview"),
    path("", include(router.urls)),
]
