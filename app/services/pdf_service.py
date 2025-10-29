"""
PDF Generation Service
Create insurance policy contract PDFs using reportlab
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import date
from pathlib import Path
import os

from app.models.policy import Policy


class PDFService:
    """
    Service for generating insurance policy contract PDFs.

    WHY PDF generation matters:
    - Legal requirement: Insurance contracts must be documented
    - Customer deliverable: Policy holder needs physical/digital copy
    - Compliance: Regulatory bodies require signed contracts
    - Broker tool: Printable version for customer meetings

    WHY reportlab:
    - Python-native (no external dependencies like wkhtmltopdf)
    - Precise control over layout
    - Industry-standard for PDF generation
    - Works in Docker/serverless environments

    ALTERNATIVE CONSIDERED:
    - WeasyPrint: HTML → PDF (easier but less control)
    - wkhtmltopdf: Requires binary installation
    - LaTeX: Overkill for simple contracts

    PDF STRUCTURE:
    1. Header (company logo, policy number)
    2. Policy details table
    3. Coverage information
    4. Terms and conditions
    5. Signature section
    """

    # PDF storage directory
    PDF_STORAGE_DIR = Path("storage/policy_pdfs")

    @classmethod
    def _ensure_storage_dir(cls):
        """Create storage directory if it doesn't exist"""
        cls.PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def generate_policy_pdf(cls, policy: Policy) -> bytes:
        """
        Generate PDF contract for an insurance policy.

        Creates a professional-looking policy document with:
        - Company header
        - Policy details (number, dates, premium)
        - Coverage information
        - Terms and conditions
        - Signature section

        Args:
            policy: Policy object with all details loaded

        Returns:
            PDF bytes (can be saved to file or returned in HTTP response)

        Example:
            policy = db.query(Policy).filter(Policy.id == 123).first()
            pdf_bytes = PDFService.generate_policy_pdf(policy)

            # Save to file
            with open("policy.pdf", "wb") as f:
                f.write(pdf_bytes)

            # Or return in FastAPI
            return Response(content=pdf_bytes, media_type="application/pdf")
        """
        from io import BytesIO

        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=12,
            spaceBefore=12
        )
        normal_style = styles['Normal']

        # Build PDF content
        story = []

        # Title
        story.append(Paragraph("INSURANCE POLICY CONTRACT", title_style))
        story.append(Spacer(1, 0.5*cm))

        # Policy number (prominent)
        policy_num_style = ParagraphStyle(
            'PolicyNumber',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        story.append(Paragraph(f"Policy Number: <b>{policy.policy_number}</b>", policy_num_style))
        story.append(Spacer(1, 1*cm))

        # Policy details table
        story.append(Paragraph("Policy Details", heading_style))

        policy_data = [
            ["Policy Number:", policy.policy_number],
            ["Status:", policy.status.value.upper()],
            ["Start Date:", policy.start_date.strftime("%B %d, %Y")],
            ["End Date:", policy.end_date.strftime("%B %d, %Y")],
            ["Renewal Date:", policy.renewal_date.strftime("%B %d, %Y") if policy.renewal_date else "N/A"],
            ["Annual Premium:", f"€{policy.quote.annual_premium:,.2f}"],
            ["Monthly Premium:", f"€{policy.quote.monthly_premium:,.2f}"],
        ]

        policy_table = Table(policy_data, colWidths=[6*cm, 10*cm])
        policy_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(policy_table)
        story.append(Spacer(1, 1*cm))

        # Insured party information
        story.append(Paragraph("Insured Party", heading_style))

        prospect = policy.quote.prospect
        insured_data = [
            ["Name:", f"{prospect.first_name} {prospect.last_name}"],
            ["Type:", prospect.type.value.capitalize()],
            ["Email:", prospect.email or "N/A"],
            ["Phone:", prospect.phone or "N/A"],
            ["Tax Code:", prospect.tax_code or "N/A"],
        ]

        insured_table = Table(insured_data, colWidths=[6*cm, 10*cm])
        insured_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(insured_table)
        story.append(Spacer(1, 1*cm))

        # Coverage details
        story.append(Paragraph("Coverage Information", heading_style))

        coverage_data = [
            ["Provider:", policy.quote.provider.upper()],
            ["Insurance Type:", policy.quote.insurance_type.capitalize()],
            ["Coverage Amount:", f"€{policy.quote.coverage_amount:,.2f}"],
            ["Deductible:", f"€{policy.quote.deductible:,.2f}" if policy.quote.deductible else "None"],
        ]

        coverage_table = Table(coverage_data, colWidths=[6*cm, 10*cm])
        coverage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(coverage_table)
        story.append(Spacer(1, 1.5*cm))

        # Terms and conditions
        story.append(Paragraph("Terms and Conditions", heading_style))

        terms_text = """
        This insurance policy is subject to the following terms and conditions:
        <br/><br/>
        1. <b>Coverage Period:</b> This policy is valid from the start date to the end date specified above.
        Renewal is subject to timely premium payment and policy review.
        <br/><br/>
        2. <b>Premium Payment:</b> Premiums must be paid according to the agreed schedule. Failure to pay
        premiums may result in policy cancellation.
        <br/><br/>
        3. <b>Claims Process:</b> All claims must be reported within 30 days of the incident. Claims are
        subject to deductible and policy limits.
        <br/><br/>
        4. <b>Cancellation:</b> Either party may cancel this policy with 30 days written notice.
        Pro-rated refunds will be issued for unused coverage periods.
        <br/><br/>
        5. <b>Policy Modification:</b> Any changes to this policy must be agreed upon in writing by both parties.
        <br/><br/>
        6. <b>Governing Law:</b> This policy is governed by the laws of Italy.
        """

        story.append(Paragraph(terms_text, normal_style))
        story.append(Spacer(1, 1.5*cm))

        # Signature section
        story.append(Paragraph("Signatures", heading_style))

        signature_text = f"""
        <br/>
        By signing below, the parties acknowledge and agree to the terms of this insurance policy.
        <br/><br/><br/>
        ______________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        ______________________________<br/>
        Insured Party&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        Insurance Provider<br/>
        Date: {date.today().strftime("%B %d, %Y")}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        Date: {date.today().strftime("%B %d, %Y")}
        """

        story.append(Paragraph(signature_text, normal_style))
        story.append(Spacer(1, 1*cm))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        footer_text = f"""
        <br/><br/>
        Generated on {date.today().strftime("%B %d, %Y")} | Policy Number: {policy.policy_number}<br/>
        Insurance CRM System | For inquiries: support@insurancecrm.com
        """
        story.append(Paragraph(footer_text, footer_style))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    @classmethod
    def save_policy_pdf(cls, policy: Policy, pdf_bytes: bytes) -> str:
        """
        Save PDF bytes to file system.

        Args:
            policy: Policy object
            pdf_bytes: PDF content as bytes

        Returns:
            Relative path to saved PDF file

        Example:
            pdf_bytes = PDFService.generate_policy_pdf(policy)
            pdf_path = PDFService.save_policy_pdf(policy, pdf_bytes)
            # Returns: "storage/policy_pdfs/POL-2025-000123.pdf"
        """
        cls._ensure_storage_dir()

        # Generate filename from policy number
        filename = f"{policy.policy_number}.pdf"
        file_path = cls.PDF_STORAGE_DIR / filename

        # Write PDF to file
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Return relative path (for storing in database)
        return str(file_path)

    @classmethod
    def generate_and_save(cls, policy: Policy) -> str:
        """
        Generate PDF and save to file system (convenience method).

        Args:
            policy: Policy object

        Returns:
            Path to saved PDF file

        Example:
            policy = db.query(Policy).filter(Policy.id == 123).first()
            pdf_path = PDFService.generate_and_save(policy)

            # Update policy record
            policy.pdf_path = pdf_path
            db.commit()
        """
        pdf_bytes = cls.generate_policy_pdf(policy)
        pdf_path = cls.save_policy_pdf(policy, pdf_bytes)
        return pdf_path
