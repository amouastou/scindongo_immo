from decimal import Decimal
from datetime import datetime, timedelta

from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import (
    IsAdminOrCommercial,
    IsAdminScindongo,
    IsCommercial,
    IsClient,
    IsReservationOwnerOrAdminOrCommercial,
    IsClientOwnerOrAdminOrCommercial,
)
from accounts.utils import is_admin_user

from .serializers import (
    ProgrammeSerializer,
    UniteSerializer,
    ClientSerializer,
    ReservationSerializer,
    ReservationDocumentSerializer,
    TypeBienSerializer,
    ModeleBienSerializer,
    EtapeChantierSerializer,
    AvancementChantierSerializer,
    PhotoChantierSerializer,
    AvancementChantierUniteSerializer,
    AvancementChantierUniteListSerializer,
    PhotoChantierUniteSerializer,
    BanquePartenaireSerializer,
    FinancementSerializer,
    EcheanceSerializer,
    EcheanceLoyerSerializer,
    ContratSerializer,
    PaiementSerializer,
)

from catalog.models import (
    Programme,
    Unite,
    TypeBien,
    ModeleBien,
    EtapeChantier,
    AvancementChantier,
    PhotoChantier,
    AvancementChantierUnite,
    PhotoChantierUnite,
)

from sales.models import (
    Client,
    Reservation,
    ReservationDocument,
    BanquePartenaire,
    Financement,
    Echeance,
    EcheanceLoyer,
    Contrat,
    Paiement,
)


# ============================
#     VIEWSETS CATALOGUE
# ============================


