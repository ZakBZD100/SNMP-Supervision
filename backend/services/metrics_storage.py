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
        """creates the storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            
    def get_equipment_file(self, equipment_id: int) -> str:
        """returns the storage file path for an equipment"""
        return os.path.join(self.storage_dir, f"equipment_{equipment_id}.json")
        
    def save_metrics(self, equipment_id: int, metrics: Dict, timestamp: Optional[float] = None):
        """saves equipment metrics with timestamp"""
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
            logger.debug(f"metrics saved for equipment {equipment_id}")
        except Exception as e:
            logger.error(f"error saving metrics for equipment {equipment_id}: {e}")
            
    def load_metrics(self, equipment_id: int) -> List[Dict]:
        """loads historical metrics for an equipment"""
        file_path = self.get_equipment_file(equipment_id)
        
        if not os.path.exists(file_path):
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"error loading metrics for equipment {equipment_id}: {e}")
            return []
            
    def get_recent_metrics(self, equipment_id: int, hours: int = 24) -> List[Dict]:
        """gets recent metrics (last X hours)"""
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
        """prepares data for charts"""
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
                #addition: store complete interface state for each timestamp
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
        """cleans old data (more than X days)"""
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
                    
                    #save filtered data
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
                        
                    logger.info(f"data cleaned for {filename}: {len(data)} -> {len(filtered_data)} entries")
                    
                except Exception as e:
                    logger.error(f"error cleaning {filename}: {e}")

#global metrics storage instance
metrics_storage = MetricsStorage() 