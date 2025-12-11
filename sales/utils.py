from django.utils import timezone

from core.choices import PaiementStatus, OperationType

PENDING_UNITE_SESSION_KEY = "pending_unite_id"


def set_pending_unite(request, unite_id):
    request.session[PENDING_UNITE_SESSION_KEY] = str(unite_id)


def get_pending_unite_and_clear(request):
    unite_id = request.session.get(PENDING_UNITE_SESSION_KEY)
    if unite_id:
        del request.session[PENDING_UNITE_SESSION_KEY]
    return unite_id


ECHEANCE_JOUR = 10


def generer_echeances_loyer(reservation, date_debut):
    """
    Générer les échéances de loyer pour une location.
    
    Args:
        reservation: Objet Reservation pour une location
        date_debut: Date de début du bail (datetime.date)
    
    Returns:
        Tuple (nb_created, nb_updated) avec le nombre d'échéances créées/mises à jour
    """
    from dateutil.relativedelta import relativedelta
    from sales.models import EcheanceLoyer
    
    if not reservation.is_location():
        raise ValueError("Seules les locations peuvent avoir des échéances de loyer")
    
    if not reservation.duree_bail_mois:
        raise ValueError("La durée du bail n'est pas définie")
    
    # Récupérer le prix mensuel (prix_ttc du modèle = loyer mensuel)
    montant_mensuel = reservation.unite.prix_ttc
    
    nb_created = 0
    nb_updated = 0
    
    # Créer/mettre à jour les échéances pour chaque mois
    for numero_mois in range(1, reservation.duree_bail_mois + 1):
        # Calculer la date d'échéance (10 du mois suivant)
        date_echeance = date_debut + relativedelta(months=numero_mois)
        date_echeance = date_echeance.replace(day=ECHEANCE_JOUR)
        
        echeance, created = EcheanceLoyer.objects.get_or_create(
            reservation=reservation,
            numero_mois=numero_mois,
            defaults={
                'montant': montant_mensuel,
                'date_echeance': date_echeance,
                'statut_paiement': PaiementStatus.ENREGISTRE
            }
        )
        
        if created:
            nb_created += 1
        else:
            nb_updated += 1
            # Mettre à jour si nécessaire
            echeance.montant = montant_mensuel
            echeance.date_echeance = date_echeance
            echeance.save(update_fields=['montant', 'date_echeance'])
    
    return nb_created, nb_updated


def calculer_montant_caution(reservation):
    """
    Calculer le montant de la caution (2 x loyer mensuel).
    
    Args:
        reservation: Objet Reservation pour une location
    
    Returns:
        Decimal: Montant de la caution
    """
    if not reservation.is_location():
        raise ValueError("Seules les locations peuvent avoir une caution")
    
    montant_mensuel = reservation.unite.prix_ttc
    return montant_mensuel * 2


def calculer_montant_premier_mois(reservation):
    """
    Calculer le montant du premier mois (loyer + caution).
    
    Args:
        reservation: Objet Reservation pour une location
    
    Returns:
        Decimal: Montant total du premier mois
    """
    if not reservation.is_location():
        raise ValueError("Seules les locations peuvent être calculées")
    
    montant_mensuel = reservation.unite.prix_ttc
    caution = calculer_montant_caution(reservation)
    
    return montant_mensuel + caution


def get_next_echeances_a_payer(client, reference_date=None, show_second_day=27):
    """Retourne uniquement les prochaines échéances à afficher pour un client location.

    Règles métier:
    - afficher la prochaine échéance non payée par réservation (statut != VALIDE)
    - dès qu'elle est soldée, la suivante remonte automatiquement
    - à partir du 27 du mois, afficher préventivement l'échéance du mois suivant

    Args:
        client: instance ``sales.models.Client`` (peut être None)
        reference_date: date utilisée pour la règle du 27 (par défaut: today dans TZ projet)
        show_second_day: entier représentant le jour du mois à partir duquel on affiche le mois suivant

    Returns:
        list[EcheanceLoyer]: liste triée par date d'échéance
    """
    if not client:
        return []

    if reference_date is None:
        reference_date = timezone.localdate()

    from collections import defaultdict
    from sales.models import EcheanceLoyer  # lazy import pour éviter les cycles

    echeances_qs = (
        EcheanceLoyer.objects.filter(
            reservation__client=client,
            reservation__unite__programme__type_operation=OperationType.LOCATION,
        )
        .select_related('reservation__client', 'reservation__unite', 'reservation__unite__programme')
        .order_by('reservation_id', 'numero_mois')
    )

    echeances_par_reservation = defaultdict(list)
    for echeance in echeances_qs:
        if echeance.statut_paiement == PaiementStatus.VALIDE:
            continue
        echeances_par_reservation[echeance.reservation_id].append(echeance)

    echeances_to_show = []

    for reservation_id, echeances in echeances_par_reservation.items():
        if not echeances:
            continue

        # Les QuerySet sont déjà ordonnés; on garde la première non payée
        echeances_to_show.append(echeances[0])

        if reference_date.day >= show_second_day and len(echeances) > 1:
            echeances_to_show.append(echeances[1])

    echeances_to_show.sort(key=lambda e: (e.date_echeance, e.numero_mois, e.reservation_id))
    return echeances_to_show

