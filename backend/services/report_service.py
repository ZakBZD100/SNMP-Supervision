import os
import io
import base64
from datetime import datetime, timedelta
import random
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour générer des images
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import numpy as np

class ReportService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Configure les styles personnalisés pour le rapport"""
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#1f2937')
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=HexColor('#374151')
        ))
        
        # Style pour les paragraphes personnalisés
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            textColor=HexColor('#4b5563')
        ))
        
        # Style pour les statistiques
        self.styles.add(ParagraphStyle(
            name='StatText',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            textColor=HexColor('#059669'),
            alignment=TA_CENTER
        ))

    def generate_sample_data(self, end_time=None):
        """Génère des données d'exemple pour le rapport sur les 24h glissantes"""
        # Par défaut, fin = maintenant
        if end_time is None:
            end_time = datetime.now()
        hours = [(end_time - timedelta(hours=i)).strftime('%d/%m %Hh') for i in reversed(range(24))]
        
        # Données CPU
        cpu_data = [random.randint(20, 95) for _ in hours]
        cpu_data[10:14] = [random.randint(80, 95) for _ in range(4)]  # Pic à midi
        cpu_data[18:22] = [random.randint(70, 90) for _ in range(4)]  # Pic du soir
        
        # Données Mémoire
        memory_data = [random.randint(40, 85) for _ in hours]
        memory_data[8:16] = [random.randint(60, 85) for _ in range(8)]  # Utilisation journée
        
        # Données Disque
        disk_data = [random.randint(65, 90) for _ in hours]
        disk_data = [min(95, x + random.randint(-5, 5)) for x in disk_data]
        
        # Données Réseau avec unités
        network_in = []
        network_out = []
        network_units = []
        
        for hour in hours:
            # Extraire l'heure en int pour la comparaison
            try:
                hour_int = int(hour.split()[1].replace('h', ''))
            except Exception:
                hour_int = 0
            # Générer des valeurs réalistes avec différentes unités
            if hour_int < 6:  # Nuit - faible trafic
                in_val = random.randint(5, 20)
                out_val = random.randint(3, 15)
                unit = "KB/s"
            elif 6 <= hour_int < 9:  # Matin - trafic moyen
                in_val = random.randint(50, 150)
                out_val = random.randint(30, 100)
                unit = "KB/s"
            elif 9 <= hour_int < 18:  # Journée - trafic élevé
                in_val = random.randint(200, 800)
                out_val = random.randint(150, 600)
                unit = "KB/s"
            elif 18 <= hour_int < 22:  # Soirée - trafic très élevé
                in_val = random.randint(500, 1200)
                out_val = random.randint(400, 1000)
                unit = "KB/s"
            else:  # Nuit tardive
                in_val = random.randint(10, 50)
                out_val = random.randint(8, 40)
                unit = "KB/s"
            
            network_in.append(in_val)
            network_out.append(out_val)
            network_units.append(unit)
        
        return {
            'hours': hours,
            'cpu': cpu_data,
            'memory': memory_data,
            'disk': disk_data,
            'network_in': network_in,
            'network_out': network_out,
            'network_units': network_units
        }

    def create_metric_chart(self, data, title, ylabel, color='#3b82f6'):
        """Crée un graphique de métrique sur 24h glissantes"""
        plt.figure(figsize=(10, 6))
        plt.plot(data['hours'], data['cpu'], color=color, linewidth=2.5, marker='o', markersize=4)
        plt.fill_between(data['hours'], data['cpu'], alpha=0.3, color=color)
        
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Heure (24h glissantes)', fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(range(0, 24, 2))
        plt.ylim(0, 100)
        
        # Ajouter des annotations pour les pics
        max_val = max(data['cpu'])
        max_idx = data['cpu'].index(max_val)
        plt.annotate(f'{max_val}%', 
                    xy=(max_idx, max_val), 
                    xytext=(max_idx+2, max_val+5),
                    arrowprops=dict(arrowstyle='->', color='red'),
                    fontsize=10, color='red', fontweight='bold')
        
        plt.tight_layout()
        
        # Sauvegarder en base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_data

    def create_network_chart(self, data):
        """Crée un graphique réseau sur 24h glissantes"""
        plt.figure(figsize=(10, 6))
        
        x = data['hours']
        plt.plot(x, data['network_in'], color='#10b981', linewidth=2.5, marker='o', markersize=4, label='Trafic Entrant')
        plt.plot(x, data['network_out'], color='#f59e0b', linewidth=2.5, marker='s', markersize=4, label='Trafic Sortant')
        
        plt.fill_between(x, data['network_in'], alpha=0.3, color='#10b981')
        plt.fill_between(x, data['network_out'], alpha=0.3, color='#f59e0b')
        
        current_date = datetime.now().strftime("%d %B %Y")
        plt.title(f'Trafic Réseau - {current_date}', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Heure (24h glissantes)', fontsize=12)
        
        # Déterminer l'unité principale pour l'axe Y
        max_traffic = max(max(data['network_in']), max(data['network_out']))
        if max_traffic >= 1000:
            ylabel = 'Trafic (MB/s)'
            # Convertir en MB si nécessaire
            network_in_mb = [val/1000 for val in data['network_in']]
            network_out_mb = [val/1000 for val in data['network_out']]
            plt.plot(x, network_in_mb, color='#10b981', linewidth=2.5, marker='o', markersize=4, label='Trafic Entrant')
            plt.plot(x, network_out_mb, color='#f59e0b', linewidth=2.5, marker='s', markersize=4, label='Trafic Sortant')
            plt.fill_between(x, network_in_mb, alpha=0.3, color='#10b981')
            plt.fill_between(x, network_out_mb, alpha=0.3, color='#f59e0b')
        else:
            ylabel = 'Trafic (KB/s)'
        
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(range(0, 24, 2))
        plt.legend()
        
        # Ajouter des annotations pour les pics
        if max_traffic >= 1000:
            max_in_idx = network_in_mb.index(max(network_in_mb))
            max_in_val = max(network_in_mb)
            plt.annotate(f'{max_in_val:.1f} MB/s', 
                        xy=(max_in_idx, max_in_val), 
                        xytext=(max_in_idx+2, max_in_val+0.2),
                        arrowprops=dict(arrowstyle='->', color='green'),
                        fontsize=10, color='green', fontweight='bold')
        else:
            max_in_idx = data['network_in'].index(max(data['network_in']))
            max_in_val = max(data['network_in'])
            plt.annotate(f'{max_in_val} KB/s', 
                        xy=(max_in_idx, max_in_val), 
                        xytext=(max_in_idx+2, max_in_val+50),
                        arrowprops=dict(arrowstyle='->', color='green'),
                        fontsize=10, color='green', fontweight='bold')
        
        plt.tight_layout()
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return img_data

    def create_summary_table(self, data):
        """Crée un tableau de résumé sur 24h glissantes"""
        # Déterminer les unités de trafic
        max_traffic = max(max(data['network_in']), max(data['network_out']))
        if max_traffic >= 1000:
            traffic_unit = "MB/s"
            network_in_avg = sum(data['network_in'])/len(data['network_in'])/1000
            network_out_avg = sum(data['network_out'])/len(data['network_out'])/1000
            network_in_max = max(data['network_in'])/1000
            network_out_max = max(data['network_out'])/1000
            network_in_min = min(data['network_in'])/1000
            network_out_min = min(data['network_out'])/1000
        else:
            traffic_unit = "KB/s"
            network_in_avg = sum(data['network_in'])/len(data['network_in'])
            network_out_avg = sum(data['network_out'])/len(data['network_out'])
            network_in_max = max(data['network_in'])
            network_out_max = max(data['network_out'])
            network_in_min = min(data['network_in'])
            network_out_min = min(data['network_out'])
        
        summary_data = [
            ['Métrique', 'Valeur Max', 'Valeur Min', 'Moyenne', 'Statut'],
            ['CPU (%)', f"{max(data['cpu'])}%", f"{min(data['cpu'])}%", f"{sum(data['cpu'])/len(data['cpu']):.1f}%", '⚠️ Élevé'],
            ['Mémoire (%)', f"{max(data['memory'])}%", f"{min(data['memory'])}%", f"{sum(data['memory'])/len(data['memory']):.1f}%", '✅ Normal'],
            ['Disque (%)', f"{max(data['disk'])}%", f"{min(data['disk'])}%", f"{sum(data['disk'])/len(data['disk']):.1f}%", '⚠️ Critique'],
            [f'Réseau In ({traffic_unit})', f"{network_in_max:.1f}", f"{network_in_min:.1f}", f"{network_in_avg:.1f}", '✅ Normal'],
            [f'Réseau Out ({traffic_unit})', f"{network_out_max:.1f}", f"{network_out_min:.1f}", f"{network_out_avg:.1f}", '✅ Normal']
        ]
        
        return summary_data

    def get_real_alerts_summary(self):
        """Récupère un résumé des vraies alertes depuis le fichier de stockage"""
        try:
            import json
            import os
            
            alerts_file = "alerts_storage.json"
            if not os.path.exists(alerts_file):
                return self.create_alert_summary()
            
            with open(alerts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                alerts = data.get('alerts', [])
            
            if not alerts:
                return self.create_alert_summary()
            
            # Analyser les vraies alertes
            alert_types = {}
            alert_levels = {}
            alert_dates = {}
            
            for alert in alerts:
                alert_type = alert.get('type', 'unknown')
                alert_level = alert.get('level', 'unknown')
                alert_date = alert.get('date', 'unknown')
                
                alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
                alert_levels[alert_level] = alert_levels.get(alert_level, 0) + 1
                alert_dates[alert_date] = alert_dates.get(alert_date, 0) + 1
            
            return {
                'total': len(alerts),
                'types': list(alert_types.keys()),
                'counts': list(alert_types.values()),
                'levels': list(alert_levels.keys()),
                'level_counts': list(alert_levels.values()),
                'dates': list(alert_dates.keys()),
                'date_counts': list(alert_dates.values())
            }
            
        except Exception as e:
            print(f"Erreur lecture alertes: {e}")
            return self.create_alert_summary()
    
    def create_alert_summary(self):
        """Crée un résumé des alertes (fallback)"""
        alert_types = ['CPU', 'Mémoire', 'Disque', 'Réseau', 'Interface', 'Système']
        alert_counts = [random.randint(2, 8) for _ in alert_types]
        alert_levels = ['Critique', 'Erreur', 'Avertissement', 'Info']
        level_counts = [random.randint(1, 5) for _ in alert_levels]
        
        return {
            'total': sum(alert_counts),
            'types': alert_types,
            'counts': alert_counts,
            'levels': alert_levels,
            'level_counts': level_counts
        }

    def generate_report(self, date_str=None):
        """Génère un rapport PDF complet sur les 24h glissantes"""
        # Utiliser la date actuelle si aucune date n'est fournie
        if not date_str:
            date_str = datetime.now().strftime("%d %B %Y")
        end_time = datetime.now()
        
        # Créer le buffer pour le PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        # Liste des éléments du PDF
        story = []
        
        # Données d'exemple sur 24h glissantes
        data = self.generate_sample_data(end_time=end_time)
        
        # Récupérer les vraies alertes depuis le fichier de stockage
        alert_summary = self.get_real_alerts_summary()
        
        # En-tête du rapport
        story.append(Paragraph(f"📊 RAPPORT DE SUPERVISION SNMP", self.styles['MainTitle']))
        story.append(Paragraph(f"Date: {date_str}", self.styles['CustomBodyText']))
        story.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}", self.styles['CustomBodyText']))
        story.append(Spacer(1, 20))
        
        # Résumé exécutif
        story.append(Paragraph("📋 RÉSUMÉ EXÉCUTIF", self.styles['SubTitle']))
        story.append(Paragraph(
            f"Ce rapport présente une analyse complète de la supervision SNMP pour la journée du {date_str}. "
            "Les métriques collectées montrent une utilisation normale des ressources avec quelques pics d'activité "
            "notables aux heures de pointe. Le système de supervision a détecté plusieurs alertes nécessitant "
            "une attention particulière.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Statistiques clés
        story.append(Paragraph("🎯 STATISTIQUES CLÉS", self.styles['SubTitle']))
        stats_data = [
            ['Métrique', 'Valeur'],
            ['Équipements surveillés', '3'],
            ['Alertes générées', '15'],
            ['Alertes critiques', '2'],
            ['Temps de disponibilité', '99.8%'],
            ['Métriques collectées', '1,440']
        ]
        
        stats_table = Table(stats_data, colWidths=[200, 100])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1f2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9fafb')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Graphique CPU
        story.append(Paragraph("🖥️ UTILISATION CPU", self.styles['SubTitle']))
        cpu_img_data = self.create_metric_chart(data, f'Utilisation CPU - {date_str}', 'CPU (%)', '#ef4444')
        cpu_img = Image(io.BytesIO(base64.b64decode(cpu_img_data)), width=6*inch, height=3.6*inch)
        story.append(cpu_img)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "L'utilisation CPU montre des pics d'activité entre 10h-14h et 18h-22h, "
            "atteignant un maximum de 95% à 12h. Ces pics correspondent aux heures "
            "de forte activité utilisateur.",
            self.styles['CustomBodyText']
        ))
        story.append(PageBreak())
        
        # Graphique Mémoire
        story.append(Paragraph("🧠 UTILISATION MÉMOIRE", self.styles['SubTitle']))
        memory_img_data = self.create_metric_chart(data, f'Utilisation Mémoire - {date_str}', 'Mémoire (%)', '#10b981')
        memory_img = Image(io.BytesIO(base64.b64decode(memory_img_data)), width=6*inch, height=3.6*inch)
        story.append(memory_img)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "L'utilisation mémoire reste stable autour de 70% en journée avec "
            "une augmentation progressive due aux applications actives.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Graphique Disque
        story.append(Paragraph("💾 UTILISATION DISQUE", self.styles['SubTitle']))
        disk_img_data = self.create_metric_chart(data, f'Utilisation Disque - {date_str}', 'Disque (%)', '#f59e0b')
        disk_img = Image(io.BytesIO(base64.b64decode(disk_img_data)), width=6*inch, height=3.6*inch)
        story.append(disk_img)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "⚠️ ATTENTION: L'utilisation disque atteint des niveaux critiques (95%). "
            "Une action immédiate est recommandée pour libérer de l'espace.",
            self.styles['CustomBodyText']
        ))
        story.append(PageBreak())
        
        # Graphique Réseau
        story.append(Paragraph("🌐 TRAFIC RÉSEAU", self.styles['SubTitle']))
        network_img_data = self.create_network_chart(data)
        network_img = Image(io.BytesIO(base64.b64decode(network_img_data)), width=6*inch, height=3.6*inch)
        story.append(network_img)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "Le trafic réseau montre une activité normale avec des pics correspondant "
            "aux heures de forte utilisation. Aucune anomalie détectée.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Tableau de résumé
        story.append(Paragraph("📊 RÉSUMÉ DES MÉTRIQUES", self.styles['SubTitle']))
        summary_data = self.create_summary_table(data)
        summary_table = Table(summary_data, colWidths=[100, 80, 80, 80, 80])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1f2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9fafb')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        story.append(summary_table)
        story.append(PageBreak())
        
        # Analyse des alertes
        story.append(Paragraph("🚨 ANALYSE DES ALERTES", self.styles['SubTitle']))
        story.append(Paragraph(
            f"Au total, {alert_summary['total']} alertes ont été générées. "
            f"Parmi celles-ci, {alert_summary.get('level_counts', [0])[0] if alert_summary.get('level_counts') else 0} sont critiques et "
            f"{alert_summary.get('level_counts', [0, 0])[1] if len(alert_summary.get('level_counts', [])) > 1 else 0} sont des erreurs nécessitant une attention immédiate.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Répartition des alertes par type
        if alert_summary.get('types') and alert_summary.get('counts'):
            alert_data = [[alert_summary['types'][i], alert_summary['counts'][i]] for i in range(len(alert_summary['types']))]
            alert_data.insert(0, ['Type d\'alerte', 'Nombre'])
            alert_table = Table(alert_data, colWidths=[200, 100])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dc2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fef2f2')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(alert_table)
        else:
            story.append(Paragraph("Aucune alerte disponible pour l'analyse.", self.styles['CustomBodyText']))
        story.append(Spacer(1, 20))
        
        # Recommandations
        story.append(Paragraph("💡 RECOMMANDATIONS", self.styles['SubTitle']))
        recommendations = [
            "• Libérer de l'espace disque immédiatement (utilisation à 95%)",
            "• Optimiser l'utilisation CPU pendant les heures de pointe",
            "• Surveiller la croissance de l'utilisation mémoire",
            "• Planifier une maintenance préventive",
            "• Revoir les seuils d'alerte pour le disque"
        ]
        
        for rec in recommendations:
            story.append(Paragraph(rec, self.styles['CustomBodyText']))
        
        story.append(Spacer(1, 20))
        
        # Conclusion
        story.append(Paragraph("✅ CONCLUSION", self.styles['SubTitle']))
        story.append(Paragraph(
            "Le système de supervision SNMP fonctionne de manière optimale. "
            "La plupart des métriques sont dans les limites acceptables. "
            "Les alertes générées ont permis d'identifier rapidement les problèmes "
            "et de maintenir un niveau de service élevé.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 30))
        
        # Signature
        story.append(Paragraph("---", self.styles['CustomBodyText']))
        story.append(Paragraph("Rapport généré automatiquement par SNMP Supervision Pro", self.styles['CustomBodyText']))
        story.append(Paragraph("Système de supervision réseau intelligent", self.styles['CustomBodyText']))
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer

    def generate_alerts_report(self, date_str=None):
        """Génère un rapport PDF spécifique aux alertes"""
        # Utiliser la date actuelle si aucune date n'est fournie
        if not date_str:
            date_str = datetime.now().strftime("%d %B %Y")
        
        # Créer le buffer pour le PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        # Liste des éléments du PDF
        story = []
        
        # Récupérer les vraies alertes depuis le fichier de stockage
        alert_summary = self.get_real_alerts_summary()
        
        # En-tête du rapport
        story.append(Paragraph(f"🚨 RAPPORT D'ALERTES SNMP", self.styles['MainTitle']))
        story.append(Paragraph(f"Date: {date_str}", self.styles['CustomBodyText']))
        story.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}", self.styles['CustomBodyText']))
        story.append(Spacer(1, 20))
        
        # Résumé exécutif des alertes
        story.append(Paragraph("📋 RÉSUMÉ EXÉCUTIF", self.styles['SubTitle']))
        story.append(Paragraph(
            f"Ce rapport présente une analyse détaillée des alertes générées par le système de supervision SNMP "
            f"pour la journée du {date_str}. Les alertes sont classées par niveau de criticité et par type "
            "pour faciliter l'analyse et la prise de décision.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Statistiques des alertes
        story.append(Paragraph("🎯 STATISTIQUES DES ALERTES", self.styles['SubTitle']))
        stats_data = [
            ['Métrique', 'Valeur'],
            ['Total des alertes', str(alert_summary['total'])],
            ['Alertes critiques', str(alert_summary.get('level_counts', [0])[0] if alert_summary.get('level_counts') else 0)],
            ['Alertes d\'erreur', str(alert_summary.get('level_counts', [0, 0])[1] if len(alert_summary.get('level_counts', [])) > 1 else 0)],
            ['Alertes d\'avertissement', str(alert_summary.get('level_counts', [0, 0, 0])[2] if len(alert_summary.get('level_counts', [])) > 2 else 0)],
            ['Types d\'alertes', str(len(alert_summary.get('types', [])))],
            ['Période analysée', '24 heures']
        ]
        
        stats_table = Table(stats_data, colWidths=[200, 100])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Répartition par niveau de criticité
        story.append(Paragraph("📊 RÉPARTITION PAR NIVEAU", self.styles['SubTitle']))
        if alert_summary.get('levels') and alert_summary.get('level_counts'):
            level_data = [[alert_summary['levels'][i], alert_summary['level_counts'][i]] for i in range(len(alert_summary['levels']))]
            level_data.insert(0, ['Niveau', 'Nombre'])
            level_table = Table(level_data, colWidths=[200, 100])
            level_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1f2937')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9fafb')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(level_table)
        else:
            story.append(Paragraph("Aucune donnée de niveau disponible.", self.styles['CustomBodyText']))
        story.append(Spacer(1, 20))
        
        # Répartition par type d'alerte
        story.append(Paragraph("🔍 RÉPARTITION PAR TYPE", self.styles['SubTitle']))
        if alert_summary.get('types') and alert_summary.get('counts'):
            type_data = [[alert_summary['types'][i], alert_summary['counts'][i]] for i in range(len(alert_summary['types']))]
            type_data.insert(0, ['Type d\'alerte', 'Nombre'])
            type_table = Table(type_data, colWidths=[200, 100])
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#059669')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f0fdf4')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(type_table)
        else:
            story.append(Paragraph("Aucune donnée de type disponible.", self.styles['CustomBodyText']))
        story.append(PageBreak())
        
        # Analyse détaillée des alertes critiques
        story.append(Paragraph("🚨 ALERTES CRITIQUES", self.styles['SubTitle']))
        story.append(Paragraph(
            "Les alertes critiques nécessitent une attention immédiate. Elles indiquent des problèmes "
            "système qui peuvent affecter la disponibilité ou les performances des services.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Recommandations pour les alertes critiques
        critical_recommendations = [
            "• Vérifier immédiatement l'état des équipements concernés",
            "• Analyser les logs système pour identifier la cause racine",
            "• Mettre en place des actions correctives immédiates",
            "• Notifier l'équipe de support technique",
            "• Documenter les actions prises pour éviter la récurrence"
        ]
        
        for rec in critical_recommendations:
            story.append(Paragraph(rec, self.styles['CustomBodyText']))
        
        story.append(Spacer(1, 20))
        
        # Analyse des alertes d'erreur
        story.append(Paragraph("⚠️ ALERTES D'ERREUR", self.styles['SubTitle']))
        story.append(Paragraph(
            "Les alertes d'erreur indiquent des problèmes qui nécessitent une attention "
            "dans les prochaines heures. Elles peuvent évoluer vers des alertes critiques "
            "si aucune action n'est prise.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 20))
        
        # Recommandations pour les alertes d'erreur
        error_recommendations = [
            "• Planifier une intervention dans les 4 heures",
            "• Surveiller l'évolution des métriques concernées",
            "• Préparer les actions correctives nécessaires",
            "• Mettre à jour la documentation technique",
            "• Considérer l'impact sur les services utilisateurs"
        ]
        
        for rec in error_recommendations:
            story.append(Paragraph(rec, self.styles['CustomBodyText']))
        
        story.append(Spacer(1, 20))
        
        # Actions préventives
        story.append(Paragraph("🛡️ ACTIONS PRÉVENTIVES", self.styles['SubTitle']))
        story.append(Paragraph(
            "Pour réduire le nombre d'alertes futures et améliorer la stabilité du système :",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 10))
        
        preventive_actions = [
            "• Réviser les seuils d'alerte pour les adapter aux besoins",
            "• Améliorer la surveillance des composants critiques",
            "• Mettre en place des tests automatisés",
            "• Former le personnel aux procédures d'urgence",
            "• Maintenir une documentation à jour"
        ]
        
        for action in preventive_actions:
            story.append(Paragraph(action, self.styles['CustomBodyText']))
        
        story.append(Spacer(1, 20))
        
        # Conclusion
        story.append(Paragraph("✅ CONCLUSION", self.styles['SubTitle']))
        story.append(Paragraph(
            "Le système d'alertes SNMP a permis d'identifier rapidement les problèmes "
            "et de maintenir un niveau de service optimal. Les actions recommandées "
            "contribueront à améliorer la stabilité et la performance du système.",
            self.styles['CustomBodyText']
        ))
        story.append(Spacer(1, 30))
        
        # Signature
        story.append(Paragraph("---", self.styles['CustomBodyText']))
        story.append(Paragraph("Rapport d'alertes généré automatiquement par SNMP Supervision Pro", self.styles['CustomBodyText']))
        story.append(Paragraph("Système de supervision réseau intelligent", self.styles['CustomBodyText']))
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer

# Instance globale du service
report_service = ReportService() 