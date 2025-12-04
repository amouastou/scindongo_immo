from django.shortcuts import redirect
from django.contrib import messages
from django.http import Http404
from .models import Reservation


class ReservationRequiredMixin:
    """
    Mixin pour vérifier qu'une réservation existe.
    Utilisé pour s'assurer qu'on ne peut accéder à financement/contrat/paiement
    que si la réservation existe d'abord.
    """
    def dispatch(self, request, *args, **kwargs):
        reservation_id = self.kwargs.get('reservation_id')
        if not reservation_id:
            raise Http404("Réservation non trouvée")
        
        try:
            self.reservation = Reservation.objects.get(id=reservation_id, client__user=request.user)
        except Reservation.DoesNotExist:
            raise Http404("Réservation non trouvée")
        
        return super().dispatch(request, *args, **kwargs)


class FinancementFormMixin:
    """
    Mixin pour vérifier qu'on peut ajouter un financement.
    Conditions : la réservation doit exister
    """
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if not self.reservation.can_add_financement():
            messages.error(request, "Vous devez créer une réservation avant de choisir un financement.")
            return redirect('client_dashboard')
        
        return response


class ContratFormMixin:
    """
    Mixin pour vérifier qu'on peut signer un contrat.
    Conditions : la réservation doit exister
    """
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if not self.reservation.can_sign_contrat():
            messages.error(request, "Vous devez créer une réservation avant de signer le contrat.")
            return redirect('client_dashboard')
        
        return response


class PaiementFormMixin:
    """
    Mixin pour vérifier qu'on peut ajouter un paiement.
    Conditions : 
    - la réservation doit exister
    - (optionnel) le contrat doit être signé si vous voulez la confirmation
    """
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if not self.reservation.can_add_paiement():
            messages.error(request, "Vous devez créer une réservation avant de faire un paiement.")
            return redirect('client_dashboard')
        
        # Avertir si le contrat n'est pas signé
        if hasattr(self.reservation, 'contrat') and self.reservation.contrat.statut != 'signe':
            messages.warning(request, "⚠️ Conseil : Signez le contrat avant de payer pour valider définitivement votre réservation.")
        
        return response
