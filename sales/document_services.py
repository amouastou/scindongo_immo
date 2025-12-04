"""Services pour validation des documents de réservation et financement"""

from .models import ReservationDocument


class ReservationDocumentService:
    """Service pour valider les documents requis à la réservation"""
    
    REQUIRED_DOCUMENTS = ['cni', 'photo', 'residence']
    
    @staticmethod
    def can_make_reservation(reservation):
        """
        Vérifier que TOUS les documents requis sont validés
        
        Returns:
            tuple: (bool, str) - (peut créer réservation, message)
        """
        for doc_type in ReservationDocumentService.REQUIRED_DOCUMENTS:
            doc = ReservationDocument.objects.filter(
                reservation=reservation,
                document_type=doc_type,
                statut='valide'
            ).exists()
            
            if not doc:
                label = dict(ReservationDocument.DOCUMENT_TYPES).get(doc_type, doc_type)
                return False, f"Document '{label}' manquant ou non validé"
        
        return True, "Tous les documents validés ✅"
    
    @staticmethod
    def get_missing_documents(reservation):
        """
        Retourner liste des documents manquants ou invalides
        
        Returns:
            list: Liste des documents manquants
        """
        missing = []
        
        for doc_type in ReservationDocumentService.REQUIRED_DOCUMENTS:
            doc = ReservationDocument.objects.filter(
                reservation=reservation,
                document_type=doc_type,
                statut='valide'
            ).exists()
            
            if not doc:
                label = dict(ReservationDocument.DOCUMENT_TYPES).get(doc_type, doc_type)
                missing.append({
                    'type': doc_type,
                    'label': label
                })
        
        return missing
    
    @staticmethod
    def get_documents_status(reservation):
        """
        Retourner status de tous les documents requis
        
        Returns:
            dict: Dict avec document_type -> statut
        """
        status_dict = {}
        
        for doc_type in ReservationDocumentService.REQUIRED_DOCUMENTS:
            doc = ReservationDocument.objects.filter(
                reservation=reservation,
                document_type=doc_type
            ).first()
            
            if doc:
                status_dict[doc_type] = {
                    'statut': doc.statut,
                    'raison_rejet': doc.raison_rejet if doc.statut == 'rejete' else None
                }
            else:
                status_dict[doc_type] = {
                    'statut': 'non_fourni',
                    'raison_rejet': None
                }
        
        return status_dict
