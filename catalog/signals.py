"""
Signaux pour la gestion automatique des statuts de chantier.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from catalog.models import AvancementChantierUnite
from core.choices import StatutChantier


@receiver(post_save, sender=AvancementChantierUnite)
def update_unite_statut_chantier(sender, instance, created, **kwargs):
    """
    Quand un AvancementChantierUnite est créé/modifié :
    - Si c'est le premier avancement → statut = "en_cours"
    - Si pourcentage = 100 → statut = "termine"
    - Sinon → statut = "en_cours"
    """
    unite = instance.unite
    
    # Récupère tous les avancements de cette unité
    avancements = unite.avancements_chantier.all()
    
    if avancements.exists():
        # Prend le pourcentage max
        max_percentage = max([a.pourcentage for a in avancements])
        
        if max_percentage >= 100:
            unite.statut_chantier = StatutChantier.TERMINE
        else:
            unite.statut_chantier = StatutChantier.EN_COURS
    else:
        # S'il n'y a plus d'avancements, revenir à "non_commence"
        unite.statut_chantier = StatutChantier.NON_COMMENCE
    
    unite.save(update_fields=['statut_chantier', 'updated_at'])


@receiver(post_delete, sender=AvancementChantierUnite)
def update_unite_statut_chantier_on_delete(sender, instance, **kwargs):
    """
    Quand un AvancementChantierUnite est supprimé,
    recalculer le statut de l'unité.
    """
    unite = instance.unite
    avancements = unite.avancements_chantier.all()
    
    if avancements.exists():
        max_percentage = max([a.pourcentage for a in avancements])
        
        if max_percentage >= 100:
            unite.statut_chantier = StatutChantier.TERMINE
        else:
            unite.statut_chantier = StatutChantier.EN_COURS
    else:
        unite.statut_chantier = StatutChantier.NON_COMMENCE
    
    unite.save(update_fields=['statut_chantier', 'updated_at'])
