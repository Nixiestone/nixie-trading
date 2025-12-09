"""
PDF Generator for CSV Reports
Admin can download CSV files as formatted PDFs
"""

import csv
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFGenerator:
    """Generate PDF reports from CSV files"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a73e8'),
            spaceAfter=30,
            alignment=1  # Center
        )
    
    def generate_signals_pdf(self, csv_file: str, output_file: str) -> bool:
        """Generate PDF from signals CSV"""
        try:
            # Read CSV
            data = []
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                data = list(reader)
            
            if len(data) < 2:
                logger.warning("CSV file is empty or has no data")
                return False
            
            # Create PDF
            doc = SimpleDocTemplate(output_file, pagesize=A4)
            elements = []
            
            # Title
            title = Paragraph(f"<b>NIXIE'S TRADING BOT<br/>Signals Report</b>", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*inch))
            
            # Date
            date_text = Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", 
                self.styles['Normal']
            )
            elements.append(date_text)
            elements.append(Spacer(1, 0.3*inch))
            
            # Summary stats
            wins = sum(1 for row in data[1:] if row[21] == 'WIN')
            losses = sum(1 for row in data[1:] if row[21] == 'LOSS')
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            
            summary = Paragraph(
                f"<b>Summary:</b> Total Trades: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%",
                self.styles['Normal']
            )
            elements.append(summary)
            elements.append(Spacer(1, 0.3*inch))
            
            # Select key columns for PDF (too many columns for one page)
            key_columns = [0, 1, 2, 3, 4, 5, 8, 9, 10, 20, 21, 22]  # Signal ID, Time, Symbol, etc.
            table_data = []
            
            # Header
            header = [data[0][i] for i in key_columns]
            table_data.append(header)
            
            # Data rows (limit to last 50 for readability)
            for row in data[-50:]:
                if len(row) >= max(key_columns):
                    table_data.append([row[i] for i in key_columns])
            
            # Create table
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
            ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            logger.info(f"PDF generated successfully: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            return False
    
    def generate_closed_trades_pdf(self, csv_file: str, output_file: str) -> bool:
        """Generate PDF from closed trades CSV"""
        try:
            # Similar to above but for closed trades
            data = []
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                data = list(reader)
            
            if len(data) < 2:
                return False
            
            doc = SimpleDocTemplate(output_file, pagesize=A4)
            elements = []
            
            title = Paragraph(f"<b>NIXIE'S TRADING BOT<br/>Closed Trades Report</b>", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*inch))
            
            # Stats
            wins = sum(1 for row in data[1:] if row[7] == 'WIN')
            losses = sum(1 for row in data[1:] if row[7] == 'LOSS')
            total_pips = sum(float(row[8]) for row in data[1:] if row[8])
            
            summary = Paragraph(
                f"<b>Performance:</b> Wins: {wins} | Losses: {losses} | Total Pips: {total_pips:.1f}",
                self.styles['Normal']
            )
            elements.append(summary)
            elements.append(Spacer(1, 0.3*inch))
            
            # Table
            table = Table(data[:51], repeatRows=1)  # Header + 50 rows
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
            ]))
            
            elements.append(table)
            doc.build(elements)
            return True
            
        except Exception as e:
            logger.error(f"Error generating closed trades PDF: {e}")
            return False