from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random
import json
import os
from ...services.snmp_service import SNMPService
from ...services.notification_service import NotificationService

router = APIRouter(prefix="/alerts", tags=["alerts"])

#permanent alert storage file
ALERTS_FILE = "alerts_storage.json"
alerts_storage = []
alert_id_counter = 1
snmp_service = SNMPService()
notification_service = NotificationService()

def load_alerts_from_file():
    """Charge les alertes depuis le fichier de stockage"""
    global alerts_storage, alert_id_counter
    
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                alerts_storage = data.get('alerts', [])
                alert_id_counter = data.get('counter', 1)
        except Exception as e:
            print(f"Erreur chargement alertes: {e}")
            alerts_storage = []
            alert_id_counter = 1

def save_alerts_to_file():
    """Sauvegarde les alertes dans le fichier de stockage"""
    try:
        data = {
            'alerts': alerts_storage,
            'counter': alert_id_counter,
            'last_updated': datetime.now().isoformat()
        }
        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde alertes: {e}")

def generate_dynamic_alerts():
    """Génère des alertes dynamiques basées sur les métriques réelles (désactive le spam et ne garde que les alertes importantes pour les switches)"""
    global alert_id_counter
    current_time = datetime.now()
    new_alerts = []
    #disable random alert spam, only create important critical alerts
    #examples:
    # - CPU > 90% (serveur)
    # - Mémoire > 90% (serveur)
    # - Disque > 95% (serveur)
    # - Interface DOWN (switch)
    # - Erreur critique sur switch
    # (Ici, on ne fait rien en random, la vraie logique doit être branchée sur les vraies métriques)
    return new_alerts

def send_email_for_critical_alerts(new_alerts: List[Dict[str, Any]]):
    """Envoie des emails pour les alertes critiques et erreurs"""
    try:
        #filter critical and error alerts that haven't been sent yet
        critical_alerts = [
            alert for alert in new_alerts 
            if alert.get('level') in ['critical', 'error'] and not alert.get('email_sent', False)
        ]
        
        if not critical_alerts:
            print("ℹ️ Aucune alerte critique/erreur à envoyer")
            return
        
        print(f"📧 Envoi de {len(critical_alerts)} alertes critiques/erreurs par email...")
        
        #send grouped notifications
        result = notification_service.send_grouped_notifications()
        
        if result.get('success'):
            #mark alerts as sent
            current_time = datetime.now()
            for alert in critical_alerts:
                alert['email_sent'] = True
                alert['email_sent_at'] = current_time.isoformat()
            
            #save changes
            save_alerts_to_file()
            print(f"✅ Emails envoyés pour {len(critical_alerts)} alertes critiques")
            print(f"📬 Destinataire: {result.get('details', {}).get('recipient', 'Non spécifié')}")
        else:
            print(f"❌ Erreur envoi emails: {result.get('message', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur envoi emails alertes: {e}")
        import traceback
        traceback.print_exc()

@router.get("")
def list_alerts():
    """Récupère la liste des alertes, synchronisée avec les métriques en temps réel"""
    global alerts_storage

    #synchronize with metrics (generates critical alerts if needed)
    check_metrics_and_alert()
    
    #load existing alerts
    load_alerts_from_file()
    
    #generate new dynamic alerts
    new_alerts = generate_dynamic_alerts()
    alerts_storage.extend(new_alerts)
    
    #keep only the last 1000 alerts (more history)
    if len(alerts_storage) > 1000:
        alerts_storage = alerts_storage[-1000:]
    
    #add some base alerts if none exist
    if not alerts_storage:
        current_time = datetime.now()
        alerts_storage = [
            {
                "id": "1",
                "type": "cpu",
                "level": "warning",
                "message": "CPU usage above 80% - Monitoring active",
                "timestamp": (current_time - timedelta(minutes=5)).isoformat(),
                "equipment": "Serveur Ubuntu",
                "date": (current_time - timedelta(minutes=5)).strftime("%d/%m/%Y"),
                "time": (current_time - timedelta(minutes=5)).strftime("%H:%M:%S"),
                "email_sent": False,
                "email_sent_at": None
            },
            {
                "id": "2",
                "type": "memory",
                "level": "info",
                "message": "Memory usage normal - System healthy",
                "timestamp": (current_time - timedelta(minutes=10)).isoformat(),
                "equipment": "Switch Cisco",
                "date": (current_time - timedelta(minutes=10)).strftime("%d/%m/%Y"),
                "time": (current_time - timedelta(minutes=10)).strftime("%H:%M:%S"),
                "email_sent": False,
                "email_sent_at": None
            },
            {
                "id": "3",
                "type": "disk",
                "level": "error",
                "message": "Disk space critical - Immediate action required",
                "timestamp": (current_time - timedelta(minutes=15)).isoformat(),
                "equipment": "Serveur Ubuntu",
                "date": (current_time - timedelta(minutes=15)).strftime("%d/%m/%Y"),
                "time": (current_time - timedelta(minutes=15)).strftime("%H:%M:%S"),
                "email_sent": False,
                "email_sent_at": None
            },
            {
                "id": "4",
                "type": "network",
                "level": "warning",
                "message": "High network traffic detected on interface eth0",
                "timestamp": (current_time - timedelta(minutes=20)).isoformat(),
                "equipment": "Switch Cisco",
                "date": (current_time - timedelta(minutes=20)).strftime("%d/%m/%Y"),
                "time": (current_time - timedelta(minutes=20)).strftime("%H:%M:%S"),
                "email_sent": False,
                "email_sent_at": None
            },
            {
                "id": "5",
                "type": "interface",
                "level": "critical",
                "message": "Interface GigabitEthernet0/1 is down - Network issue",
                "timestamp": (current_time - timedelta(minutes=25)).isoformat(),
                "equipment": "Switch Cisco",
                "date": (current_time - timedelta(minutes=25)).strftime("%d/%m/%Y"),
                "time": (current_time - timedelta(minutes=25)).strftime("%H:%M:%S"),
                "email_sent": False,
                "email_sent_at": None
            }
        ]
    
    #save alerts
    save_alerts_to_file()
    
    #send emails for new critical/error alerts
    send_email_for_critical_alerts(new_alerts)
    
    return alerts_storage

