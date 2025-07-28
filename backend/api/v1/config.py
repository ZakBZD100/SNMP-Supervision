from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os
from ...services.auth_service import auth_service
from ...models.user import User
from ...services.notification_service import NotificationService
from ...services.snmp_service import SNMPService

router = APIRouter(prefix="/config", tags=["configuration"])

#equipment configuration file
EQUIPMENTS_CONFIG_FILE = "equipments_config.json"
equipments_config = []

def load_equipments_config():
    """Charge la configuration des équipements"""
    global equipments_config
    
    if os.path.exists(EQUIPMENTS_CONFIG_FILE):
        try:
            with open(EQUIPMENTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                equipments_config = json.load(f)
        except Exception as e:
            print(f"Erreur chargement config équipements: {e}")
            equipments_config = []
    else:
        #default configuration
        equipments_config = [
            {
                "id": 1,
                "name": "Serveur Ubuntu",
                "ip": "192.168.1.100",
                "type": "server",
                "community": "public",
                "enabled": True,
                "description": "Serveur principal Ubuntu"
            },
            {
                "id": 2,
                "name": "Switch Cisco",
                "ip": "192.168.1.1",
                "type": "switch",
                "community": "public",
                "enabled": True,
                "description": "Switch principal Cisco"
            }
        ]
        save_equipments_config()

def save_equipments_config():
    """Sauvegarde la configuration des équipements"""
    try:
        with open(EQUIPMENTS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(equipments_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde config équipements: {e}")

@router.get("/equipments")
def get_equipments_config(current_user: User = Depends(auth_service.get_current_user)):
    """Récupère la configuration des équipements (lecture seule pour tous)"""
    load_equipments_config()
    return equipments_config

@router.post("/equipments")
def add_equipment(equipment_data: Dict[str, Any], current_user: User = Depends(auth_service.get_current_user)):
    """Ajoute un nouvel équipement (admin seulement)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé - Admin seulement")
    
    load_equipments_config()
    
            #generate new ID
    new_id = max([eq.get('id', 0) for eq in equipments_config], default=0) + 1
    
    new_equipment = {
        "id": new_id,
        "name": equipment_data.get("name", "Nouvel équipement"),
        "ip": equipment_data.get("ip", ""),
        "type": equipment_data.get("type", "server"),
        "community": equipment_data.get("community", "public"),
        "enabled": equipment_data.get("enabled", True),
        "description": equipment_data.get("description", ""),
        "created_at": datetime.now().isoformat(),
        "created_by": current_user.username
    }
    
    equipments_config.append(new_equipment)
    save_equipments_config()
    
    return {
        "success": True,
        "message": "Équipement ajouté avec succès",
        "equipment": new_equipment
    }

@router.put("/equipments/{equipment_id}")
def update_equipment(equipment_id: int, equipment_data: Dict[str, Any], current_user: User = Depends(auth_service.get_current_user)):
    """Met à jour un équipement (admin seulement)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé - Admin seulement")
    
    load_equipments_config()
    
    #find equipment
    equipment = next((eq for eq in equipments_config if eq.get('id') == equipment_id), None)
    if not equipment:
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    
    #update fields
    for key, value in equipment_data.items():
        if key in ['name', 'ip', 'type', 'community', 'enabled', 'description']:
            equipment[key] = value
    
    equipment['updated_at'] = datetime.now().isoformat()
    equipment['updated_by'] = current_user.username
    
    save_equipments_config()
    
    return {
        "success": True,
        "message": "Équipement mis à jour avec succès",
        "equipment": equipment
    }

@router.delete("/equipments/{equipment_id}")
def delete_equipment(equipment_id: int, current_user: User = Depends(auth_service.get_current_user)):
    """Supprime un équipement (admin seulement)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé - Admin seulement")
    
    load_equipments_config()
    
    #find and delete equipment
    global equipments_config
    equipments_config = [eq for eq in equipments_config if eq.get('id') != equipment_id]
    save_equipments_config()
    
    return {
        "success": True,
        "message": f"Équipement {equipment_id} supprimé avec succès"
    }

@router.post("/equipments/{equipment_id}/test")
def test_equipment_connection(equipment_id: int, current_user: User = Depends(auth_service.get_current_user)):
    """Teste la connexion SNMP d'un équipement"""
    load_equipments_config()
    
    #find equipment
    equipment = next((eq for eq in equipments_config if eq.get('id') == equipment_id), None)
    if not equipment:
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    
    try:
        #test SNMP connection
        snmp_service = SNMPService()
        result = snmp_service.test_connection(
            equipment['ip'],
            equipment['community'],
            equipment['type']
        )
        
        return {
            "success": True,
            "message": "Test de connexion effectué",
            "equipment": equipment,
            "test_result": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur lors du test: {str(e)}",
            "equipment": equipment
        }

@router.get("/notifications")
def get_notifications_config(current_user: User = Depends(auth_service.get_current_user)):
    """Récupère la configuration des notifications (lecture seule pour tous)"""
    notification_service = NotificationService()
    config = notification_service.get_notification_config()
    
    #mask email for non-admin users
    if current_user.role != "admin":
        config["notification_email"] = "***@***.***"
    
    return config

@router.put("/notifications")
def update_notifications_config(new_config: Dict[str, Any], current_user: User = Depends(auth_service.get_current_user)):
    """Met à jour la configuration des notifications (admin seulement)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé - Admin seulement")
    
    notification_service = NotificationService()
    result = notification_service.update_notification_config(new_config)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@router.post("/notifications/test")
def test_notification(current_user: User = Depends(auth_service.get_current_user)):
    """Teste l'envoi d'une notification (admin seulement)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé - Admin seulement")
    
    notification_service = NotificationService()
    result = notification_service.test_notification()
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@router.post("/notifications/send")
def send_notifications(current_user: User = Depends(auth_service.get_current_user)):
    """Envoie les notifications groupées (admin seulement)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé - Admin seulement")
    
    notification_service = NotificationService()
    result = notification_service.send_grouped_notifications()
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@router.get("/system")
def get_system_config(current_user: User = Depends(auth_service.get_current_user)):
    """Récupère la configuration système (lecture seule pour tous)"""
    load_equipments_config()
    
    #system statistics
    total_equipments = len(equipments_config)
    enabled_equipments = len([eq for eq in equipments_config if eq.get('enabled', True)])
    servers = len([eq for eq in equipments_config if eq.get('type') == 'server'])
    switches = len([eq for eq in equipments_config if eq.get('type') == 'switch'])
    
    notification_service = NotificationService()
    notification_config = notification_service.get_notification_config()
    
    return {
        "equipments": {
            "total": total_equipments,
            "enabled": enabled_equipments,
            "disabled": total_equipments - enabled_equipments,
            "servers": servers,
            "switches": switches
        },
        "notifications": {
            "enabled": notification_config.get("notifications_enabled", False),
            "interval": notification_config.get("notification_interval", 300),
            "email_configured": bool(notification_config.get("notification_email"))
        },
        "user_role": current_user.role,
        "last_updated": datetime.now().isoformat()
    } 