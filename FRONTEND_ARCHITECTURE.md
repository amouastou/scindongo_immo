# SCINDONGO Immo Frontend Architecture Guide

## Overview
The SCINDONGO Immo frontend is built using Django Templates and Bootstrap 5, organized into role-based dashboards and public pages. This document describes the architecture, file organization, and key patterns.

---

## Directory Structure

```
templates/
├── base.html                           # Base template with navbar, footer
├── includes/
│   └── _navbar.html                    # Navigation bar (header)
├── accounts/
│   ├── login.html                      # Login form (unauthenticated)
│   └── register.html                   # Registration form (unauthenticated)
├── catalog/
│   ├── programme_list.html             # List of all programmes (public)
│   ├── programme_detail.html           # Single programme detail + map (public)
│   └── unite_detail.html               # Single unit detail + map (public)
├── public/
│   ├── home.html                       # Homepage (public)
│   ├── pourquoi_investir.html          # Investment information page (public)
│   ├── contact.html                    # Contact form (public)
├── sales/
│   ├── reservation_form.html           # Reservation form (authenticated CLIENT)
│   ├── paiement_form.html              # Payment form (authenticated CLIENT)
│   └── paiement_success.html           # Payment success confirmation
├── dashboards/
│   ├── client_dashboard.html           # Client dashboard (authenticated CLIENT)
│   ├── commercial_dashboard.html       # Commercial dashboard (authenticated COMMERCIAL)
│   └── admin_dashboard.html            # Admin dashboard (authenticated ADMIN)
└── errors/
    └── 404.html / 500.html             # Error pages
```

---

## Core Components

### 1. Base Template (`templates/base.html`)
- Contains HTML skeleton (DOCTYPE, head, body)
- Includes navbar (`_navbar.html`)
- Defines `{% block content %}` for page-specific content
- Loads Bootstrap 5 CSS/JS and custom static files
- May include footer if present

### 2. Navbar (`templates/includes/_navbar.html`)
**Key Features**:
- SCINDONGO Immo branding/logo
- Public navigation: Programmes, Pourquoi investir, Contact
- Authentication state:
  - **If not authenticated**: Show "Connexion" and "Créer un compte" links
  - **If authenticated**: Show user dropdown with role-specific links
    - CLIENT: "Mon espace client" → `/ventes/client/dashboard/`
    - COMMERCIAL: "Espace commercial" → `/ventes/commercial/dashboard/`
    - ADMIN: "Espace admin" → `/ventes/admin/dashboard/`
    - All roles: "Se déconnecter" → logout action

**Guard Pattern Applied**: Checks `{% if user and user.is_authenticated %}` before accessing user attributes

---

## Page Categories

### A. Public Pages (Unauthenticated Access)

#### Homepage (`/` – `public/home.html`)
- Hero section with CTA
- Featured programmes
- Info sections (why invest, testimonials, etc.)
- No user data required

#### Programme List (`/catalogue/programmes/` – `catalog/programme_list.html`)
- Cards for each active programme
- Links to detail pages
- Filter/search (optional)

#### Programme Detail (`/catalogue/programmes/<uuid>/` – `catalog/programme_detail.html`)
- Programme name, description, address
- Leaflet map (if GPS coords provided)
- Units grid showing available/reserved/sold status
- Links to unit detail pages

#### Unit Detail (`/catalogue/unites/<uuid>/` – `catalog/unite_detail.html`)
- Unit reference, price, specs
- Status (available, reserved, sold, delivered)
- "Réserver maintenant" button → login/register if not authenticated
- Leaflet map (optional)

#### Info Pages
- `/pourquoi-investir/` – Investment benefits, market info
- `/contact/` – Contact form (optional backend processing)

---

### B. Authentication Pages

#### Login (`/comptes/login/` – `accounts/login.html`)
- Email & password inputs
- "Se connecter" button
- Link to register page
- Error messages for invalid credentials
- **Redirect behavior**:
  - Successful login → Role-based redirect (see below)
  - CLIENT → `/ventes/client/dashboard/`
  - COMMERCIAL → `/ventes/commercial/dashboard/`
  - ADMIN → `/ventes/admin/dashboard/`

