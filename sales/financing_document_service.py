"""Service pour gérer les documents de financement"""

from sales.models import FinancementDocument


class FinancementDocumentService:
    """Service pour valider et gérer les documents de financement"""
    
    REQUIRED_DOCUMENTS = [
        ('brochure', 'Brochure du programme'),
        ('cni', 'CNI'),
        ('bulletin_salaire', 'Bulletin de salaire'),
        ('rib_ou_iban', 'RIB ou IBAN'),
        ('attestation_employeur', "Attestation d'employeur"),
    ]
    
    @staticmethod
    def can_proceed_financing(financement):
        """
        Vérifier si tous les documents de financement sont validés.
        
        Returns:
            tuple: (bool, message)
        """
        docs_valides = financement.documents.filter(statut='valide').count()
        total_docs = len(FinancementDocumentService.REQUIRED_DOCUMENTS)
        
        if docs_valides == total_docs:
            return (True, "Tous les documents de financement sont validés")
        
        return (False, f"{docs_valides}/{total_docs} documents validés")
    
    @staticmethod
    def get_missing_documents(financement):
        """
        Retourner la liste des documents manquants ou non validés.
        
        Returns:
            list: [{'type': 'cni', 'label': 'CNI'}, ...]
        """
        missing = []
        
        for doc_type, label in FinancementDocumentService.REQUIRED_DOCUMENTS:
            doc = financement.documents.filter(document_type=doc_type).first()
            
            if not doc or doc.statut != 'valide':
                missing.append({
                    'type': doc_type,
                    'label': label,
                    'status': doc.statut if doc else 'missing'
                })
        
        return missing
    
    @staticmethod
    def get_documents_status(financement):
        """
        Retourner un dict avec le statut de tous les documents.
        
        Returns:
            dict: {'cni': {'statut': 'valide', 'created_at': ...}, ...}
        """
        status = {}
        
        for doc in financement.documents.all():
            status[doc.document_type] = {
                'statut': doc.statut,
                'created_at': doc.created_at,
                'verifie_par': doc.verifie_par,
                'verifie_le': doc.verifie_le,
                'raison_rejet': doc.raison_rejet,
            }
        
        return status
