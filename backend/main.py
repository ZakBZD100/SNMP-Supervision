from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import sys
import os

#add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.v1.routes import router as api_v1_router

#load environment variables
load_dotenv()
if os.path.exists("config.env"):
    load_dotenv("config.env")
else:
    load_dotenv(".env")

#logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#create FastAPI application
app = FastAPI(
    title="SNMP Supervision API",
    description="API de supervision SNMP professionnelle",
    version="1.0.0"
)

#CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À configurer selon vos besoins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Route racine"""
    return {
        "message": "SNMP Supervision API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Vérification de l'état de santé de l'API"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "api": "running",
                "snmp": "available",
                "email": "available"
            }
        }
    except Exception as e:
        logger.error(f"Erreur lors du health check: {e}")
        raise HTTPException(status_code=500, detail="Service indisponible")

@app.get("/api/v1/status")
async def get_status():
    """Récupération du statut détaillé"""
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    #server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Démarrage du serveur SNMP Supervision sur {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    ) 