import hashlib
import io
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.formats import date_format, number_format
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from sales.models import Contrat
from sales.utils import calculer_montant_caution


COMPANY_NAME = getattr(settings, "PROJECT_NAME", "SCINDONGO Immo")
COMPANY_CITY = getattr(settings, "COMPANY_CITY", "Dakar, Sénégal")
COMPANY_SLOGAN = getattr(settings, "COMPANY_SLOGAN", "Solutions immobilières sur mesure")


def _format_amount(amount) -> str:
    if amount is None:
        return "-"
    return f"{number_format(amount, decimal_pos=0, force_grouping=True)} FCFA"


def _draw_table(pdf, items, start_x, start_y, label_width, value_width, leading=16):
    y = start_y
    for label, value in items:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(start_x, y, f"{label} :")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(start_x + label_width, y, value or "-")
        y -= leading
    return y


def _draw_paragraph(pdf, text: str, start_x, start_y, max_width, leading=14):
    if not text:
        return start_y
    pdf.setFont("Helvetica", 10)
    y = start_y
    for paragraph in text.splitlines() or [""]:
        lines = simpleSplit(paragraph or " ", "Helvetica", 10, max_width)
        for line in lines:
            pdf.drawString(start_x, y, line)
            y -= leading
        y -= leading / 2
    return y


def _pdf_filename(contrat: Contrat, timestamp) -> str:
    return f"contrat_{str(contrat.id)[:8]}_{timestamp.strftime('%Y%m%d%H%M%S')}.pdf"


def generate_contract_pdf(contrat: Optional[Contrat], generated_by=None):
    """Génère (ou régénère) le PDF du contrat avec les informations éditables."""
    if not contrat:
        return None

    if contrat.pdf:
        contrat.pdf.delete(save=False)

    timestamp = timezone.now()
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin
    reservation = contrat.reservation
    programme = reservation.unite.programme
    operation_type_label = programme.get_type_operation_display()
    is_location = reservation.is_location()
    caution_amount = None
    if is_location:
        try:
            caution_amount = calculer_montant_caution(reservation)
        except Exception:
            caution_amount = None

    # Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, f"{COMPANY_NAME} - Contrat Immobilier")
    y -= 18
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, f"N° {contrat.numero}")
    y -= 16
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, COMPANY_SLOGAN)
    y -= 32

    # Bloc Contrat
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Informations Contrat")
    y -= 18
    y = _draw_table(
        pdf,
        [
            ("Date de signature", date_format(contrat.date_signature or timezone.localdate(), "d/m/Y")),
            ("Date de fin", date_format(contrat.date_fin, "d/m/Y") if contrat.date_fin else "-"),
            ("Lieu", contrat.lieu_signature or COMPANY_CITY),
            ("Statut", contrat.get_statut_display() if hasattr(contrat, "get_statut_display") else contrat.statut),
            (
                "Commercial",
                contrat.commercial_nom
                or (getattr(generated_by, "get_full_name", lambda: "")() or getattr(generated_by, "email", ""))
                or COMPANY_NAME,
            ),
            ("Contact commercial", contrat.commercial_email or getattr(generated_by, "email", "-")),
        ],
        start_x=margin,
        start_y=y,
        label_width=120,
        value_width=width - (2 * margin) - 120,
    )
    y -= 15

    # Bloc Client
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Partie Client")
    y -= 18
    y = _draw_table(
        pdf,
        [
            ("Nom", contrat.client_nom or "-"),
            ("Email", contrat.client_email or "-"),
            ("Téléphone", contrat.client_telephone or "-"),
            ("Adresse", contrat.client_adresse or "-"),
        ],
        start_x=margin,
        start_y=y,
        label_width=120,
        value_width=width - (2 * margin) - 120,
    )
    y -= 15

    # Bloc Bien
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Bien concerné")
    y -= 18
    y = _draw_table(
        pdf,
        [
            ("Programme", contrat.programme_nom or "-"),
            ("Référence lot", contrat.unite_reference or "-"),
            ("Description", contrat.unite_description or "-"),
            ("Type d'opération", operation_type_label),
            ("Montant", _format_amount(contrat.montant_total)),
            (
                "Caution",
                _format_amount(caution_amount) if caution_amount else ("Non applicable" if not is_location else "-")
            ),
        ],
        start_x=margin,
        start_y=y,
        label_width=120,
        value_width=width - (2 * margin) - 120,
    )
    y -= 10

    # Conditions
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Conditions générales")
    y -= 18
    y = _draw_paragraph(pdf, contrat.conditions_generales, margin, y, width - 2 * margin)
    y -= 10

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Conditions particulières")
    y -= 18
    y = _draw_paragraph(pdf, contrat.conditions_particulieres, margin, y, width - 2 * margin)

    if y < margin:
        pdf.showPage()
        y = height - margin

    pdf.setFont("Helvetica", 9)
    pdf.drawString(margin, y - 10, f"Document généré automatiquement le {timestamp.strftime('%d/%m/%Y %H:%M')}")
    pdf.drawRightString(width - margin, y - 10, COMPANY_CITY)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    file_bytes = buffer.getvalue()
    filename = _pdf_filename(contrat, timestamp)
    contrat.pdf.save(filename, ContentFile(file_bytes), save=False)
    contrat.pdf_hash = hashlib.sha256(file_bytes).hexdigest()
    contrat.generated_pdf = True
    contrat.save(update_fields=["pdf", "pdf_hash", "generated_pdf"])
    return filename
