# 📋 PLAN INTÉGRATION DOCUMENTS KYC - SANS RÉGRESSION

**Date:** 4 Décembre 2025  
**Branche:** `dev`  
**Objectif:** Ajouter document upload sans casser workflows existants

---

## 🎯 ARCHITECTURE ACTUELLE

### Backend Structure
```
sales/
├─ models.py
│  ├─ Client (kyc_statut = vide, jamais utilisé)
│  ├─ Reservation (statut: en_cours, confirmee, annulee, expiree)
│  └─ Financement (statut: soumis, en_etude, accepte, refuse, clos)
├─ views.py (Django templates + API)
├─ forms.py (ReservationForm, FinancementForm, etc)
└─ urls.py

api/
├─ views.py
│  ├─ ReservationViewSet (GET/POST/PATCH/DELETE)
│  └─ FinancementViewSet (GET/POST/PATCH/DELETE)
├─ serializers.py (ReservationSerializer, FinancementSerializer)
└─ urls.py (Router DRF)

core/
└─ models.py
   └─ Document (polymorphe: objet_type, objet_id)
```

### Current Workflows
```
RÉSERVATION WORKFLOW (steps 1-8)
1. Client crée compte
2. Client selectionne bien (Unite)
3. Client fait réservation (acompte)
   ✅ Réservation créée immédiatement (AUCUNE vérification document!)
4. Commercial confirme
5. Client signe contrat
6. Paiements
7-8. Financement

FINANCEMENT WORKFLOW
1. Client demande financement
   ✅ Financement créé immédiatement (AUCUNE vérification document!)
2. Commercial soumet à banque
3. Banque accepte/refuse
4. Échéances générées
```

**⚠️ PROBLÈME:** Documents jamais vérifiés avant réservation/financement

---

## 🔧 PLAN INTÉGRATION (NON-BREAKING)

### ÉTAPE 1: Créer modèles polymorphes (SAFE ✅)

**Fichier:** `sales/models.py`

**Action:** Ajouter APRÈS Echeance:
```python
class ReservationDocument(TimeStampedModel):
    """Documents pour étape réservation"""
    DOCUMENT_TYPES = [
        ('cni', 'CNI'),
        ('photo', 'Photo/Selfie'),
        ('residence', 'Preuve de résidence'),
    ]
    STATUS_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]
    
    reservation = ForeignKey(Reservation, on_delete=CASCADE, related_name='documents')
    document_type = CharField(max_length=50, choices=DOCUMENT_TYPES)
    fichier = FileField(upload_to='documents/reservations/%Y/%m/')
    statut = CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    raison_rejet = TextField(blank=True)
    verifie_par = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True)
    verifie_le = DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('reservation', 'document_type')
        ordering = ['-created_at']

class FinancementDocument(TimeStampedModel):
    """Documents pour étape financement"""
    DOCUMENT_TYPES = [
        ('brochure', 'Brochure programme'),
        ('cni', 'CNI'),
        ('bulletin_salaire', 'Bulletin de salaire'),
        ('rib_ou_iban', 'RIB ou IBAN'),
        ('attestation_employeur', 'Attestation employeur'),
    ]
    STATUS_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]
    
    financement = ForeignKey(Financement, on_delete=CASCADE, related_name='documents')
    document_type = CharField(max_length=50, choices=DOCUMENT_TYPES)
    fichier = FileField(upload_to='documents/financements/%Y/%m/')
    statut = CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    raison_rejet = TextField(blank=True)
    verifie_par = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True)
    verifie_le = DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('financement', 'document_type')
        ordering = ['-created_at']
```

**Impact:** ✅ Non-breaking (nouveaux modèles uniquement)

---

### ÉTAPE 2: Migration Django (SAFE ✅)

**Fichier:** Auto-généré par Django

```bash
python manage.py makemigrations sales
python manage.py migrate
```

**Impact:** ✅ Non-breaking (ajoute tables, ne modifie pas existantes)

---

### ÉTAPE 3: Ajouter Serializers (SAFE ✅)

**Fichier:** `api/serializers.py`