@router.post("")
def create_alert():
    """Crée une nouvelle alerte"""
    global alert_id_counter, alerts_storage
    
    current_time = datetime.now()
    new_alert = {
        "id": str(alert_id_counter),
        "type": "system",
        "level": "info",
        "message": "Manual alert created",
        "timestamp": current_time.isoformat() + "Z",
        "equipment": "System",
        "date": current_time.strftime("%d/%m/%Y"),
        "time": current_time.strftime("%H:%M:%S")
    }
    
    alerts_storage.append(new_alert)
    alert_id_counter += 1
    
    #save
    save_alerts_to_file()
    
    return {"message": "Alerte créée", "alert": new_alert}

@router.delete("/{alert_id}")
def delete_alert(alert_id: str):
    """Supprime une alerte"""
    global alerts_storage
    
    alerts_storage = [alert for alert in alerts_storage if alert["id"] != alert_id]
    save_alerts_to_file()
    
    return {"message": f"Alerte {alert_id} supprimée"}

@router.put("/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    """Marque une alerte comme résolue"""
    try:
        load_alerts_from_file()
        
        #find alert
        alert = next((a for a in alerts_storage if a.get('id') == alert_id), None)
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alerte non trouvée")
        
        #mark as resolved
        alert['resolved'] = True
        alert['resolved_at'] = datetime.now().isoformat()
        alert['status'] = 'resolved'
        
        #save
        save_alerts_to_file()
        
        return {
            "success": True,
            "message": f"Alerte {alert_id} marquée comme résolue",
            "alert": alert
        }
        
    except Exception as e:
        print(f"Erreur résolution alerte: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la résolution: {str(e)}")

@router.put("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str):
    """Marque une alerte comme acquittée"""
    try:
        load_alerts_from_file()
        
        #find alert
        alert = next((a for a in alerts_storage if a.get('id') == alert_id), None)
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alerte non trouvée")
        
        #mark as acknowledged
        alert['acknowledged'] = True
        alert['acknowledged_at'] = datetime.now().isoformat()
        alert['status'] = 'acknowledged'
        
        #save
        save_alerts_to_file()
        
        return {
            "success": True,
            "message": f"Alerte {alert_id} acquittée",
            "alert": alert
        }
        
    except Exception as e:
        print(f"Erreur acquittement alerte: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'acquittement: {str(e)}")

@router.get("/{alert_id}/details")
def get_alert_details(alert_id: str):
    """Récupère les détails complets d'une alerte"""
    try:
        load_alerts_from_file()
        
        #find alert
        alert = next((a for a in alerts_storage if a.get('id') == alert_id), None)
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alerte non trouvée")
        
        #enrich with additional details
        alert_details = {
            **alert,
            "duration": "Calculé depuis la création",
            "equipment_status": "En ligne",
            "related_alerts": [],
            "recommended_actions": []
        }
        
        #add recommended actions based on type
        if alert.get('type') == 'cpu':
            alert_details['recommended_actions'] = [
                "Vérifier les processus gourmands",
                "Optimiser la configuration",
                "Ajouter des ressources si nécessaire"
            ]
        elif alert.get('type') == 'memory':
            alert_details['recommended_actions'] = [
                "Libérer la mémoire cache",
                "Redémarrer les services",
                "Vérifier les fuites mémoire"
            ]
        elif alert.get('type') == 'disk':
            alert_details['recommended_actions'] = [
                "Nettoyer les fichiers temporaires",
                "Archiver les anciens logs",
                "Augmenter l'espace disque"
            ]
        elif alert.get('type') == 'network':
            alert_details['recommended_actions'] = [
                "Vérifier la bande passante",
                "Analyser le trafic réseau",
                "Optimiser la configuration réseau"
            ]
        
        return alert_details
        
    except Exception as e:
        print(f"Erreur récupération détails alerte: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.get("/stats")
def get_alerts_stats():
    """Récupère les statistiques des alertes"""
    load_alerts_from_file()
    
    if not alerts_storage:
        return {
            "total": 0,
            "by_level": {},
            "by_type": {},
            "by_date": {},
            "email_stats": {
                "sent": 0,
                "pending": 0,
                "total_critical": 0,
                "total_error": 0
            }
        }
    
    #statistics by level
    by_level = {}
    by_type = {}
    by_date = {}
    email_sent = 0
    email_pending = 0
    total_critical = 0
    total_error = 0
    
    for alert in alerts_storage:
        level = alert.get("level", "unknown")
        alert_type = alert.get("type", "unknown")
        date = alert.get("date", "unknown")
        email_sent_status = alert.get("email_sent", False)
        
        by_level[level] = by_level.get(level, 0) + 1
        by_type[alert_type] = by_type.get(alert_type, 0) + 1
        by_date[date] = by_date.get(date, 0) + 1
        
        if level in ['critical', 'error']:
            if level == 'critical':
                total_critical += 1
            if level == 'error':
                total_error += 1
            
            if email_sent_status:
                email_sent += 1
            else:
                email_pending += 1
    
    return {
        "total": len(alerts_storage),
        "by_level": by_level,
        "by_type": by_type,
        "by_date": by_date,
        "email_stats": {
            "sent": email_sent,
            "pending": email_pending,
            "total_critical": total_critical,
            "total_error": total_error
        }
    }

#addition: real-time critical alert generation on each call
@router.api_route("/metrics-check", methods=["GET", "POST"])
def check_metrics_and_alert():
    """Vérifie les métriques de tous les équipements et génère/envoie des alertes critiques si besoin."""
    from backend.database.db import SessionLocal
    db = SessionLocal()
    try:
        from backend.models.equipment import Equipment
        equipments = db.query(Equipment).all()
        alerts = []
        for eq in equipments:
            metrics = snmp_service.get_equipment_metrics(eq)
            if not metrics:
                continue
            #server: CPU > 90%
            if eq.type == 'server' and metrics.get('cpu_usage', 0) > 90:
                alerts.append({
                    'type': 'cpu', 'level': 'critical', 'message': f'CPU > 90% sur {eq.name}', 'equipment': eq.name
                })
            #server: RAM > 90%
            if eq.type == 'server' and metrics.get('memory_usage', 0) > 90:
                alerts.append({
                    'type': 'memory', 'level': 'critical', 'message': f'RAM > 90% sur {eq.name}', 'equipment': eq.name
                })
            #switch: interface down (put as info to avoid spam)
            if eq.type == 'switch' and 'interfaces' in metrics:
                for iface in metrics['interfaces']:
                    if iface.get('oper_status') == 2:
                        alerts.append({
                            'type': 'interface', 'level': 'info', 'message': f"Interface {iface.get('name')} DOWN sur {eq.name}", 'equipment': eq.name
                        })
        #save and send critical alerts
        if alerts:
            load_alerts_from_file()
            global alert_id_counter
            for alert in alerts:
                alert['id'] = str(alert_id_counter)
                alert['timestamp'] = datetime.now().isoformat()
                alert['email_sent'] = False
                alerts_storage.append(alert)
                alert_id_counter += 1
            save_alerts_to_file()
            notification_service.send_grouped_notifications()
        return {'success': True, 'alerts': alerts}
    finally:
        db.close() 

@router.post("/test-email")
async def test_email(request: Request):
    data = await request.json()
    email = data.get('email')
    if not email:
        return {"success": False, "message": "Aucune adresse email fournie"}
    try:
        result = notification_service.email_service.send_alert_notification_to_user(email, {
            'severity': 'info',
            'equipment_name': 'Test',
            'message': 'Ceci est un email de test SNMP Supervision',
            'created_at': datetime.now().strftime('%d/%m/%Y à %H:%M:%S')
        })
        if result:
            return {"success": True, "message": "Email de test envoyé avec succès"}
        else:
            return {"success": False, "message": "Erreur lors de l'envoi SMTP (voir logs)"}
    except Exception as e:
        return {"success": False, "message": str(e)} 