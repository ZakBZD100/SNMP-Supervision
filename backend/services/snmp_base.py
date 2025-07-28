import gc
import time
import logging
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

#logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SNMPBase:
    def __init__(self):
        self.cache = {}
        self.cpu_cache = {}
        self.cache_timeout = 30  #30 seconds cache
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  #cleanup every 60 seconds

    def _safe_int(self, value) -> int:
        """Safely converts a value to integer"""
        try:
            if value is None:
                return 0
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # Try to convert to integer
                return int(value.strip())
            return 0
        except (ValueError, TypeError):
            return 0

    def _safe_str(self, value) -> str:
        """Safely converts a value to string"""
        try:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode('utf-8', errors='ignore')
            return str(value)
        except Exception:
            return ""

    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Gets cached data if not expired"""
        try:
            #periodic cache cleanup
            now = time.time()
            if now - self.last_cleanup > self.cleanup_interval:
                self._cleanup_cache()
                self.last_cleanup = now
            
            if key in self.cache:
                cached_data, timestamp = self.cache[key]
                if now - timestamp < self.cache_timeout:
                    logger.debug(f"Cache hit for {key}")
                    return cached_data
                else:
                    logger.debug(f"Cache expired for {key}")
                    del self.cache[key]
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    def _cache_data(self, key: str, data: Dict):
        """Caches data with timestamp"""
        try:
            self.cache[key] = (data, time.time())
            logger.debug(f"Cache set for {key}")
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")

    def _cleanup_cache(self):
        """Cleans expired cache"""
        try:
            now = time.time()
            expired_keys = []
            for key, (data, timestamp) in self.cache.items():
                if now - timestamp > self.cache_timeout:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cache cleaned: {len(expired_keys)} entries removed")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

    def test_connectivity(self, ip: str, community: str) -> bool:
        """Tests basic SNMP connectivity"""
        try:
            #local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=3, retries=1)
            
            #simple test with sysDescr
            result = session.get('1.3.6.1.2.1.1.1.0')
            if result and result.value:
                logger.info(f"SNMP connectivity OK for {ip}")
                return True
            else:
                logger.warning(f"No SNMP response for {ip}")
                return False
                
        except Exception as e:
            logger.error(f"SNMP connectivity error for {ip}: {e}")
            return False
        finally:
            gc.collect()

    def get_equipment_name(self, ip: str, community: str) -> str:
        """Gets equipment name"""
        try:
            #local import to avoid memory issues
            from easysnmp import Session
            session = Session(hostname=ip, community=community, version=2, timeout=3, retries=1)
            
            #try sysName first
            try:
                result = session.get('1.3.6.1.2.1.1.5.0')  # sysName
                if result and result.value:
                    return self._safe_str(result.value)
            except:
                pass
            
            #fallback to sysDescr
            try:
                result = session.get('1.3.6.1.2.1.1.1.0')  # sysDescr
                if result and result.value:
                    return self._safe_str(result.value)
            except:
                pass
            
            return f"Equipment-{ip}"
            
        except Exception as e:
            logger.error(f"Equipment name retrieval error for {ip}: {e}")
            return f"Equipment-{ip}"
        finally:
            gc.collect() 