class ProgrammeViewSet(viewsets.ModelViewSet):
    queryset = Programme.objects.prefetch_related('unites', 'unites__reservations').all()
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["statut"]
    search_fields = ["nom", "description", "adresse"]
    ordering_fields = ["nom", "created_at"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        
        # 🔒 ADMIN voit tout, COMMERCIAL seulement ses programmes
        if not user.is_authenticated:
            return qs  # Lecture publique autorisée
        
        if is_admin_user(user):
            return qs
        
        # Commercial ne voit que ses programmes
        return qs.filter(contact_commercial=user)


class UniteViewSet(viewsets.ModelViewSet):
    queryset = Unite.objects.select_related('programme', 'modele_bien', 'modele_bien__type_bien').prefetch_related('reservations').all()
    serializer_class = UniteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["programme", "statut_disponibilite", "modele_bien"]
    search_fields = ["reference_lot"]
    ordering_fields = ["prix_ttc", "reference_lot", "created_at"]
    ordering = ["reference_lot"]
    
    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        
        # 🔒 ADMIN voit tout, COMMERCIAL seulement ses unités
        if not user.is_authenticated:
            return qs  # Lecture publique autorisée
        
        if is_admin_user(user):
            return qs
        
        # Commercial ne voit que les unités de ses programmes
        return qs.filter(programme__contact_commercial=user)


class TypeBienViewSet(viewsets.ModelViewSet):
    queryset = TypeBien.objects.all()
    serializer_class = TypeBienSerializer
    permission_classes = [IsAuthenticated]


class ModeleBienViewSet(viewsets.ModelViewSet):
    queryset = ModeleBien.objects.select_related('type_bien', 'programme').all()
    serializer_class = ModeleBienSerializer
    permission_classes = [IsAuthenticated]


class EtapeChantierViewSet(viewsets.ModelViewSet):
    queryset = EtapeChantier.objects.select_related('programme').all()
    serializer_class = EtapeChantierSerializer
    permission_classes = [IsAdminOrCommercial]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_authenticated and getattr(user, "is_commercial", False) and not is_admin_user(user):
            qs = qs.filter(programme__contact_commercial=user)

        programme_id = self.request.query_params.get("programme")
        if programme_id:
            qs = qs.filter(programme_id=programme_id)
        return qs


class AvancementChantierViewSet(viewsets.ModelViewSet):
    queryset = AvancementChantier.objects.all()
    serializer_class = AvancementChantierSerializer
    permission_classes = [IsAdminOrCommercial]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_authenticated and getattr(user, "is_commercial", False) and not is_admin_user(user):
            qs = qs.filter(etape__programme__contact_commercial=user)

        programme_id = self.request.query_params.get("programme")
        etape_id = self.request.query_params.get("etape")

        if programme_id:
            qs = qs.filter(etape__programme_id=programme_id)
        if etape_id:
            qs = qs.filter(etape_id=etape_id)

        return qs


class PhotoChantierViewSet(viewsets.ModelViewSet):
    queryset = PhotoChantier.objects.all()
    serializer_class = PhotoChantierSerializer
    permission_classes = [IsAdminOrCommercial]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_authenticated and getattr(user, "is_commercial", False) and not is_admin_user(user):
            qs = qs.filter(avancement__etape__programme__contact_commercial=user)

        avancement_id = self.request.query_params.get("avancement")
        if avancement_id:
            qs = qs.filter(avancement_id=avancement_id)
        return qs


# ============================
# AVANCEMENTS CHANTIER PAR UNITÉ
# ============================


class AvancementChantierUniteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer l'avancement des chantiers par unité individuelle.
    
    Permissions:
    - Commercial/Admin: CRUD complet
    - Client: READ ONLY, filtrés sur ses propres réservations confirmées
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["unite", "unite__programme", "reservation", "etape"]
    search_fields = ["unite__reference_lot", "etape", "commentaire"]
    ordering_fields = ["date_pointage", "pourcentage", "created_at"]
    ordering = ["-date_pointage"]

    def get_serializer_class(self):
        if self.action == "list":
            return AvancementChantierUniteListSerializer
        return AvancementChantierUniteSerializer

    def get_queryset(self):
        user = self.request.user
        
        qs = AvancementChantierUnite.objects.select_related(
            'unite', 'unite__programme', 'reservation'
        )

        # Admin : toutes les avancées
        if is_admin_user(user):
            return qs

        # Commercial : uniquement ses programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(unite__programme__contact_commercial=user)
        
        # Client : seulement ses réservations avec contrat signé
        if user.is_client:
            from sales.models import Client as ClientModel
            from core.choices import ContratStatus
            try:
                client_profile = ClientModel.objects.get(user=user)
                # Avancements liés aux réservations du client avec contrat signé
                return qs.filter(
                    reservation__client=client_profile,
                    reservation__contrat__statut=ContratStatus.SIGNE
                )
            except ClientModel.DoesNotExist:
                return qs.none()
        
        return qs.none()

    def get_permissions(self):
        """
        - list, retrieve : IsAuthenticated (filtrés par get_queryset)
        - create, update, partial_update, destroy : IsAdminOrCommercial
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsAdminOrCommercial]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Log l'ajout d'un avancement chantier"""
        instance = serializer.save()
        # Optionnel : audit log
        # audit_log(self.request.user, instance, 'create', {...}, self.request)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrCommercial])
    def add_photo(self, request, pk=None):
        """
        Ajoute une photo à un avancement existant.
        POST /api/avancements-unites/{id}/add_photo/
        Body: { image, gps_lat, gps_lng, pris_le, description }
        """
        avancement = self.get_object()
        serializer = PhotoChantierUniteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(avancement=avancement)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PhotoChantierUniteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les photos d'avancements unitaires.
    
    Permissions:
    - Commercial/Admin: CRUD complet
    - Client: READ ONLY sur les photos des avancements de ses réservations confirmées
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["avancement", "avancement__unite"]
    ordering_fields = ["pris_le", "created_at"]
    ordering = ["-pris_le"]

    def get_queryset(self):
        user = self.request.user
        
        qs = PhotoChantierUnite.objects.select_related(
            'avancement', 'avancement__unite', 'avancement__reservation'
        )

        # Admin : toutes les photos
        if is_admin_user(user):
            return qs

        # Commercial : photos liées à ses programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(avancement__unite__programme__contact_commercial=user)
        
        # Client : photos des avancements de ses réservations confirmées
        if user.is_client:
            from sales.models import Client as ClientModel
            from core.choices import ContratStatus
            try:
                client_profile = ClientModel.objects.get(user=user)
                return qs.filter(
                    avancement__reservation__client=client_profile,
                    avancement__reservation__contrat__statut=ContratStatus.SIGNE
                )
            except ClientModel.DoesNotExist:
                return qs.none()
        
        return qs.none()

    def get_serializer_class(self):
        return PhotoChantierUniteSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsAdminOrCommercial]
        return [permission() for permission in permission_classes]