**Action:** Ajouter à la fin:
```python
class ReservationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationDocument
        fields = ['id', 'document_type', 'fichier', 'statut', 'raison_rejet', 'created_at']
        read_only_fields = ['id', 'created_at', 'statut', 'raison_rejet']

class FinancementDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancementDocument
        fields = ['id', 'document_type', 'fichier', 'statut', 'raison_rejet', 'created_at']
        read_only_fields = ['id', 'created_at', 'statut', 'raison_rejet']

# Mettre à jour ReservationSerializer pour inclure documents
class ReservationSerializer(serializers.ModelSerializer):
    documents = ReservationDocumentSerializer(many=True, read_only=True)
    # ... reste du code
    class Meta:
        model = Reservation
        fields = [..., 'documents']  # Ajouter à list

# Mettre à jour FinancementSerializer pour inclure documents
class FinancementSerializer(serializers.ModelSerializer):
    documents = FinancementDocumentSerializer(many=True, read_only=True)
    # ... reste du code
    class Meta:
        model = Financement
        fields = [..., 'documents']  # Ajouter à list
```

**Impact:** ✅ Non-breaking (nested serializers read-only)

---

### ÉTAPE 4: Ajouter ViewSets (SAFE ✅)

**Fichier:** `api/views.py`

**Action:** Ajouter avant ReservationViewSet:
```python
class ReservationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationDocumentSerializer
    permission_classes = [IsAuthenticated, IsClientOwnerOrAdminOrCommercial]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["document_type", "statut"]

    def get_queryset(self):
        """Chaque user ne voit que SES documents"""
        user = self.request.user
        if getattr(user, "is_admin_scindongo", False) or getattr(user, "is_commercial", False):
            return ReservationDocument.objects.all()
        
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return ReservationDocument.objects.filter(reservation__client=client_profile)
        
        return ReservationDocument.objects.none()

class FinancementDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = FinancementDocumentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["document_type", "statut"]

    def get_queryset(self):
        """Chaque user ne voit que SES documents"""
        user = self.request.user
        if getattr(user, "is_admin_scindongo", False) or getattr(user, "is_commercial", False):
            return FinancementDocument.objects.all()
        
        client_profile = getattr(user, "client_profile", None)
        if client_profile:
            return FinancementDocument.objects.filter(financement__reservation__client=client_profile)
        
        return FinancementDocument.objects.none()
```

**Action:** Ajouter routes au router dans `api/urls.py`:
```python
router.register("reservations/documents", ReservationDocumentViewSet, basename="reservation-documents")
router.register("financements/documents", FinancementDocumentViewSet, basename="financing-documents")
```

**Impact:** ✅ Non-breaking (nouveaux endpoints, pas de modification)

---

### ÉTAPE 5: Services de validation (SAFE ✅)

**Fichier:** Créer `sales/document_services.py` (NOUVEAU)

```python
class ReservationDocumentService:
    REQUIRED_DOCUMENTS = ['cni', 'photo', 'residence']
    
    @staticmethod
    def can_make_reservation(reservation):
        """Vérifier que TOUS les docs requis sont validés"""
        for doc_type in ReservationDocumentService.REQUIRED_DOCUMENTS:
            doc = ReservationDocument.objects.filter(
                reservation=reservation,
                document_type=doc_type,
                statut='valide'
            ).exists()
            
            if not doc:
                return False, f"Document '{doc_type}' manquant ou non validé"
        
        return True, "Tous les documents validés"

class FinancementDocumentService:
    REQUIRED_DOCUMENTS = ['brochure', 'cni', 'bulletin_salaire', 'rib_ou_iban']
    OPTIONAL_DOCUMENTS = ['attestation_employeur']
    
    @staticmethod
    def can_request_financing(financement):
        """Vérifier que TOUS les docs requis sont validés"""
        for doc_type in FinancementDocumentService.REQUIRED_DOCUMENTS:
            doc = FinancementDocument.objects.filter(
                financement=financement,
                document_type=doc_type,
                statut='valide'
            ).exists()
            
            if not doc:
                return False, f"Document '{doc_type}' manquant ou non validé"
        
        return True, "Tous les documents validés"
```

**Impact:** ✅ Non-breaking (nouveau service, pas de modification)

---

### ÉTAPE 6: Ajouter validations optionnelles (SEMI-BREAKING ⚠️)

