from __future__ import annotations

import io
from typing import Any, Dict

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.formats import number_format
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from sales.models import Paiement


COMPANY_NAME = getattr(settings, "PROJECT_NAME", "SCINDONGO Immo")
COMPANY_CITY = getattr(settings, "COMPANY_CITY", "Dakar, Sénégal")


def _format_amount(value) -> str:
    return f"{number_format(value, decimal_pos=0, force_grouping=True)} FCFA"


def _receipt_filename(paiement: Paiement, timestamp) -> str:
    return f"recu_{str(paiement.id)[:8]}_{timestamp.strftime('%Y%m%d%H%M%S')}.pdf"


def _receipt_number(paiement: Paiement, timestamp) -> str:
    return f"REC-{timestamp.strftime('%Y%m%d')}-{str(paiement.id)[:6].upper()}"


def generate_payment_receipt(paiement: Paiement, validated_by) -> Dict[str, Any]:
    """Generate and attach a PDF receipt for a validated payment."""
    if not paiement:
        return {}

    if paiement.recu_pdf:
        paiement.recu_pdf.delete(save=False)

    timestamp = timezone.now()
    receipt_no = _receipt_number(paiement, timestamp)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, f"{COMPANY_NAME} - Reçu de paiement")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y - 18, COMPANY_CITY)
    pdf.drawRightString(width - margin, y, f"N° {receipt_no}")

    y -= 40

    client = paiement.reservation.client
    unite = paiement.reservation.unite
    programme = unite.programme

    details = [
        ("Date paiement", paiement.date_paiement.strftime("%d/%m/%Y")),
        ("Montant", _format_amount(paiement.montant)),
        ("Moyen", paiement.get_moyen_display()),
        ("Type", paiement.get_type_paiement_display()),
        ("Client", f"{client.prenom} {client.nom}".strip()),
        ("Téléphone", client.telephone or "-"),
        ("Programme", programme.nom),
        ("Référence lot", unite.reference_lot),
        (
            "Commercial",
            (validated_by.get_full_name() or "").strip() or validated_by.email,
        ),
        ("Validé le", timestamp.strftime("%d/%m/%Y %H:%M")),
    ]

    pdf.setFont("Helvetica", 11)
    for label, value in details:
        pdf.drawString(margin, y, f"{label} :")
        pdf.drawString(margin + 120, y, str(value))
        y -= 18

    y -= 10
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(margin, y, "Ce reçu atteste la bonne réception du paiement. Conservez-le pour vos archives.")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    filename = _receipt_filename(paiement, timestamp)
    paiement.recu_pdf.save(filename, ContentFile(buffer.read()), save=False)

    metadata = {
        "receipt_number": receipt_no,
        "generated_at": timestamp.isoformat(),
        "validated_by": getattr(validated_by, "email", None),
        "client_name": f"{client.prenom} {client.nom}".strip(),
        "programme": programme.nom,
        "unite_reference": unite.reference_lot,
        "amount": float(paiement.montant),
        "moyen": paiement.moyen,
        "type": paiement.type_paiement,
    }
    paiement.recu_meta = metadata
    paiement.recu_emis_le = timestamp
    paiement.save(update_fields=["recu_pdf", "recu_meta", "recu_emis_le"])
    return metadata
