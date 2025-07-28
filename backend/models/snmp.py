from pydantic import BaseModel
from typing import Optional
 
class SNMPDevice(BaseModel):
    ip: str
    community: str = "public"
    type: str = "server"  #or "switch"
    name: Optional[str] = None 