# ============================
#     VIEWSETS COMMERCIAL
# ============================


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.select_related('user').prefetch_related('reservations').all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["nom", "prenom", "email", "telephone"]
    filterset_fields = ["kyc_statut"]

    def get_queryset(self):
        """Admin voit tout. Commercial voit ses clients. Client ne voit que son propre profil."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les clients ayant réservé sur SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(reservations__unite__programme__contact_commercial=user).distinct()
        
        # CLIENT : ne voir que son propre profil
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(pk=client_profile.pk)
        
        return qs.none()


# ============================
#   RESERVATION DOCUMENTS
# ============================


class ReservationDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet pour uploader et gérer documents de réservation"""
    queryset = ReservationDocument.objects.select_related('reservation', 'reservation__client').all()
    serializer_class = ReservationDocumentSerializer
    permission_classes = [IsAuthenticated, IsClientOwnerOrAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["document_type", "statut", "reservation"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Client voit QUE ses documents. Admin/Commercial voient tous."""
        qs = super().get_queryset()
        user = self.request.user
        
        if is_admin_user(user):
            return qs

        if getattr(user, "is_commercial", False):
            return qs.filter(reservation__unite__programme__contact_commercial=user)
        
        # Client : ne voir que les documents de SES réservations
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(reservation__client=client_profile)
        
        return qs.none()

    def perform_create(self, serializer):
        """Log l'upload du document"""
        doc = serializer.save()
        from core.utils import audit_log
        audit_log(self.request.user, doc, 'reservation_document_uploaded',
                 {'document_type': doc.document_type}, self.request)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related('client', 'unite', 'unite__programme', 'unite__modele_bien').prefetch_related('paiements', 'documents').all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated, IsReservationOwnerOrAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statut", "client", "unite__programme"]
    ordering_fields = ["date_reservation", "created_at"]
    ordering = ["-date_reservation"]

    def get_queryset(self):
        """Admin/Commercial voient leurs réservations. Client ne voit que SES réservations."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les réservations de SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(unite__programme__contact_commercial=user)
        
        # CLIENT : ne voir que ses réservations
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(client=client_profile)
        
        return qs.none()
    
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Endpoint pour annuler une réservation.
        Restreint à COMMERCIAL ou ADMIN.
        Payload: { "motif": "Raison de l'annulation" }
        """
        reservation = self.get_object()
        
        # Vérifier les permissions : seul COMMERCIAL ou ADMIN peut annuler
        is_admin = is_admin_user(request.user)
        is_commercial = getattr(request.user, "is_commercial", False)
        
        if not (is_admin or is_commercial):
            return Response(
                {"detail": "Seul un commercial ou admin peut annuler une réservation."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier si la réservation peut être annulée
        if not reservation.can_cancel():
            return Response(
                {
                    "detail": "Cette réservation ne peut pas être annulée. "
                              "(Statut déjà annulé/expiré ou contrat signé)"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Récupérer le motif
        motif = request.data.get("motif", "").strip()
        if not motif:
            return Response(
                {"motif": "Le motif d'annulation est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Annuler la réservation
        try:
            reservation.cancel(request.user, motif)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Audit log manuel
        from core.utils import audit_log
        audit_log(request.user, reservation, "reservation_cancelled",
                 {"motif": motif}, request)
        
        return Response(
            {
                "detail": "Réservation annulée avec succès.",
                "reservation": ReservationSerializer(reservation).data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["delete"], url_path="delete-cancelled")
    def delete_cancelled(self, request, pk=None):
        """
        Endpoint pour supprimer une réservation ANNULÉE seulement.
        Restreint à COMMERCIAL ou ADMIN.
        Supprime aussi les contrats, paiements, et financements liés.
        """
        reservation = self.get_object()
        
        # Vérifier les permissions : seul COMMERCIAL ou ADMIN peut supprimer
        is_admin = is_admin_user(request.user)
        is_commercial = getattr(request.user, "is_commercial", False)
        
        if not (is_admin or is_commercial):
            return Response(
                {"detail": "Seul un commercial ou admin peut supprimer une réservation."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que la réservation est annulée
        if not reservation.can_delete():
            return Response(
                {
                    "detail": "Seules les réservations annulées peuvent être supprimées."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Audit log avant suppression
        from core.utils import audit_log
        audit_log(request.user, reservation, "reservation_deleted",
                 {"motif_annulation": reservation.motif_annulation}, request)
        
        # Supprimer les relations liées d'abord (pour contourner les PROTECT ForeignKeys)
        reservation_id = reservation.id
        
        # Supprimer les documents liés à la réservation
        reservation.documents.all().delete()
        
        # Supprimer les contrats liés
        if hasattr(reservation, 'contrat'):
            reservation.contrat.delete()
        
        # Supprimer les paiements liés
        reservation.paiements.all().delete()
        
        # Supprimer le financement lié
        if hasattr(reservation, 'financement'):
            # Supprimer les échéances du financement (CASCADE auto-gérée mais on peut être explicite)
            reservation.financement.echeances.all().delete()
            reservation.financement.delete()
        
        # Maintenant supprimer la réservation elle-même
        reservation.delete()
        
        return Response(
            {
                "detail": f"Réservation {reservation_id} et tous ses éléments liés ont été supprimés avec succès."
            },
            status=status.HTTP_204_NO_CONTENT

        )


# ============================
#   VIEWSETS BANQUES & FINANCEMENT
# ============================


class BanquePartenaireViewSet(viewsets.ModelViewSet):
    queryset = BanquePartenaire.objects.all()
    serializer_class = BanquePartenaireSerializer
    # Admins et commerciaux peuvent gérer les banques partenaires
    from accounts.permissions import IsAdminScindongo, IsCommercial
    permission_classes = [IsAuthenticated, IsAdminScindongo | IsCommercial]


class FinancementViewSet(viewsets.ModelViewSet):
    queryset = Financement.objects.select_related('reservation', 'reservation__client', 'reservation__unite', 'banque').prefetch_related('echeances').all()
    serializer_class = FinancementSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statut", "reservation__client"]
    ordering_fields = ["created_at", "montant"]

    def get_queryset(self):
        """Admin voit tout. Commercial voit ses financements. Client voit SES financements."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les financements de SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(reservation__unite__programme__contact_commercial=user)
        
        # CLIENT : ne voir que ses financements
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(reservation__client=client_profile)
        
        return qs.none()

    @action(detail=True, methods=["post"], url_path="generer-echeances")
    def generer_echeances(self, request, pk=None):
        financement = self.get_object()
        data = request.data

        try:
            nombre = int(data.get("nombre_echeances", 0))
        except (TypeError, ValueError):
            return Response(
                {"nombre_echeances": "Nombre d'échéances invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if nombre <= 0:
            return Response(
                {"nombre_echeances": "Le nombre d'échéances doit être > 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        premiere_str = data.get("premiere_echeance")
        if not premiere_str:
            return Response(
                {"premiere_echeance": "La date de première échéance est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            premiere_date = datetime.strptime(premiere_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"premiere_echeance": "Format de date invalide (YYYY-MM-DD attendu)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        montant_total = financement.montant
        montant_par_echeance = (montant_total / nombre).quantize(Decimal("0.01"))

        echeances = []
        for i in range(nombre):
            date_ech = premiere_date + timedelta(days=30 * i)
            echeance = Echeance.objects.create(
                financement=financement,
                date_echeance=date_ech,
                montant_total=montant_par_echeance,
                statut=financement.statut,
            )
            echeances.append(echeance)

        serializer = EcheanceSerializer(echeances, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EcheanceViewSet(viewsets.ModelViewSet):
    queryset = Echeance.objects.select_related('financement', 'financement__reservation', 'financement__reservation__client').all()
    serializer_class = EcheanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statut", "financement__reservation__client"]
    ordering_fields = ["date_echeance"]

    def get_queryset(self):
        """Admin voit tout. Commercial voit ses échéances. Client voit SES échéances."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les échéances de SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(financement__reservation__unite__programme__contact_commercial=user)
        
        # CLIENT : ne voir que ses échéances
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(financement__reservation__client=client_profile)
        
        return qs.none()


# ============================
#   VIEWSETS CONTRATS & PAIEMENTS
# ============================


class ContratViewSet(viewsets.ModelViewSet):
    queryset = Contrat.objects.select_related('reservation', 'reservation__client', 'reservation__unite').prefetch_related('documents').all()
    serializer_class = ContratSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statut", "reservation__client"]
    ordering_fields = ["created_at", "signe_le"]

    def get_queryset(self):
        """Admin voit tout. Commercial voit ses contrats. Client voit SES contrats."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les contrats de SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(reservation__unite__programme__contact_commercial=user)
        
        # CLIENT : ne voir que ses contrats
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(reservation__client=client_profile)
        
        return qs.none()


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.select_related('reservation', 'reservation__client', 'reservation__unite').all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statut", "moyen", "reservation__client"]
    ordering_fields = ["date_paiement", "montant"]

    def get_queryset(self):
        """Admin voit tout. Commercial voit ses paiements. Client voit SES paiements."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les paiements de SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(reservation__unite__programme__contact_commercial=user)
        
        # CLIENT : ne voir que ses paiements
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(reservation__client=client_profile)
        
        return qs.none()


class EcheanceLoyerViewSet(viewsets.ModelViewSet):
    """ViewSet pour les échéances de loyer (location)."""
    queryset = EcheanceLoyer.objects.select_related(
        'reservation', 
        'reservation__client', 
        'reservation__unite', 
        'paiement'
    ).all()
    serializer_class = EcheanceLoyerSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["statut_paiement", "reservation__client", "numero_mois"]
    ordering_fields = ["date_echeance", "montant", "numero_mois"]

    def get_queryset(self):
        """Admin voit tout. Commercial voit les échéances de ses programmes. Client voit SES échéances."""
        qs = super().get_queryset()
        user = self.request.user
        
        # ADMIN voit tout
        if is_admin_user(user):
            return qs
        
        # COMMERCIAL ne voit que les échéances de SES programmes
        if getattr(user, "is_commercial", False):
            return qs.filter(reservation__unite__programme__contact_commercial=user)
        
        # CLIENT : ne voir que ses échéances
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return qs.filter(reservation__client=client_profile)
        
        return qs.none()
