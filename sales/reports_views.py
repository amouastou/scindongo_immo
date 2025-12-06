"""
Vues pour les rapports et exports administrateur
"""
import csv
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.generic import TemplateView, View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Q
from accounts.mixins import RoleRequiredMixin
from catalog.models import Programme, Unite
from .models import Reservation, Paiement, Financement, Contrat, Client, BanquePartenaire


# ============================================================================
# RAPPORTS ADMIN - Réservations
# ============================================================================

class ReservationsReportView(RoleRequiredMixin, TemplateView):
    """Rapport des réservations avec export CSV"""
    template_name = 'reports/reservations_report.html'
    required_roles = ["ADMIN"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Récupérer les paramètres de filtrage
        programme_id = self.request.GET.get('programme')
        statut = self.request.GET.get('statut')
        
        # Query de base
        reservations = Reservation.objects.select_related(
            'client', 'unite', 'unite__programme', 'unite__modele_bien'
        ).all()
        
        # Filtrer par programme
        if programme_id:
            reservations = reservations.filter(unite__programme_id=programme_id)
        
        # Filtrer par statut
        if statut:
            reservations = reservations.filter(statut=statut)
        
        # Ordonner
        reservations = reservations.order_by('-created_at')
        
        # Statistiques
        ctx['total_reservations'] = reservations.count()
        ctx['total_acomptes'] = reservations.aggregate(Sum('acompte'))['acompte__sum'] or 0
        ctx['reservations_confirmees'] = reservations.filter(statut='confirmee').count()
        ctx['reservations_en_cours'] = reservations.filter(statut='en_cours').count()
        
        # Listes
        ctx['reservations'] = reservations[:100]  # Pagination simple
        ctx['programmes'] = Programme.objects.all().order_by('nom')
        ctx['selected_programme'] = programme_id
        ctx['selected_statut'] = statut
        ctx['statuts'] = [
            ('en_cours', 'En cours'),
            ('confirmee', 'Confirmée'),
            ('annulee', 'Annulée'),
            ('expiree', 'Expirée'),
        ]
        
        return ctx


class ReservationsExportCSVView(RoleRequiredMixin, View):
    """Export réservations en CSV"""
    required_roles = ["ADMIN"]

    def get(self, request):
        # Récupérer les paramètres de filtrage
        programme_id = request.GET.get('programme')
        statut = request.GET.get('statut')
        
        # Query
        reservations = Reservation.objects.select_related(
            'client', 'unite', 'unite__programme', 'unite__modele_bien'
        ).all()
        
        if programme_id:
            reservations = reservations.filter(unite__programme_id=programme_id)
        if statut:
            reservations = reservations.filter(statut=statut)
        
        reservations = reservations.order_by('-created_at')
        
        # Créer la réponse CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reservations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID Réservation', 'Client', 'Email Client', 'Téléphone', 
            'Programme', 'Unité', 'Modèle', 'Prix Unitaire', 'Acompte Payé',
            'Statut', 'Date Réservation', 'Confirmée le'
        ])
        
        for res in reservations:
            writer.writerow([
                str(res.id),
                f"{res.client.prenom} {res.client.nom}",
                res.client.email,
                res.client.telephone or '-',
                res.unite.programme.nom,
                res.unite.reference_lot,
                res.unite.modele_bien.nom_marketing,
                f"{res.unite.prix_ttc:,.0f}",
                f"{res.acompte:,.0f}",
                res.get_statut_display(),
                res.created_at.strftime('%d/%m/%Y %H:%M'),
                res.updated_at.strftime('%d/%m/%Y %H:%M') if res.statut == 'confirmee' else '-'
            ])
        
        return response


# ============================================================================
# RAPPORTS ADMIN - Paiements
# ============================================================================