#### Register (`/comptes/register/` – `accounts/register.html`)
- First name, last name, email, password, password confirm inputs
- "Créer un compte" button
- Link to login page
- Validation messages
- **Post-registration**: User needs to select role or auto-assigned as CLIENT

---

### C. Authenticated Role-Based Pages

#### Client Dashboard (`/ventes/client/dashboard/` – `dashboards/client_dashboard.html`)
**Access**: CLIENT role (enforced via `RoleRequiredMixin`)

**Layout**:
- Header: "💼 Mon espace client" + welcome greeting
- KPI Cards (4 columns):
  - Réservations (count)
  - Paiements (count)
  - Contrats (count)
  - Financements (count)
- Tabbed content:
  1. **Réservations**: Client's reserved units with status badges
     - Status: En cours, Confirmée, Annulée, Expirée
     - Actions: View details, Make payment (if en_cours)
  2. **Paiements**: Payment history
     - Columns: Date, Reservation, Amount, Method, Status
     - Status: Enregistré, Validé, Rejeté
  3. **Contrats**: Signed contracts
     - Columns: Number, Unit, Status, Sign date
     - Action: Download PDF
  4. **Financement**: Financing records
     - Columns: Bank, Type, Amount, Rate, Status
     - Status: Soumis, En étude, Accepté, Refusé, Clos
  5. **Mon profil**: User profile information
     - Display: Name, Email, Phone
     - Actions: Edit profile, Change password, Logout

**Context Variables Provided by View**:
- `reservations` – Client's reservations (QuerySet)
- `paiements` – Client's payments (QuerySet)
- `contrats` – Client's contracts (QuerySet)
- `financements` – Client's financings (QuerySet)

---

#### Commercial Dashboard (`/ventes/commercial/dashboard/` – `dashboards/commercial_dashboard.html`)
**Access**: COMMERCIAL role

**Layout**:
- Header: "📊 Tableau de bord commercial"
- KPI Cards (4 columns):
  - Clients (count)
  - Réservations (count)
  - Paiements (count)
  - Financements (count)
- Tabbed content:
  1. **Réservations**: All reservations across all clients
     - Columns: Client, Unit, Programme, Amount, Status, Date
     - Includes nested guard for `res.client.user` display
  2. **Clients**: All clients with contact info
     - Columns: Name, Email, Phone, Reservation count, Join date
     - Nested guard for `client.user` lookup
  3. **Paiements**: All payments
     - Columns: Date, Client, Amount, Method, Status, Unit
     - Nested guard for `p.reservation.client.user`
  4. **Financements**: All financing records
     - Columns: Bank, Type, Amount, Rate, Status, Client
     - Nested guard for `f.reservation.client.user`
  5. **Programmes**: Active programmes overview
     - Columns: Name, Address, Total units, Reserved, Sold, Status
     - Quick link to programme detail

**Context Variables Provided by View**:
- `clients_count`, `reservations_count`, `paiements_count`, `financements_count`
- `reservations`, `clients`, `paiements`, `financements`, `programmes` (limited to ~20 each)

---

#### Admin Dashboard (`/ventes/admin/dashboard/` – `dashboards/admin_dashboard.html`)
**Access**: ADMIN role

**Layout**:
- Header: "⚙️ Tableau de bord administrateur"
- **KPI Section 1** (4 columns):
  - Programmes (total & active count)
  - Units (total & available count)
  - Reservations (total & confirmed count)
  - Payments (total & validated count)
- **KPI Section 2** (4 cards):
  - Users by role (Clients, Commerciaux, Admins)
  - Financements (total & accepted count)
  - Contracts (total & signed count)
  - Partner banks (count)
- **Action Panel**:
  - Link to Django Admin interface
  - Placeholder buttons for export (CSV, reports)
