import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.device import Device
from app.db.models.alert import Alert
from app.services.mikrotik import analyze_device_health
from app.services.ai_analysis import analyze_logs_with_ai, generate_alert_from_ai_analysis

logger = logging.getLogger(__name__)

@celery_app.task
def monitor_devices() -> str:
    """
    Tarea programada para monitorear todos los dispositivos activos.
    """
    db = SessionLocal()
    try:
        # Obtener todos los dispositivos activos
        devices = db.query(Device).filter(Device.is_active == True).all()
        
        if not devices:
            return "No active devices found"
        
        total_devices = len(devices)
        processed_devices = 0
        total_alerts = 0
        
        for device in devices:
            try:
                # Analizar salud del dispositivo
                alerts = analyze_device_health(device, db)
                total_alerts += len(alerts)
                processed_devices += 1
                
                logger.info(f"Monitored device {device.name} ({device.ip_address}), generated {len(alerts)} alerts")
            except Exception as e:
                logger.error(f"Error monitoring device {device.name} ({device.ip_address}): {str(e)}")
        
        return f"Monitored {processed_devices}/{total_devices} devices, generated {total_alerts} alerts"
    
    except Exception as e:
        logger.error(f"Error in monitor_devices task: {str(e)}")
        return f"Error: {str(e)}"
    
    finally:
        db.close()

@celery_app.task
def analyze_device_logs_with_ai(device_id: int) -> str:
    """
    Tarea para analizar logs de un dispositivo con IA.
    """
    db = SessionLocal()
    try:
        # Obtener dispositivo
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return f"Device with ID {device_id} not found"
        
        if not device.is_active:
            return f"Device {device.name} is not active"
        
        try:
            from app.services.mikrotik import get_logs
            
            # Obtener logs recientes
            logs = get_logs(device, limit=100)
            
            # Analizar logs con IA
            analysis = analyze_logs_with_ai(logs, device.name)
            
            # Generar alerta basada en análisis
            alert = generate_alert_from_ai_analysis(analysis, device)
            
            if alert:
                db.add(alert)
                db.commit()
                return f"Generated AI analysis alert for device {device.name}"
            else:
                return f"No alert generated for device {device.name}"
        
        except Exception as e:
            logger.error(f"Error analyzing logs for device {device.name}: {str(e)}")
            return f"Error: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error in analyze_device_logs_with_ai task: {str(e)}")
        return f"Error: {str(e)}"
    
    finally:
        db.close()

@celery_app.task
def cleanup_old_alerts(days: int = 30) -> str:
    """
    Tarea para eliminar alertas antiguas.
    """
    db = SessionLocal()
    try:
        # Calcular fecha límite
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Eliminar alertas antiguas
        result = db.query(Alert).filter(Alert.created_at < cutoff_date).delete()
        db.commit()
        
        return f"Deleted {result} old alerts"
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_alerts task: {str(e)}")
        return f"Error: {str(e)}"
    
    finally:
        db.close()