class PaymentsReportView(RoleRequiredMixin, TemplateView):
    """Rapport des paiements avec statistiques"""
    template_name = 'reports/payments_report.html'
    required_roles = ["ADMIN"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Récupérer les paramètres de filtrage
        programme_id = self.request.GET.get('programme')
        moyen = self.request.GET.get('moyen')
        statut = self.request.GET.get('statut')
        
        # Query
        paiements = Paiement.objects.select_related(
            'reservation', 'reservation__client', 'reservation__unite__programme'
        ).all()
        
        if programme_id:
            paiements = paiements.filter(reservation__unite__programme_id=programme_id)
        if moyen:
            paiements = paiements.filter(moyen=moyen)
        if statut:
            paiements = paiements.filter(statut=statut)
        
        paiements = paiements.order_by('-date_paiement')
        
        # Statistiques
        total_montant = paiements.aggregate(Sum('montant'))['montant__sum'] or 0
        total_valides = paiements.filter(statut='valide').aggregate(Sum('montant'))['montant__sum'] or 0
        total_rejetes = paiements.filter(statut='rejete').aggregate(Sum('montant'))['montant__sum'] or 0
        
        # Par mode de paiement
        paiements_par_moyen = paiements.values('moyen').annotate(
            total=Sum('montant'),
            count=Count('id')
        ).order_by('-total')
        
        ctx['total_paiements'] = paiements.count()
        ctx['total_montant'] = total_montant
        ctx['total_valides'] = total_valides
        ctx['total_rejetes'] = total_rejetes
        ctx['paiements_valides_count'] = paiements.filter(statut='valide').count()
        ctx['paiements_en_attente_count'] = paiements.filter(statut='enregistre').count()
        ctx['paiements_par_moyen'] = paiements_par_moyen
        
        # Listes
        ctx['paiements'] = paiements[:100]
        ctx['programmes'] = Programme.objects.all().order_by('nom')
        ctx['selected_programme'] = programme_id
        ctx['selected_moyen'] = moyen
        ctx['selected_statut'] = statut
        ctx['moyens'] = [
            ('virement', 'Virement'),
            ('cheque', 'Chèque'),
            ('espece', 'Espèce'),
            ('carte', 'Carte'),
        ]
        ctx['statuts'] = [
            ('enregistre', 'Enregistré'),
            ('valide', 'Validé'),
            ('rejete', 'Rejeté'),
        ]
        
        return ctx


class PaymentsExportCSVView(RoleRequiredMixin, View):
    """Export paiements en CSV"""
    required_roles = ["ADMIN"]

    def get(self, request):
        programme_id = request.GET.get('programme')
        moyen = request.GET.get('moyen')
        statut = request.GET.get('statut')
        
        paiements = Paiement.objects.select_related(
            'reservation', 'reservation__client', 'reservation__unite__programme'
        ).all()
        
        if programme_id:
            paiements = paiements.filter(reservation__unite__programme_id=programme_id)
        if moyen:
            paiements = paiements.filter(moyen=moyen)
        if statut:
            paiements = paiements.filter(statut=statut)
        
        paiements = paiements.order_by('-date_paiement')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="paiements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID Paiement', 'Réservation', 'Client', 'Programme', 'Montant',
            'Mode de paiement', 'Statut', 'Date de paiement'
        ])
        
        for paiement in paiements:
            writer.writerow([
                str(paiement.id),
                str(paiement.reservation.id),
                f"{paiement.reservation.client.prenom} {paiement.reservation.client.nom}",
                paiement.reservation.unite.programme.nom,
                f"{paiement.montant:,.0f}",
                paiement.get_moyen_display(),
                paiement.get_statut_display(),
                paiement.date_paiement.strftime('%d/%m/%Y')
            ])
        
        return response


# ============================================================================
# RAPPORTS ADMIN - Financement
# ============================================================================

