# ----- PATCH ÉTAPE 6 -----
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from sales.models import Reservation, Paiement
from catalog.models import Unite


class StatsOverview(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_paye = Paiement.objects.filter(statut="valide").aggregate(s=Sum("montant"))["s"] or 0

        return Response({
            "total_reservations": Reservation.objects.count(),
            "reservations_confirmees": Reservation.objects.filter(statut="confirmee").count(),
            "montant_total_paye": float(total_paye),
            "unites_reservees": Unite.objects.filter(statut_disponibilite="reserve").count(),
            "unites_disponibles": Unite.objects.filter(statut_disponibilite="disponible").count(),
        })
