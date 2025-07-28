import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging
from .email_service import EmailService

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.email_service = EmailService()
        self.alerts_file = "alerts_storage.json"
        self.notification_config_file = "notification_config.json"
        self.last_notification_time = None
        self.notification_interval = 300  # 5 minutes par défaut
        
        # Charger la configuration des notifications
        self.load_notification_config()
        
    def load_notification_config(self):
        """Charge la configuration des notifications"""
        try:
            if os.path.exists(self.notification_config_file):
                with open(self.notification_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.notification_email = config.get('notification_email', 'admin@snmp-supervision.com')
                    self.notification_interval = config.get('notification_interval', 300)
                    self.notifications_enabled = config.get('notifications_enabled', True)
            else:
                # Configuration par défaut
                self.notification_email = 'admin@snmp-supervision.com'
                self.notification_interval = 300
                self.notifications_enabled = True
                self.save_notification_config()
        except Exception as e:
            logger.error(f"Erreur chargement config notifications: {e}")
            self.notification_email = 'admin@snmp-supervision.com'
            self.notification_interval = 300
            self.notifications_enabled = True
    
    def save_notification_config(self):
        """Sauvegarde la configuration des notifications"""
        try:
            config = {
                'notification_email': self.notification_email,
                'notification_interval': self.notification_interval,
                'notifications_enabled': self.notifications_enabled,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.notification_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config notifications: {e}")
    
    def update_notification_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour la configuration des notifications (admin seulement)"""
        try:
            if 'notification_email' in new_config:
                self.notification_email = new_config['notification_email']
            if 'notification_interval' in new_config:
                self.notification_interval = new_config['notification_interval']
            if 'notifications_enabled' in new_config:
                self.notifications_enabled = new_config['notifications_enabled']
            
            self.save_notification_config()
            
            return {
                "success": True,
                "message": "Configuration des notifications mise à jour",
                "config": {
                    "notification_email": self.notification_email,
                    "notification_interval": self.notification_interval,
                    "notifications_enabled": self.notifications_enabled
                }
            }
        except Exception as e:
            logger.error(f"Erreur mise à jour config notifications: {e}")
            return {
                "success": False,
                "message": f"Erreur mise à jour: {str(e)}"
            }
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Récupère la configuration des notifications (lecture seule pour utilisateurs)"""
        return {
            "notification_email": self.notification_email,
            "notification_interval": self.notification_interval,
            "notifications_enabled": self.notifications_enabled,
            "last_updated": datetime.now().isoformat()
        }
    
    def group_alerts_by_timestamp(self, alerts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Groupe les alertes par timestamp (dans un intervalle de 5 minutes)"""
        grouped_alerts = defaultdict(list)
        
        for alert in alerts:
            try:
                # Parser le timestamp
                timestamp_str = alert.get('timestamp', '')
                if timestamp_str:
                    # Enlever le 'Z' à la fin si présent
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1]
                    
                    alert_time = datetime.fromisoformat(timestamp_str)
                    
                    # Créer une clé de groupe basée sur l'heure (arrondie à 5 minutes)
                    minutes = alert_time.minute - (alert_time.minute % 5)
                    group_time = alert_time.replace(minute=minutes, second=0, microsecond=0)
                    group_key = group_time.isoformat()
                    
                    grouped_alerts[group_key].append(alert)
            except Exception as e:
                logger.error(f"Erreur parsing timestamp alert: {e}")
                # Grouper par date si erreur de parsing
                date_key = alert.get('date', 'unknown')
                grouped_alerts[date_key].append(alert)
        
        return dict(grouped_alerts)
    
    def create_grouped_notification_email(self, grouped_alerts: Dict[str, List[Dict[str, Any]]]) -> str:
        """Crée le contenu HTML de l'email groupé"""
        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { background-color: #dc2626; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .group { margin-bottom: 25px; border: 1px solid #e5e5e5; border-radius: 5px; }
                .group-header { background-color: #f8f9fa; padding: 10px; border-bottom: 1px solid #e5e5e5; font-weight: bold; }
                .alert { padding: 10px; margin: 5px; border-left: 4px solid #ccc; background-color: #f9f9f9; }
                .alert.critical { border-left-color: #dc2626; background-color: #fef2f2; }
                .alert.error { border-left-color: #f59e0b; background-color: #fffbeb; }
                .alert.warning { border-left-color: #10b981; background-color: #f0fdf4; }
                .alert.info { border-left-color: #3b82f6; background-color: #eff6ff; }
                .severity { font-weight: bold; }
                .equipment { color: #374151; }
                .message { margin-top: 5px; }
                .timestamp { color: #6b7280; font-size: 12px; }
                .summary { background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Notifications SNMP Supervision</h1>
                    <p>Résumé des alertes groupées par période</p>
                </div>
        """
        
        # Statistiques globales
        total_alerts = sum(len(alerts) for alerts in grouped_alerts.values())
        critical_count = 0
        error_count = 0
        warning_count = 0
        info_count = 0
        
        for alerts in grouped_alerts.values():
            for alert in alerts:
                level = alert.get('level', 'info')
                if level == 'critical':
                    critical_count += 1
                elif level == 'error':
                    error_count += 1
                elif level == 'warning':
                    warning_count += 1
                else:
                    info_count += 1
        
        html_content += f"""
                <div class="summary">
                    <h3>📊 Résumé Global</h3>
                    <p><strong>Total des alertes:</strong> {total_alerts}</p>
                    <p><strong>Critiques:</strong> {critical_count} | <strong>Erreurs:</strong> {error_count} | <strong>Avertissements:</strong> {warning_count} | <strong>Infos:</strong> {info_count}</p>
                </div>
        """
        
        # Grouper par période
        for group_time, alerts in grouped_alerts.items():
            try:
                # Formater l'heure du groupe
                if 'T' in group_time:
                    group_datetime = datetime.fromisoformat(group_time)
                    group_display = group_datetime.strftime("%d/%m/%Y à %H:%M")
                else:
                    group_display = group_time
                
                html_content += f"""
                <div class="group">
                    <div class="group-header">
                        📅 Période: {group_display} ({len(alerts)} alertes)
                    </div>
                """
                
                for alert in alerts:
                    level = alert.get('level', 'info')
                    equipment = alert.get('equipment', 'Équipement inconnu')
                    message = alert.get('message', 'Aucun message')
                    time = alert.get('time', '')
                    date = alert.get('date', '')
                    
                    html_content += f"""
                    <div class="alert {level}">
                        <div class="severity">{level.upper()}</div>
                        <div class="equipment">🖥️ {equipment}</div>
                        <div class="message">{message}</div>
                        <div class="timestamp">⏰ {date} {time}</div>
                    </div>
                    """
                
                html_content += "</div>"
                
            except Exception as e:
                logger.error(f"Erreur formatage groupe alertes: {e}")
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_grouped_notifications(self) -> Dict[str, Any]:
        """Envoie les notifications groupées par email"""
        try:
            if not self.notifications_enabled:
                return {
                    "success": False,
                    "message": "Notifications désactivées"
                }
            
            # Charger les alertes
            if not os.path.exists(self.alerts_file):
                return {
                    "success": False,
                    "message": "Aucune alerte disponible"
                }
            
            with open(self.alerts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                alerts = data.get('alerts', [])
            
            if not alerts:
                return {
                    "success": False,
                    "message": "Aucune alerte à notifier"
                }
            
            # Filtrer seulement les alertes critiques et erreurs non envoyées
            critical_alerts = [
                alert for alert in alerts 
                if alert.get('level') in ['critical', 'error'] and not alert.get('email_sent', False)
            ]
            
            if not critical_alerts:
                return {
                    "success": False,
                    "message": "Aucune alerte critique/erreur en attente d'envoi"
                }
            
            # Vérifier si on doit envoyer (basé sur l'intervalle)
            current_time = datetime.now()
            if self.last_notification_time:
                time_diff = (current_time - self.last_notification_time).total_seconds()
                if time_diff < self.notification_interval:
                    return {
                        "success": False,
                        "message": f"Trop tôt pour envoyer (attendre {self.notification_interval - time_diff:.0f}s)"
                    }
            
            # Grouper les alertes critiques
            grouped_alerts = self.group_alerts_by_timestamp(critical_alerts)
            
            if not grouped_alerts:
                return {
                    "success": False,
                    "message": "Aucune alerte critique à grouper"
                }
            
            # Créer l'email groupé
            html_content = self.create_grouped_notification_email(grouped_alerts)
            
            # Envoyer l'email
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            message = MIMEMultipart()
            message["From"] = self.email_service.from_email
            message["To"] = self.notification_email
            message["Subject"] = f"🚨 Alertes Critiques SNMP - {current_time.strftime('%d/%m/%Y %H:%M')}"
            
            message.attach(MIMEText(html_content, "html"))
            
            # Envoyer via le service email
            success = self.email_service._send_email(message)
            
            if success:
                self.last_notification_time = current_time
                return {
                    "success": True,
                    "message": f"Alertes critiques envoyées à {self.notification_email}",
                    "details": {
                        "groups_sent": len(grouped_alerts),
                        "total_alerts": sum(len(alerts) for alerts in grouped_alerts.values()),
                        "recipient": self.notification_email,
                        "critical_count": len(critical_alerts)
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Erreur lors de l'envoi de l'email"
                }
                
        except Exception as e:
            logger.error(f"Erreur envoi notifications groupées: {e}")
            return {
                "success": False,
                "message": f"Erreur: {str(e)}"
            }
    
    def test_notification(self) -> Dict[str, Any]:
        """Teste l'envoi d'une notification"""
        try:
            # Créer une alerte de test
            test_alert = {
                "id": "test",
                "type": "test",
                "level": "info",
                "message": "Ceci est un test de notification",
                "timestamp": datetime.now().isoformat() + "Z",
                "equipment": "Système de test",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "time": datetime.now().strftime("%H:%M:%S")
            }
            
            grouped_alerts = {"test": [test_alert]}
            html_content = self.create_grouped_notification_email(grouped_alerts)
            
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            message = MIMEMultipart()
            message["From"] = self.email_service.from_email
            message["To"] = self.notification_email
            message["Subject"] = "🧪 Test Notification SNMP"
            
            message.attach(MIMEText(html_content, "html"))
            
            success = self.email_service._send_email(message)
            
            return {
                "success": success,
                "message": "Test de notification envoyé" if success else "Erreur lors du test",
                "recipient": self.notification_email
            }
            
        except Exception as e:
            logger.error(f"Erreur test notification: {e}")
            return {
                "success": False,
                "message": f"Erreur test: {str(e)}"
            } 

    def send_alert(self, alert):
        # Recharger la config SMTP à chaque envoi
        self.email_service.reload_config()
        if self.email_service.email_alerts_enabled:
            if alert.get('level') == 'critical' and self.email_service.critical_alerts_only:
                self.email_service.send_alert_notification_to_user(self.notification_email, alert)
            elif not self.email_service.critical_alerts_only:
                self.email_service.send_alert_notification_to_user(self.notification_email, alert)
