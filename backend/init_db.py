#!/usr/bin/env python3
"""
Script d'initialisation de la base de données SNMP Supervision
"""

import sys
import os

#add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import engine, SessionLocal, Base
from backend.models.equipment import Equipment
from backend.models.alert import Alert
from backend.models.user import User
from backend.services.auth_service import auth_service

def init_database():
    """Initialise la base de données avec les tables et données de test"""
    print("Création des tables...")
    
    #import all models so they are registered with Base
    import backend.models.user
    import backend.models.equipment
    import backend.models.alert
    
    #create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Tables créées avec succès")
    
    #create default admin user
    db = SessionLocal()
    try:
        auth_service.create_admin_user(db)
    except Exception as e:
        print(f"Erreur lors de la création de l'admin: {e}")
    finally:
        db.close()
    
    #add real equipment
    db = SessionLocal()
    try:
        #remove old test equipment
        db.query(Equipment).delete()
        db.commit()
        
        print("Ajout des équipements réels...")
        
        # Équipements réels
        real_equipments = [
            {
                "name": "Switch Cisco",
                "ip": "192.168.57.2",
                "community": "public",
                "type": "switch",
                "snmp_version": "v1"
            },
            {
                "name": "Serveur Ubuntu GNS3",
                "ip": "192.168.57.3",
                "community": "public",
                "type": "server",
                "snmp_version": "v1"
            }
        ]
        
        for eq_data in real_equipments:
            equipment = Equipment(**eq_data)
            db.add(equipment)
        
        db.commit()
        print(f"✓ {len(real_equipments)} équipements réels ajoutés")
        print("  - Switch Cisco (192.168.57.2)")
        print("  - Serveur Ubuntu GNS3 (192.168.57.3)")
            
    except Exception as e:
        print(f"Erreur lors de l'ajout des équipements: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("Initialisation de la base de données terminée !")

if __name__ == "__main__":
    init_database() 