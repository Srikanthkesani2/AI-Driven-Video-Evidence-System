import datetime
from pathlib import Path
from typing import List
from application.interfaces import IPdfGenerator
from domain.models import ForensicReport, TimelineEvent, CaseStatus, RiskLevel
from utils.logger import logger

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab library not available. Fallback PDF text generator will be used.")

class PdfGenerator(IPdfGenerator):
    def generate_forensic_pdf(self, report: ForensicReport) -> Path:
        output_dir = Path(report.pdf_path).parent if report.pdf_path else Path("data/processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_filename = f"forensic_report_{report.case_id}.pdf"
        pdf_path = output_dir / pdf_filename
        
        logger.info(f"Generating PDF forensic report at: {pdf_path}")
        
        if not REPORTLAB_AVAILABLE:
            # Simple text fallback if reportlab compilation fails
            with open(pdf_path, "w") as f:
                f.write(f"FORENSIC REPORT: {report.case_id}\n")
                f.write("="*40 + "\n")
                f.write(f"Generated at: {report.generated_at}\n\n")
                f.write(f"EXECUTIVE SUMMARY:\n{report.executive_summary}\n\n")
                f.write("VIDEO METADATA:\n")
                f.write(f"- Filename: {report.metadata.filename}\n")
                f.write(f"- Size: {report.metadata.file_size} bytes\n")
                f.write(f"- Resolution: {report.metadata.resolution}\n\n")
                f.write("TIMELINE EVENTS:\n")
                for event in report.timeline:
                    f.write(f"- [{event.timestamp}s] [{event.risk_level.value}] {event.description}\n")
            return pdf_path
            
        try:
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=letter,
                rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
            )
            
            styles = getSampleStyleSheet()
            
            # Custom styling for Palantir/Microsoft look (Deep Slate & Navy theme)
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=24,
                leading=28,
                textColor=colors.HexColor('#0F172A'), # Slate 900
                spaceAfter=15
            )
            
            subtitle_style = ParagraphStyle(
                'ReportSubtitle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#64748B'), # Slate 500
                spaceAfter=25
            )
            
            h1_style = ParagraphStyle(
                'ReportH1',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                leading=18,
                textColor=colors.HexColor('#1E3A8A'), # Navy 900
                spaceBefore=15,
                spaceAfter=8,
                keepWithNext=True
            )
            
            body_style = ParagraphStyle(
                'ReportBody',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#334155'), # Slate 700
                spaceAfter=10
            )
            
            timeline_style = ParagraphStyle(
                'TimelineText',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=12,
                textColor=colors.HexColor('#334155')
            )
            
            story = []
            
            # --- Header / Title ---
            story.append(Paragraph("FORENSIC EVIDENCE & INVESTIGATION REPORT", title_style))
            story.append(Paragraph(f"CONFIDENTIAL // FOR LAW ENFORCEMENT & SECURITY TEAMS ONLY<br/>"
                                   f"Case ID: {report.case_id} | Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", subtitle_style))
            
            # Draw line
            line_table = Table([[""]], colWidths=[500], rowHeights=[2])
            line_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(line_table)
            story.append(Spacer(1, 15))
            
            # --- Executive Summary ---
            story.append(Paragraph("Executive Summary", h1_style))
            story.append(Paragraph(report.executive_summary, body_style))
            story.append(Spacer(1, 10))
            
            # --- Video Metadata ---
            story.append(Paragraph("Evidence Video Metadata", h1_style))
            meta = report.metadata
            meta_data = [
                [Paragraph("<b>Property</b>", body_style), Paragraph("<b>Value</b>", body_style)],
                [Paragraph("Filename", body_style), Paragraph(meta.filename, body_style)],
                [Paragraph("File Size", body_style), Paragraph(f"{meta.file_size / (1024*1024):.2f} MB", body_style)],
                [Paragraph("Duration", body_style), Paragraph(f"{meta.duration_seconds:.2f} seconds", body_style)],
                [Paragraph("Resolution / FPS", body_style), Paragraph(f"{meta.resolution} @ {meta.fps} FPS", body_style)],
                [Paragraph("Encoding Format", body_style), Paragraph(meta.format, body_style)]
            ]
            t_meta = Table(meta_data, colWidths=[150, 350])
            t_meta.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#F1F5F9')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t_meta)
            story.append(Spacer(1, 15))
            
            # --- Risk Assessment ---
            story.append(Paragraph("AI Threat & Risk Assessment", h1_style))
            risk = report.risk_assessment
            risk_color = '#10B981' # Green
            if risk.risk_level == RiskLevel.MEDIUM:
                risk_color = '#F59E0B' # Orange
            elif risk.risk_level == RiskLevel.HIGH or risk.risk_level == RiskLevel.CRITICAL:
                risk_color = '#EF4444' # Red
                
            risk_data = [
                [Paragraph(f"<b>Risk Level:</b> <font color='{risk_color}'><b>{risk.risk_level.value.upper()}</b></font>", body_style), 
                 Paragraph(f"<b>Overall Score:</b> {risk.overall_score}/100", body_style)],
            ]
            t_risk = Table(risk_data, colWidths=[250, 250])
            t_risk.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('PADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(t_risk)
            story.append(Spacer(1, 10))
            
            # --- Timeline Events ---
            story.append(Paragraph("Synchronized Evidence Chronology", h1_style))
            timeline_headers = [
                Paragraph("<b>Time</b>", body_style),
                Paragraph("<b>Event Type</b>", body_style),
                Paragraph("<b>Description</b>", body_style),
                Paragraph("<b>Risk</b>", body_style)
            ]
            timeline_data = [timeline_headers]
            for event in report.timeline:
                risk_cell_color = '#10B981'
                if event.risk_level == RiskLevel.MEDIUM:
                    risk_cell_color = '#F59E0B'
                elif event.risk_level == RiskLevel.HIGH or event.risk_level == RiskLevel.CRITICAL:
                    risk_cell_color = '#EF4444'
                
                timeline_data.append([
                    Paragraph(f"{event.timestamp:.2f}s", timeline_style),
                    Paragraph(event.event_type, timeline_style),
                    Paragraph(event.description, timeline_style),
                    Paragraph(f"<font color='{risk_cell_color}'><b>{event.risk_level.value}</b></font>", timeline_style)
                ])
                
            t_timeline = Table(timeline_data, colWidths=[50, 100, 290, 60])
            t_timeline.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (3, 0), colors.HexColor('#F1F5F9')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t_timeline)
            story.append(Spacer(1, 15))
            
            # --- Recommendations ---
            story.append(Paragraph("Actionable Security Recommendations", h1_style))
            for rec in report.recommendations:
                story.append(Paragraph(f"• {rec}", body_style))
                
            # Build Document
            doc.build(story)
            logger.info("PDF forensic report generated successfully using ReportLab.")
            
        except Exception as e:
            logger.error(f"Error compiling ReportLab PDF layout: {e}. Reverting to text fallback.")
            with open(pdf_path, "w") as f:
                f.write(f"PDF compilation failed. Details: {e}\n\nCase ID: {report.case_id}")
                
        return pdf_path
