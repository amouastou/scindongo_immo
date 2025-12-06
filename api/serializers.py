from decimal import Decimal
import hashlib
from datetime import datetime, timedelta

from django.db import models
from rest_framework import serializers

from accounts.models import User
from sales.models import (
    Client,
    Reservation,
    ReservationDocument,
    Contrat,
    Paiement,
    BanquePartenaire,
    Financement,
    Echeance,
)
from catalog.models import (
    Programme,
    Unite,
    TypeBien,
    ModeleBien,
    EtapeChantier,
    AvancementChantier,
    PhotoChantier,
)


# ============================
#          CATALOGUE
# ============================


class TypeBienSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeBien
        fields = "__all__"


class ModeleBienSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeleBien
        fields = "__all__"


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = "__all__"


class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unite
        fields = "__all__"


class EtapeChantierSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtapeChantier
        fields = [
            "id",
            "programme",
            "code",
            "libelle",
            "ordre",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class AvancementChantierSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvancementChantier
        fields = [
            "id",
            "etape",
            "date_pointage",
            "pourcentage",
            "commentaire",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_pourcentage(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le pourcentage doit être entre 0 et 100.")
        return value


class PhotoChantierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoChantier
        fields = [
            "id",
            "avancement",
            "image",
            "gps_lat",
            "gps_lng",
            "pris_le",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        gps_lat = attrs.get("gps_lat")
        gps_lng = attrs.get("gps_lng")

        errors = {}

        # Si une coordonnée est remplie, l’autre doit l’être aussi
        if (gps_lat is None) != (gps_lng is None):
            errors["gps"] = "gps_lat et gps_lng doivent être fournis ensemble ou laissés vides."

        if gps_lat is not None:
            if gps_lat < Decimal("-90") or gps_lat > Decimal("90"):
                errors["gps_lat"] = "Latitude invalide (doit être entre -90 et 90)."

        if gps_lng is not None:
            if gps_lng < Decimal("-180") or gps_lng > Decimal("180"):
                errors["gps_lng"] = "Longitude invalide (doit être entre -180 et 180)."

        pris_le = attrs.get("pris_le")
        if pris_le is not None:
            # On tolère légèrement, mais on évite une date très future
            if pris_le > datetime.utcnow() + timedelta(days=1):
                errors["pris_le"] = "La date de prise de vue ne peut pas être très ultérieure."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class PhotoChantierListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes filtrées, si besoin plus tard."""
    class Meta:
        model = PhotoChantier
        fields = [
            "id",
            "avancement",
            "gps_lat",
            "gps_lng",
            "pris_le",
        ]


# ============================
#          COMMERCIAL : CLIENTS & RESERVATIONS
# ============================




# ============================
#   RESERVATION DOCUMENTS
# ============================


class ReservationDocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les documents de réservation"""
    class Meta:
        model = ReservationDocument
        fields = [
            "id",
            "document_type",
            "fichier",
            "statut",
            "raison_rejet",
            "verifie_par",
            "verifie_le",
            "created_at",
        ]
        read_only_fields = ["id", "statut", "raison_rejet", "verifie_par", "verifie_le", "created_at"]


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "user",
            "nom",
            "prenom",
            "telephone",
            "email",
            "kyc_statut",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class ReservationSerializer(serializers.ModelSerializer):
    documents = ReservationDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            "id",
            "client",
            "unite",
            "date_reservation",
            "acompte",
            "statut",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "date_reservation", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        unite = attrs.get("unite") or (instance.unite if instance else None)
        statut = attrs.get("statut") or (instance.statut if instance else None)
        acompte = attrs.get("acompte") if "acompte" in attrs else (instance.acompte if instance else None)

        errors = {}

        if acompte is not None and acompte < 0:
            errors["acompte"] = "L'acompte doit être positif."

        if acompte is not None and unite is not None and getattr(unite, "prix_ttc", None) is not None:
            if acompte > unite.prix_ttc:
                errors["acompte"] = "L'acompte ne peut pas dépasser le prix TTC de l'unité."

        if unite is not None:
            qs = Reservation.objects.filter(unite=unite).exclude(statut__in=["annulee", "expiree"])
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists() and statut in ["en_cours", "confirmee"]:
                errors["unite"] = "Cette unité a déjà une réservation active."

            if statut in ["en_cours", "confirmee"] and unite.statut_disponibilite not in ["disponible", "reserve"]:
                errors["unite"] = "L'unité n'est pas disponible pour une nouvelle réservation."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def _update_unite_statut(self, reservation: Reservation):
        unite = reservation.unite
        if not unite:
            return

        new_statut = None
        if reservation.statut == "en_cours":
            new_statut = "reserve"
        elif reservation.statut == "confirmee":
            new_statut = "vendu"
        elif reservation.statut in ["annulee", "expiree"]:
            new_statut = "disponible"

        if new_statut and unite.statut_disponibilite != new_statut:
            unite.statut_disponibilite = new_statut
            unite.save(update_fields=["statut_disponibilite"])

    def create(self, validated_data):
        reservation = super().create(validated_data)
        self._update_unite_statut(reservation)
        return reservation

    def update(self, instance, validated_data):
        reservation = super().update(instance, validated_data)
        self._update_unite_statut(reservation)
        return reservation


# ============================
#        BANQUES & FINANCEMENT
# ============================


class BanquePartenaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = BanquePartenaire
        fields = [
            "id",
            "nom",
            "code_banque",
            "contact",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class FinancementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Financement
        fields = [
            "id",
            "reservation",
            "banque",
            "type",
            "montant",
            "statut",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        reservation = attrs.get("reservation") or (instance.reservation if instance else None)
        montant = attrs.get("montant") if "montant" in attrs else (instance.montant if instance else None)

        errors = {}

        if montant is not None and montant <= 0:
            errors["montant"] = "Le montant de financement doit être positif."

        if reservation is not None and montant is not None:
            unite = reservation.unite
            if getattr(unite, "prix_ttc", None) is not None and montant > unite.prix_ttc:
                errors["montant"] = "Le montant du financement dépasse le prix TTC de l'unité."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class EcheanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Echeance
        fields = [
            "id",
            "financement",
            "date_echeance",
            "montant_total",
            "statut",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        montant_total = attrs.get("montant_total")
        errors = {}
        if montant_total is not None and montant_total <= 0:
            errors["montant_total"] = "Le montant de l'échéance doit être positif."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


# ============================
#          CONTRATS & PAIEMENTS
# ============================


class ContratSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrat
        fields = [
            "id",
            "reservation",
            "numero",
            "statut",
            "pdf",
            "signe_le",
            "pdf_hash",
            "otp_logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "pdf_hash", "created_at", "updated_at")

    def validate(self, attrs):
        """Valider que la réservation est confirmée avant de créer un contrat."""
        from core.choices import ReservationStatus
        
        instance = self.instance
        reservation = attrs.get("reservation") or (instance.reservation if instance else None)
        
        if not instance and reservation:
            # Création : vérifier que la réservation est confirmée
            if reservation.statut != ReservationStatus.CONFIRMEE:
                raise serializers.ValidationError(
                    {"reservation": "Un contrat ne peut être créé que pour une réservation confirmée."}
                )
        
        return attrs

    def _compute_pdf_hash(self, pdf_field):
        if not pdf_field:
            return ""
        hasher = hashlib.sha256()
        for chunk in pdf_field.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()

    def validate(self, attrs):
        instance = self.instance
        statut = attrs.get("statut") or (instance.statut if instance else None)
        pdf = attrs.get("pdf") or (instance.pdf if instance else None)

        errors = {}
        if statut == "signe" and not pdf:
            errors["pdf"] = "Un contrat signé doit avoir un PDF associé."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        pdf = validated_data.get("pdf")
        contrat = super().create(validated_data)
        if pdf:
            contrat.pdf_hash = self._compute_pdf_hash(pdf)
            contrat.save(update_fields=["pdf_hash"])
        return contrat

    def update(self, instance, validated_data):
        pdf = validated_data.get("pdf", instance.pdf)
        contrat = super().update(instance, validated_data)
        if pdf:
            contrat.pdf_hash = self._compute_pdf_hash(pdf)
            contrat.save(update_fields=["pdf_hash"])
        return contrat


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = [
            "id",
            "reservation",
            "montant",
            "date_paiement",
            "moyen",
            "source",
            "statut",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "date_paiement", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        reservation = attrs.get("reservation") or (instance.reservation if instance else None)
        montant = attrs.get("montant") if "montant" in attrs else (instance.montant if instance else None)
        statut = attrs.get("statut") or (instance.statut if instance else None)

        errors = {}

        if montant is not None and montant <= 0:
            errors["montant"] = "Le montant du paiement doit être positif."

        if reservation is not None and montant is not None:
            unite = reservation.unite
            prix = getattr(unite, "prix_ttc", None)
            if prix is not None:
                qs = Paiement.objects.filter(reservation=reservation).exclude(statut="rejete")
                if instance is not None:
                    qs = qs.exclude(pk=instance.pk)

                total_existant = qs.aggregate(total=models.Sum("montant"))["total"] or Decimal("0")
                total_apres = total_existant + Decimal(montant)

                if total_apres > prix:
                    errors["montant"] = "La somme des paiements dépasse le prix TTC de l'unité."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


# ============================
#          USER
# ============================


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
