import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MetricsStorage:
    def __init__(self, storage_dir: str = "metrics_data"):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
        
    def ensure_storage_dir(self):
        """Crée le répertoire de stockage s'il n'existe pas"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            
    def get_equipment_file(self, equipment_id: int) -> str:
        """Retourne le chemin du fichier de stockage pour un équipement"""
        return os.path.join(self.storage_dir, f"equipment_{equipment_id}.json")
        
    def save_metrics(self, equipment_id: int, metrics: Dict, timestamp: Optional[float] = None):
        """Sauvegarde les métriques d'un équipement avec timestamp"""
        if timestamp is None:
            timestamp = time.time()
            
        file_path = self.get_equipment_file(equipment_id)
        
        #load existing data
        existing_data = self.load_metrics(equipment_id)
        
        #add new metrics
        metric_entry = {
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
            "metrics": metrics
        }
        
        existing_data.append(metric_entry)
        
        #keep only the last 1000 points (about 16 hours at 1 point/minute)
        if len(existing_data) > 1000:
            existing_data = existing_data[-1000:]
            
        #save
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Métriques sauvegardées pour équipement {equipment_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques pour équipement {equipment_id}: {e}")
            
    def load_metrics(self, equipment_id: int) -> List[Dict]:
        """Charge les métriques historiques d'un équipement"""
        file_path = self.get_equipment_file(equipment_id)
        
        if not os.path.exists(file_path):
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Erreur lors du chargement des métriques pour équipement {equipment_id}: {e}")
            return []
            
    def get_recent_metrics(self, equipment_id: int, hours: int = 24) -> List[Dict]:
        """Récupère les métriques récentes (dernières X heures)"""
        all_metrics = self.load_metrics(equipment_id)
        
        if not all_metrics:
            return []
            
        #filter by timestamp
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [
            entry for entry in all_metrics 
            if entry.get('timestamp', 0) >= cutoff_time
        ]
        
        return recent_metrics
        
    def get_metrics_for_chart(self, equipment_id: int, hours: int = 24) -> Dict:
        """Prépare les données pour les graphiques"""
        recent_metrics = self.get_recent_metrics(equipment_id, hours)
        
        if not recent_metrics:
            return {
                'timestamps': [],
                'cpu': [],
                'memory': [],
                'disk': [],
                'interfaces': [],
                'traffic_in': [],
                'traffic_out': []
            }
            
        #sort by timestamp
        recent_metrics.sort(key=lambda x: x.get('timestamp', 0))
        
        timestamps = []
        cpu_values = []
        memory_values = []
        disk_values = []
        interfaces_values = []
        traffic_in_values = []
        traffic_out_values = []
        interfaces_states = []
        for entry in recent_metrics:
            timestamp = entry.get('timestamp', 0)
            metrics = entry.get('metrics', {})
            
            timestamps.append(timestamp)
            
            #CPU
            if 'cpu_usage' in metrics:
                cpu_values.append(metrics['cpu_usage'])
            elif 'cpu_percent' in metrics:
                cpu_values.append(metrics['cpu_percent'])
            else:
                cpu_values.append(0)
                
            #Memory
            if 'memory_usage' in metrics:
                memory_values.append(metrics['memory_usage'])
            elif 'memory_percent' in metrics:
                memory_values.append(metrics['memory_percent'])
            else:
                memory_values.append(0)
                
            #Disk
            if 'disk_usage' in metrics:
                disk_values.append(metrics['disk_usage'])
            elif 'disk_percent' in metrics:
                disk_values.append(metrics['disk_percent'])
            else:
                disk_values.append(0)
                
            #Interfaces (for switches)
            if 'interfaces' in metrics:
                interfaces_values.append(len(metrics['interfaces']))
                # Ajout : stocker l'état complet des interfaces pour chaque timestamp
                interfaces_states.append(metrics['interfaces'])
            else:
                interfaces_values.append(0)
                interfaces_states.append([])
                
            #Traffic (for switches)
            total_traffic_in = 0
            total_traffic_out = 0
            if 'interfaces' in metrics:
                for interface in metrics['interfaces']:
                    total_traffic_in += interface.get('traffic_in', 0)
                    total_traffic_out += interface.get('traffic_out', 0)
                    
            traffic_in_values.append(total_traffic_in)
            traffic_out_values.append(total_traffic_out)
            
        return {
            'timestamps': timestamps,
            'cpu': cpu_values,
            'memory': memory_values,
            'disk': disk_values,
            'interfaces': interfaces_states,
            'traffic_in': traffic_in_values,
            'traffic_out': traffic_out_values
        }
        
    def cleanup_old_data(self, days: int = 7):
        """Nettoie les anciennes données (plus de X jours)"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        for filename in os.listdir(self.storage_dir):
            if filename.startswith('equipment_') and filename.endswith('.json'):
                file_path = os.path.join(self.storage_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    #filter old data
                    filtered_data = [
                        entry for entry in data 
                        if entry.get('timestamp', 0) >= cutoff_time
                    ]
                    
                    # Sauvegarder les données filtrées
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
                        
                    logger.info(f"Données nettoyées pour {filename}: {len(data)} -> {len(filtered_data)} entrées")
                    
                except Exception as e:
                    logger.error(f"Erreur lors du nettoyage de {filename}: {e}")

# Instance globale du stockage de métriques
metrics_storage = MetricsStorage() 