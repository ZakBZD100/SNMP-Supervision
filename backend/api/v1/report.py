from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from backend.services.report_service import report_service
import io

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/generate")
def generate_report(date: str = None):
    """Génère un rapport PDF détaillé"""
    try:
        #use provided date or current date
        if not date:
            date = datetime.now().strftime("%d %B %Y")
        
        #generate report
        pdf_buffer = report_service.generate_report(date)
        
        #create filename
        filename = f"rapport_supervision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        #return PDF as streaming
        return StreamingResponse(
            io.BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du rapport: {str(e)}")

@router.get("/alerts")
def generate_alerts_report(date: str = None):
    """Génère un rapport PDF des alertes"""
    try:
        #use provided date or current date
        if not date:
            date = datetime.now().strftime("%d %B %Y")
        
        #generate alerts report
        pdf_buffer = report_service.generate_alerts_report(date)
        
        #create filename
        filename = f"rapport_alertes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        #return PDF as streaming
        return StreamingResponse(
            io.BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du rapport d'alertes: {str(e)}")

@router.get("/preview")
def preview_report_info():
    """Aperçu des informations du rapport"""
    return {
        "message": "Rapport de supervision SNMP",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "sections": [
            "📋 Résumé exécutif",
            "🎯 Statistiques clés", 
            "🖥️ Utilisation CPU",
            "🧠 Utilisation Mémoire",
            "💾 Utilisation Disque",
            "🌐 Trafic Réseau",
            "📊 Résumé des métriques",
            "🚨 Analyse des alertes",
            "💡 Recommandations",
            "✅ Conclusion"
        ],
        "features": [
            "Graphiques haute qualité",
            "Tableaux détaillés",
            "Analyse des alertes",
            "Recommandations",
            "Format PDF professionnel"
        ]
    } 