class FinancingReportView(RoleRequiredMixin, TemplateView):
    """Rapport des financements bancaires"""
    template_name = 'reports/financing_report.html'
    required_roles = ["ADMIN"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        programme_id = self.request.GET.get('programme')
        statut = self.request.GET.get('statut')
        banque_id = self.request.GET.get('banque')
        
        financements = Financement.objects.select_related(
            'reservation', 'reservation__client', 'reservation__unite__programme',
            'banque'
        ).all()
        
        if programme_id:
            financements = financements.filter(reservation__unite__programme_id=programme_id)
        if statut:
            financements = financements.filter(statut=statut)
        if banque_id:
            financements = financements.filter(banque_id=banque_id)
        
        financements = financements.order_by('-created_at')
        
        # Statistiques
        total_montant = financements.aggregate(Sum('montant'))['montant__sum'] or 0
        total_acceptes = financements.filter(statut='accepte').aggregate(Sum('montant'))['montant__sum'] or 0
        total_refuses = financements.filter(statut='refuse').aggregate(Sum('montant'))['montant__sum'] or 0
        
        ctx['total_financements'] = financements.count()
        ctx['total_montant'] = total_montant
        ctx['acceptes_count'] = financements.filter(statut='accepte').count()
        ctx['en_etude_count'] = financements.filter(statut='en_etude').count()
        ctx['refuses_count'] = financements.filter(statut='refuse').count()
        ctx['total_acceptes'] = total_acceptes
        ctx['total_refuses'] = total_refuses
        
        if financements.count() > 0:
            ctx['taux_acceptation'] = round((financements.filter(statut='accepte').count() / financements.count()) * 100, 1)
        else:
            ctx['taux_acceptation'] = 0
        
        ctx['financements'] = financements[:100]
        ctx['programmes'] = Programme.objects.all().order_by('nom')
        ctx['banques'] = BanquePartenaire.objects.all().order_by('nom')
        ctx['selected_programme'] = programme_id
        ctx['selected_statut'] = statut
        ctx['selected_banque'] = banque_id
        ctx['statuts'] = [
            ('soumis', 'Soumis'),
            ('en_etude', 'En étude'),
            ('accepte', 'Accepté'),
            ('refuse', 'Refusé'),
            ('clos', 'Clos'),
        ]
        
        return ctx


class FinancingExportCSVView(RoleRequiredMixin, View):
    """Export financements en CSV"""
    required_roles = ["ADMIN"]

    def get(self, request):
        programme_id = request.GET.get('programme')
        statut = request.GET.get('statut')
        banque_id = request.GET.get('banque')
        
        financements = Financement.objects.select_related(
            'reservation', 'reservation__client', 'reservation__unite__programme',
            'banque'
        ).all()
        
        if programme_id:
            financements = financements.filter(reservation__unite__programme_id=programme_id)
        if statut:
            financements = financements.filter(statut=statut)
        if banque_id:
            financements = financements.filter(banque_id=banque_id)
        
        financements = financements.order_by('-created_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="financements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID Financement', 'Réservation', 'Client', 'Programme', 
            'Montant demandé', 'Banque', 'Statut', 'Date de demande'
        ])
        
        for fin in financements:
            writer.writerow([
                str(fin.id),
                str(fin.reservation.id),
                f"{fin.reservation.client.prenom} {fin.reservation.client.nom}",
                fin.reservation.unite.programme.nom,
                    f"{fin.montant:,.0f}",
                fin.banque.nom if fin.banque else '-',
                fin.get_statut_display(),
                fin.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        return response


# ============================================================================
# RAPPORTS ADMIN - Contrats
# ============================================================================

class ContractsReportView(RoleRequiredMixin, TemplateView):
    """Rapport des contrats"""
    template_name = 'reports/contracts_report.html'
    required_roles = ["ADMIN"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        programme_id = self.request.GET.get('programme')
        statut = self.request.GET.get('statut')
        
        contrats = Contrat.objects.select_related(
            'reservation', 'reservation__client', 'reservation__unite__programme'
        ).all()
        
        if programme_id:
            contrats = contrats.filter(reservation__unite__programme_id=programme_id)
        if statut:
            contrats = contrats.filter(statut=statut)
        
        contrats = contrats.order_by('-created_at')
        
        ctx['total_contrats'] = contrats.count()
        ctx['contrats_signes'] = contrats.filter(statut='signe').count()
        ctx['contrats_brouillon'] = contrats.filter(statut='brouillon').count()
        ctx['contrats_annules'] = contrats.filter(statut='annule').count()
        
        ctx['contrats'] = contrats[:100]
        ctx['programmes'] = Programme.objects.all().order_by('nom')
        ctx['selected_programme'] = programme_id
        ctx['selected_statut'] = statut
        ctx['statuts'] = [
            ('brouillon', 'Brouillon'),
            ('signe', 'Signé'),
            ('annule', 'Annulé'),
        ]
        
        return ctx


class ContractsExportCSVView(RoleRequiredMixin, View):
    """Export contrats en CSV"""
    required_roles = ["ADMIN"]

    def get(self, request):
        programme_id = request.GET.get('programme')
        statut = request.GET.get('statut')
        
        contrats = Contrat.objects.select_related(
            'reservation', 'reservation__client', 'reservation__unite__programme'
        ).all()
        
        if programme_id:
            contrats = contrats.filter(reservation__unite__programme_id=programme_id)
        if statut:
            contrats = contrats.filter(statut=statut)
        
        contrats = contrats.order_by('-created_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="contrats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID Contrat', 'Réservation', 'Client', 'Programme', 'Unité',
            'Statut', 'Date de création', 'Signé le'
        ])
        
        for contrat in contrats:
            writer.writerow([
                str(contrat.id),
                str(contrat.reservation.id),
                f"{contrat.reservation.client.prenom} {contrat.reservation.client.nom}",
                contrat.reservation.unite.programme.nom,
                contrat.reservation.unite.reference_lot,
                contrat.get_statut_display(),
                contrat.created_at.strftime('%d/%m/%Y %H:%M'),
                contrat.updated_at.strftime('%d/%m/%Y %H:%M') if contrat.statut == 'signe' else '-'
            ])
        
        return response