- **Tabbed content**:
  1. **Programmes**: Table of all programmes
     - Columns: Name, Address, Units, Reserved, Sold, Status
     - Status: Actif, Brouillon, Archivé
  2. **Derniers paiements**: Recent payments (last 10)
     - Columns: Date, Client, Amount, Method, Status
     - Nested guard for `p.reservation.client.user`
  3. **Dernieres réservations**: Recent reservations (last 10)
     - Columns: Date, Client, Unit, Programme, Acompte, Status
     - Nested guard for `res.client.user`

**Context Variables Provided by View**:
- Aggregated counts (programmes, units, reservations, etc.)
- User role breakdowns
- Recent transaction lists (programmes, paiements, reservations)

---

### D. Transactional Pages

#### Reservation Form (`/ventes/reservation/start/<unite_id>/` – `sales/reservation_form.html`)
**Access**: Any user (redirects unauthenticated to login)
- Displays unit details (reference, programme, price)
- Form field: Acompte (down payment amount)
- Validates acompte ≤ unit price
- On submit: Creates Reservation and redirects to payment form

#### Payment Form (`/ventes/reservation/<id>/payer/` – `sales/paiement_form.html`)
**Access**: Authenticated CLIENT (owner of reservation)
- Displays reservation/unit info
- Form fields: Amount, Payment method, Source
- On submit: Creates Paiement record, updates reservation status
- Redirects to success page

#### Payment Success (`/ventes/paiement/success/` – `sales/paiement_success.html`)
- Confirmation message
- Reservation and payment details
- Link back to client dashboard

---

## Key Design Patterns

### 1. Defensive Template Guards
**Problem**: Template crashes if related objects are None

**Solution**: Explicit nested guards
```django
{% if object and object.related and object.related.user %}
  {{ object.related.user.email }}
{% else %}
  N/A
{% endif %}
```

**Applied to**:
- User attribute access in navbar and dashboards
- Client/User lookups in commercial and admin dashboards
- Nested reservation/client/user chains

### 2. Form Rendering Without widget_tweaks
**Problem**: `|add_class` filter is not a Django built-in

**Solution**: Use `.as_widget(attrs={...})`
```django
<!-- Before -->
{{ form.field|add_class:"form-control" }}

<!-- After -->
{{ form.field.as_widget(attrs={'class': 'form-control'}) }}
```

### 3. Status Badges
Consistent badge styling using Bootstrap classes:
```django
{% if status == 'confirmee' %}
  <span class="badge bg-success">✓ Confirmée</span>
{% elif status == 'en_cours' %}
  <span class="badge bg-warning text-dark">⏳ En cours</span>
{% else %}
  <span class="badge bg-secondary">{{ get_status_display }}</span>
{% endif %}
```

### 4. Tabbed Interfaces
Used in dashboards for organizing multiple data views:
```django
<ul class="nav nav-tabs mb-4" role="tablist">
  <li class="nav-item" role="presentation">
    <button class="nav-link active" id="tab-id" data-bs-toggle="tab" data-bs-target="#content-id">
      📋 Tab Label
    </button>
  </li>
</ul>

<div class="tab-content">
  <div class="tab-pane fade show active" id="content-id">
    <!-- Content here -->
  </div>
</div>
```

### 5. KPI Cards
Bootstrap grid with colored backgrounds:
```django
<div class="col-md-3">
  <div class="card border-0 bg-primary text-white">
    <div class="card-body">
      <h6 class="card-title text-uppercase fw-bold small">LABEL</h6>
      <h2 class="display-5 fw-bold">{{ count }}</h2>
    </div>
  </div>
</div>
```

### 6. Responsive Tables
Tables wrapped in `.table-responsive` for mobile support:
```django
<div class="table-responsive">
  <table class="table table-hover table-sm">
    <!-- Rows -->
  </table>
</div>
```

---

## Role-Based Access Control (RBAC)

### User Roles (from `accounts.models.Role`)
- `CLIENT`: Can view own reservations/payments/contracts
- `COMMERCIAL`: Can view all client data and manage sales pipeline
- `ADMIN`: Can access all dashboards and admin interface

