from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

class ReportService:
    @staticmethod
    def generate_fleet_report(summary: Dict[str, Any], vehicles: List[Dict[str, Any]]) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#6366f1'),
            spaceAfter=20
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.grey,
            spaceAfter=30
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("FleetAI Intelligence Report", title_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
        elements.append(Spacer(1, 12))

        # 2. Executive Summary Block
        k = summary.get('kpis', {})
        summary_data = [
            ["Metric", "Value", "Status"],
            ["Total Fleet size", str(k['total']), "Nominal"],
            ["Active Vehicles", str(k['active']), "Live"],
            ["IDLE Units", str(k['idle']), "Monitoring"],
            ["Stale (>24h)", str(k['stale']), "Action Required" if k['stale'] > 0 else "Clear"],
            ["Overspeed Alerts", str(k['overspeed']), "Warning" if k['overspeed'] > 0 else "Safe"]
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 100, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(Paragraph("Executive Fleet Summary", styles['Heading2']))
        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        # 3. Detailed Vehicle Matrix
        elements.append(Paragraph("Live Telemetry Matrix", styles['Heading2']))
        
        vehicle_data = [["Vehicle Name", "UniqueID", "Speed", "Status", "Fuel %"]]
        for v in vehicles[:20]: # Limit to top 20 for PDF space
            vehicle_data.append([
                v['name'],
                v['uniqueId'],
                f"{v.get('speed', 0):.1f} km/h",
                v['status'].upper(),
                f"{v.get('attributes', {}).get('fuelLevel', 75)}%"
            ])
            
        v_table = Table(vehicle_data, colWidths=[150, 120, 80, 80, 80])
        v_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, -1), 9)
        ]))
        
        elements.append(v_table)
        
        # Footer
        elements.append(Spacer(1, 50))
        elements.append(Paragraph("End of Automated AI Intelligence Report", styles['Italic']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_fleet_report_file(summary: Dict[str, Any], vehicles: List[Dict[str, Any]], filename: str) -> str:
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom Styles (Simplified for background use)
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#6366f1'),
            spaceAfter=20
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.grey,
            spaceAfter=30
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("FleetAI Intelligence Report (Background)", title_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
        elements.append(Spacer(1, 12))

        # 2. Executive Summary Block
        k = summary.get('kpis', {})
        summary_data = [
            ["Metric", "Value", "Status"],
            ["Total Fleet size", str(k.get('total', 0)), "Nominal"],
            ["Active Vehicles", str(k.get('active', 0)), "Live"],
            ["IDLE Units", str(k.get('idle', 0)), "Monitoring"],
            ["Stale (>24h)", str(k.get('stale', 0)), "Detailed"],
            ["Overspeed Alerts", str(k.get('overspeed', 0)), "Warning"]
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 100, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(Paragraph("Executive Fleet Summary", styles['Heading2']))
        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        # 3. Detailed Vehicle Matrix
        elements.append(Paragraph("Live Telemetry Matrix", styles['Heading2']))
        
        vehicle_data = [["Vehicle Name", "UniqueID", "Speed", "Status"]]
        for v in vehicles[:50]: # Background can handle more
            vehicle_data.append([
                v.get('name', 'N/A'),
                v.get('uniqueId', 'N/A'),
                f"{v.get('speed', 0):.1f} km/h",
                v.get('status', 'offline').upper()
            ])
            
        v_table = Table(vehicle_data, colWidths=[150, 120, 100, 100])
        v_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey)
        ]))
        
        elements.append(v_table)
        doc.build(elements)
        return filename
