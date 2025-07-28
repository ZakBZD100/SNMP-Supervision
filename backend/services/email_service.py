import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

#load environment variables
if os.path.exists("config.env"):
    load_dotenv("config.env")
else:
    load_dotenv(".env")

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.reload_config()
        
    def reload_config(self):
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL')
        self.to_email = os.getenv('TO_EMAIL')
        self.use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
        self.email_alerts_enabled = os.getenv('EMAIL_ALERTS_ENABLED', 'true').lower() == 'true'
        self.critical_alerts_only = os.getenv('CRITICAL_ALERTS_ONLY', 'true').lower() == 'true'
        
    def _test_connection_on_startup(self):
        """Teste la connexion SMTP au démarrage"""
        try:
            if self.smtp_username and self.smtp_password:
                self.test_connection()
                logger.info("Service email initialisé avec succès")
            else:
                logger.warning("Configuration SMTP incomplète - emails désactivés")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service email: {e}")
            
    def test_connection(self) -> Dict[str, Any]:
        """Teste la connexion SMTP"""
        try:
            if not self.smtp_username or not self.smtp_password:
                return {
                    "success": False,
                    "message": "Configuration SMTP incomplète",
                    "details": {
                        "username_configured": bool(self.smtp_username),
                        "password_configured": bool(self.smtp_password)
                    }
                }
                
            #create SMTP connection
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    server.starttls()
                    
            #authentication
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            
            return {
                "success": True,
                "message": "Connexion SMTP réussie",
                "details": {
                    "server": self.smtp_server,
                    "port": self.smtp_port,
                    "username": self.smtp_username,
                    "use_tls": self.use_tls,
                    "use_ssl": self.use_ssl
                }
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erreur d'authentification SMTP: {e}")
            return {
                "success": False,
                "message": "Erreur d'authentification SMTP",
                "error": str(e)
            }
        except smtplib.SMTPConnectError as e:
            logger.error(f"Erreur de connexion SMTP: {e}")
            return {
                "success": False,
                "message": "Impossible de se connecter au serveur SMTP",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Erreur SMTP inattendue: {e}")
            return {
                "success": False,
                "message": "Erreur SMTP inattendue",
                "error": str(e)
            }
            
    def get_configuration_status(self) -> Dict[str, Any]:
        """Récupère le statut de la configuration email"""
        return {
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "username_configured": bool(self.smtp_username),
            "password_configured": bool(self.smtp_password),
            "from_email": self.from_email,
            "use_tls": self.use_tls,
            "use_ssl": self.use_ssl,
            "email_alerts_enabled": self.email_alerts_enabled,
            "critical_alerts_only": self.critical_alerts_only
        }
        
    def send_alert_notification_to_user(self, user_email: str, alert_data: Dict[str, Any]) -> bool:
        """Envoie une notification d'alerte à un utilisateur"""
        self.reload_config()
        try:
            severity = alert_data.get('severity', 'info')
            equipment_name = alert_data.get('equipment_name', 'Équipement inconnu')
            message_text = alert_data.get('message', 'Alerte SNMP')
            created_at = alert_data.get('created_at', datetime.now().strftime('%d/%m/%Y à %H:%M:%S'))
            
            #determine color based on severity
            severity_colors = {
                'info': '#2196F3',
                'warning': '#FF9800', 
                'error': '#F44336',
                'critical': '#D32F2F'
            }
            color = severity_colors.get(severity, '#2196F3')
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = user_email
            message["Subject"] = f"Alerte {severity.upper()} - {equipment_name}"
            
            #HTML body
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .alert {{ border-left: 4px solid {color}; padding: 15px; margin: 10px 0; background-color: #f9f9f9; }}
                    .severity {{ font-weight: bold; color: {color}; }}
                    .equipment {{ font-weight: bold; color: #333; }}
                    .timestamp {{ color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <h2>Alerte SNMP Supervision</h2>
                <div class="alert">
                    <p><span class="severity">Sévérité: {severity.upper()}</span></p>
                    <p><span class="equipment">Équipement: {equipment_name}</span></p>
                    <p><strong>Message:</strong> {message_text}</p>
                    <p class="timestamp">Date: {created_at}</p>
                </div>
                <p>Cette alerte a été générée automatiquement par le système de supervision SNMP.</p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(html_body, "html"))
            
            return self._send_email(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification d'alerte à {user_email}: {e}")
            return False
            
    def send_critical_alert_email(self, alert_data: Dict[str, Any]) -> bool:
        """Envoie un email d'alerte critique"""
        self.reload_config()
        try:
            equipment_name = alert_data.get('equipment_name', 'Équipement inconnu')
            severity = alert_data.get('severity', 'critical')
            message_text = alert_data.get('message', 'Alerte critique')
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = self.to_email
            message["Subject"] = f"🚨 ALERTE CRITIQUE - {equipment_name}"
            
            body = f"""
            ALERTE CRITIQUE SNMP SUPERVISION
            
            Équipement: {equipment_name}
            Sévérité: {severity.upper()}
            Message: {message_text}
            
            Date: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
            
            Action immédiate requise!
            
            ---
            Service SNMP Supervision
            """
            
            message.attach(MIMEText(body, "plain"))
            
            return self._send_email(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email d'alerte critique: {e}")
            return False
            
    def send_report_email(self, report_data: Dict[str, Any]) -> bool:
        """Envoie un email avec rapport en pièce jointe"""
        self.reload_config()
        try:
            title = report_data.get('title', 'Rapport SNMP')
            period = report_data.get('period', 'Période non spécifiée')
            equipments = report_data.get('equipments', 'Équipements')
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = self.to_email
            message["Subject"] = f"📊 {title}"
            
            body = f"""
            Rapport SNMP Supervision
            
            Titre: {title}
            Période: {period}
            Équipements: {equipments}
            
            Date de génération: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
            
            Le rapport est joint à cet email.
            
            ---
            Service SNMP Supervision
            """
            
            message.attach(MIMEText(body, "plain"))
            
            #add report as attachment if available
            pdf_path = report_data.get('pdf_path')
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {os.path.basename(pdf_path)}"
                )
                message.attach(part)
            
            return self._send_email(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de rapport: {e}")
            return False
            
    def send_daily_summary_email(self, summary_data: Dict[str, Any]) -> bool:
        """Envoie un résumé quotidien par email"""
        self.reload_config()
        try:
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = self.to_email
            message["Subject"] = "📋 Résumé quotidien - SNMP Supervision"
            
            #prepare summary content
            total_equipments = summary_data.get('total_equipments', 0)
            online_equipments = summary_data.get('online_equipments', 0)
            total_alerts = summary_data.get('total_alerts', 0)
            critical_alerts = summary_data.get('critical_alerts', 0)
            
            body = f"""
            Résumé quotidien SNMP Supervision
            
            Date: {datetime.now().strftime('%d/%m/%Y')}
            
            ÉQUIPEMENTS:
            - Total: {total_equipments}
            - En ligne: {online_equipments}
            - Hors ligne: {total_equipments - online_equipments}
            
            ALERTES (24h):
            - Total: {total_alerts}
            - Critiques: {critical_alerts}
            - Warnings: {summary_data.get('warning_alerts', 0)}
            - Info: {summary_data.get('info_alerts', 0)}
            
            ---
            Service SNMP Supervision
            """
            
            message.attach(MIMEText(body, "plain"))
            
            return self._send_email(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du résumé quotidien: {e}")
            return False
            
    def _send_email(self, message: MIMEMultipart) -> bool:
        """Envoie un email via SMTP"""
        self.reload_config()
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.error("Configuration SMTP incomplète")
                return False
                
            #create SMTP connection
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    server.starttls()
                    
            #authentication
            server.login(self.smtp_username, self.smtp_password)
            
            #send email
            text = message.as_string()
            server.sendmail(self.from_email, message["To"], text)
            server.quit()
            
            logger.info(f"Email envoyé avec succès à {message['To']}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erreur d'authentification SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"Erreur de connexion SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False
            
    def update_configuration(self, new_config: Dict[str, Any]) -> bool:
        """Met à jour la configuration email"""
        try:
            if 'smtp_server' in new_config:
                self.smtp_server = new_config['smtp_server']
            if 'smtp_port' in new_config:
                self.smtp_port = int(new_config['smtp_port'])
            if 'smtp_username' in new_config:
                self.smtp_username = new_config['smtp_username']
            if 'smtp_password' in new_config:
                self.smtp_password = new_config['smtp_password']
            if 'from_email' in new_config:
                self.from_email = new_config['from_email']
            if 'smtp_use_tls' in new_config:
                self.use_tls = new_config['smtp_use_tls']
            if 'smtp_use_ssl' in new_config:
                self.use_ssl = new_config['smtp_use_ssl']
                
            logger.info("Configuration email mise à jour")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la configuration email: {e}")
            return False 