### View-Level Enforcement
Using `RoleRequiredMixin` from `accounts.mixins`:
```python
class ClientDashboardView(RoleRequiredMixin, TemplateView):
    required_roles = ["CLIENT"]
    template_name = 'dashboards/client_dashboard.html'
```

### URL Routing
- `accounts/urls.py` – Auth pages (login, register, logout)
- `catalog/urls.py` – Public pages and details
- `sales/urls.py` – Dashboards and transactional views

### Login Redirect Logic
Implemented in `accounts.views.UserLoginView.get_success_url()`:
```python
if user.is_client:
    return '/ventes/client/dashboard/'
elif user.is_commercial:
    return '/ventes/commercial/dashboard/'
elif user.is_admin_scindongo:
    return '/ventes/admin/dashboard/'
```

---

## Static Files & Styling

### CSS Framework
- **Bootstrap 5** (CDN or local)
- Custom colors aligned with SCINDONGO branding
- Responsive grid system (12 columns)

### Icons & Emoji
- Emoji used inline for visual cues (🏢, 💼, 📊, 🔐, etc.)
- No separate icon library (keeps it simple)

### Custom Static Files
Expected locations:
- `static/css/` – Custom stylesheets
- `static/js/` – Custom JavaScript (minimal)
- `static/images/` – Logo, backgrounds, etc.

---

## Third-Party Integrations

### Maps
- **Leaflet.js** – Lightweight map library
- Used in `programme_detail.html` and `unite_detail.html` for location display
- Requires GPS coordinates from Programme/Unite models

### Charts (Future)
- For admin KPIs, consider Chart.js or similar
- Currently just displaying counts

---

## Future Enhancements

1. **Pagination**: Large tables could use Django's pagination
   - Limit initial query to ~20 rows
   - Add pagination controls for browsing

2. **Filtering & Sorting**: Add filter forms for status, date range, etc.
   - Use form with GET params for stateless filtering

3. **Export to CSV**: Admin and Commercial dashboards could export data
   - Use `django-import-export` or custom view

4. **Real-time Notifications**: WebSocket-based updates for new reservations
   - Requires Channels or Celery integration

5. **Advanced Search**: Full-text search across programmes, clients, etc.
   - Integrate Elasticsearch or PostgreSQL search

6. **Mobile App**: Consider React Native or Flutter frontend
   - Django REST API already supports this (see api/views.py)

---

## Testing Checklist

- [ ] Homepage loads and displays featured programmes
- [ ] Programme list shows all active programmes
- [ ] Programme detail displays unit grid and map
- [ ] Login form validates email/password
- [ ] Register form validates all required fields
- [ ] Authenticated CLIENT can access client dashboard
- [ ] Authenticated COMMERCIAL can access commercial dashboard
- [ ] Authenticated ADMIN can access admin dashboard
- [ ] Navbar shows role-specific links when authenticated
- [ ] Logout works and redirects to homepage
- [ ] Role-based access is enforced (e.g., CLIENT can't access COMMERCIAL dashboard)
- [ ] Reservation form creates reservation and redirects to payment
- [ ] Payment form processes payment and shows success
- [ ] Dashboard KPI counts are accurate
- [ ] No `VariableDoesNotExist` or `TemplateSyntaxError` in logs

---

## Deployment Notes

1. **Collect Static Files**: Run `python manage.py collectstatic` before deployment
2. **Template Caching**: In production, Django caches templates; clear cache on updates
3. **Debug Mode**: Set `DEBUG=False` in production (currently `DEBUG=True` in dev)
4. **CSRF**: Ensure CSRF token is present in all POST forms
5. **HTTPS**: Use HTTPS in production (configure `SECURE_SSL_REDIRECT`, `HSTS`)

---

**End of Architecture Guide**

For quick reference on template guards, see `FRONTEND_V2_PATCH_SUMMARY.md`.
For implementation details, see `FRONTEND_V2_PROGRESS_UPDATED.md`.