**Fichier:** `api/views.py` - Modifier ReservationViewSet.perform_create()

```python
class ReservationViewSet(viewsets.ModelViewSet):
    # ... code existant ...
    
    def perform_create(self, serializer):
        """
        ⚠️ OPTION 1 (Recommandé): Validation DOUCE - avertissements
        ⚠️ OPTION 2: Validation STRICTE - bloquer création
        """
        reservation = serializer.save()
        
        # OPTION 1 - Avertissement uniquement
        can_create, msg = ReservationDocumentService.can_make_reservation(reservation)
        if not can_create:
            audit_log(self.request.user, reservation, 'reservation_created_sans_docs', 
                     {'avertissement': msg}, self.request)
        
        # OU OPTION 2 - Bloquer (BREAKING!)
        # if not can_create:
        #     raise ValidationError(msg)
```

**Impact:** 
- **OPTION 1 (Douce):** ✅ Non-breaking - création continue
- **OPTION 2 (Stricte):** ⚠️ **BREAKING** - création impossible sans docs

**RECOMMANDATION:** Commencer par OPTION 1 (log avertissement), puis passer à OPTION 2 après tests

---

### ÉTAPE 7: Formulaires upload Django (SAFE ✅)

**Fichier:** `sales/forms.py`

```python
class ReservationDocumentForm(forms.ModelForm):
    class Meta:
        model = ReservationDocument
        fields = ['document_type', 'fichier']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
        }
    
    def clean_fichier(self):
        fichier = self.cleaned_data['fichier']
        if fichier.size > 5 * 1024 * 1024:  # 5MB
            raise ValidationError('Fichier trop volumineux (max 5MB)')
        if fichier.content_type not in ['application/pdf', 'image/jpeg', 'image/png']:
            raise ValidationError('Format non autorisé (PDF, JPG, PNG)')
        return fichier

class FinancementDocumentForm(forms.ModelForm):
    class Meta:
        model = FinancementDocument
        fields = ['document_type', 'fichier']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
        }
    
    def clean_fichier(self):
        fichier = self.cleaned_data['fichier']
        if fichier.size > 5 * 1024 * 1024:  # 5MB
            raise ValidationError('Fichier trop volumineux (max 5MB)')
        if fichier.content_type not in ['application/pdf', 'image/jpeg', 'image/png']:
            raise ValidationError('Format non autorisé (PDF, JPG, PNG)')
        return fichier
```

**Impact:** ✅ Non-breaking (nouveaux formulaires)

---

### ÉTAPE 8: Vues Django templates (SAFE ✅)

**Fichier:** Créer `sales/views_documents.py` (NOUVEAU)

```python
class ReservationDocumentUploadView(RoleRequiredMixin, CreateView):
    model = ReservationDocument
    form_class = ReservationDocumentForm
    template_name = 'sales/reservation_document_upload.html'
    required_roles = ["CLIENT"]
    
    def get_reservation(self):
        return get_object_or_404(Reservation, id=self.kwargs['reservation_id'], 
                                client=self.request.user.client_profile)
    
    def form_valid(self, form):
        doc = form.save(commit=False)
        doc.reservation = self.get_reservation()
        doc.save()
        audit_log(self.request.user, doc, 'reservation_document_uploaded', {}, self.request)
        messages.success(self.request, 'Document uploadé')
        return redirect('reservation_documents', reservation_id=doc.reservation.id)

class ReservationDocumentListView(RoleRequiredMixin, ListView):
    model = ReservationDocument
    template_name = 'sales/reservation_document_list.html'
    context_object_name = 'documents'
    required_roles = ["CLIENT", "COMMERCIAL", "ADMIN"]
    
    def get_queryset(self):
        reservation = get_object_or_404(Reservation, id=self.kwargs['reservation_id'])
        return reservation.documents.all()
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = get_object_or_404(Reservation, id=self.kwargs['reservation_id'])
        ctx['reservation'] = reservation
        ctx['can_reserve'] = ReservationDocumentService.can_make_reservation(reservation)[0]
        return ctx
```

**Impact:** ✅ Non-breaking (nouvelles vues)

---

### ÉTAPE 9: Admin Django (SAFE ✅)

**Fichier:** `sales/admin.py`

```python
class ReservationDocumentInline(admin.TabularInline):
    model = ReservationDocument
    extra = 0
    fields = ['document_type', 'statut', 'raison_rejet', 'verifie_par', 'verifie_le']
    readonly_fields = ['created_at', 'updated_at']

class FinancementDocumentInline(admin.TabularInline):
    model = FinancementDocument
    extra = 0
    fields = ['document_type', 'statut', 'raison_rejet', 'verifie_par', 'verifie_le']
    readonly_fields = ['created_at', 'updated_at']

# Modifier ReservationAdmin
class ReservationAdmin(admin.ModelAdmin):
    inlines = [ReservationDocumentInline]
    # ... reste du code

# Modifier FinancementAdmin
class FinancementAdmin(admin.ModelAdmin):
    inlines = [FinancementDocumentInline]
    # ... reste du code
```

**Impact:** ✅ Non-breaking (interface admin seulement)

---

## 🚨 STRATÉGIE DÉPLOIEMENT SANS RÉGRESSION

### Phase 1: Infrastructure (NON-BREAKING)
1. ✅ Étapes 1-5: Modèles + Services + API
2. ✅ Étapes 7-9: Formulaires + Admin
3. **Aucun client affecté** - Réservations continuent à fonctionner
4. **Commerciaux commencent à utiliser** l'admin pour valider docs

### Phase 2: Validation DOUCE (SEMI-BREAKING)
1. Activer OPTION 1 (avertissements seulement)
2. Logs des réservations sans docs
3. **Clients informés** de faire uploads
4. **Durée:** 2-4 semaines observation

### Phase 3: Validation STRICTE (BREAKING)
1. Après feedback + ajustements
2. Activer OPTION 2 (blocage à la création)
3. **Plus de réservation sans docs**
4. **Clients doivent uploader avant**

---

## ✅ CHECKLIST IMPLÉMENTATION

```
BACKEND
  □ Étape 1: Modèles ReservationDocument + FinancementDocument
  □ Étape 2: Migration
  □ Étape 3: Serializers (nested dans Reservation/Financement)
  □ Étape 4: ViewSets + Router
  □ Étape 5: Services de validation
  □ Étape 6: Validation performCreate (DOUCE d'abord)
  □ Étape 7: Formulaires Django
  □ Étape 8: Vues templates
  □ Étape 9: Admin Django
  
TESTS
  □ Test upload fichier via API
  □ Test validation fichier (taille, format)
  □ Test unique_together (un doc/type par reservation)
  □ Test permissions (client voit que ses docs)
  □ Test admin validation (commercial peut valider/rejeter)
  □ Test service de validation (can_make_reservation)
  
DOCUMENTATION
  □ Mettre à jour API documentation
  □ Créer guide upload pour clients
  □ Créer guide validation pour commerciaux
```

---

## 🔄 ROLLBACK PLAN

Si problème:

```bash
# Revenir à main
git checkout main

# Ou si sur dev:
git reset --hard origin/dev

# Descendre migration
python manage.py migrate sales <numero_avant_migration>
```

**Aucune donnée perdue** - les nouveaux modèles ne touchent pas données existantes

---

## 📝 NOTES IMPORTANTES

1. **TimeStampedModel:** Hériter de lui pour UUID auto + timestamps
2. **Polymorphe:** Documents indépendants par reservation/financement
3. **Permissions:** Clients ne voient QUE leurs docs (via get_queryset)
4. **Validation:** Service réutilisable dans API et templates
5. **Audit:** Chaque upload/validation loggé via audit_log
6. **Fichiers:** Upload dans `media/documents/` avec structure année/mois
7. **Admin:** Inline pour voir docs directement dans Reservation

---

## 🎯 COMMANDE START

```bash
# Checkout dev
git checkout dev

# Créer commit initial
git add .
git commit -m "feat(documents): add document models and services

- Add ReservationDocument model (cni, photo, residence)
- Add FinancementDocument model (brochure, cni, salary, rib_iban)
- Add document services for validation
- Add serializers and viewsets for API
- Backward compatible - no workflow changes yet"
```

---

**Prêt à commencer étape 1 ? 🚀**
