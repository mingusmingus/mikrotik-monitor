import logging
from datetime import datetime, timedelta
from typing import List

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.device import Device
from app.db.models.alert import Alert
from app.services.mikrotik import analyze_device_health, get_health, get_logs
from app.services.ai_analysis import analyze_logs_with_ai, generate_alert_from_ai_analysis

logger = logging.getLogger(__name__)

@celery_app.task
def monitor_devices() -> str:
    """Monitorea dispositivos cada 15 min"""
    db = SessionLocal()
    try:
        devices = db.query(Device).filter(Device.activo==True).all()
        for device in devices:
            analyze_device_health(device, db)
        return f"Monitoreados {len(devices)} dispositivos"
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

@shared_task(
    queue="monitor",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3
)
def poll_devices():
    """Monitorea todos los dispositivos activos"""
    db = SessionLocal()
    try:
        devices = db.query(Device).filter(Device.activo==True).all()
        alerts_generated = 0

        for device in devices:
            try:
                # Obtener métricas y logs
                health = get_health(device)
                logs = get_logs(device, limit=50)

                # Analizar métricas de salud
                if health['cpu_load'] > 80:
                    db.add(Alert(
                        equipo_id=device.id,
                        estado="Alerta Mayor",
                        titulo=f"CPU Alta: {health['cpu_load']}%",
                        descripcion=f"La carga de CPU del dispositivo {device.nombre} está alta"
                    ))
                    alerts_generated += 1

                memory_used_pct = (health['memory_used'] / health['memory_total']) * 100
                if memory_used_pct > 90:
                    db.add(Alert(
                        equipo_id=device.id,
                        estado="Alerta Crítica", 
                        titulo=f"Memoria Crítica: {memory_used_pct:.1f}%",
                        descripcion=f"El uso de memoria en {device.nombre} es crítico"
                    ))
                    alerts_generated += 1

                # Analizar logs críticos recientes
                critical_logs = [log for log in logs if log['severity'] == 'critical']
                if critical_logs:
                    db.add(Alert(
                        equipo_id=device.id,
                        estado="Alerta Crítica",
                        titulo="Logs Críticos Detectados",
                        descripcion=f"Se encontraron {len(critical_logs)} logs críticos"
                    ))
                    alerts_generated += 1

                db.commit()

            except Exception as e:
                db.add(Alert(
                    equipo_id=device.id,
                    estado="Alerta Crítica",
                    titulo="Error de Monitoreo",
                    descripcion=f"Error al monitorear dispositivo: {str(e)}"
                ))
                db.commit()
                alerts_generated += 1

        return f"Monitoreados {len(devices)} dispositivos, generadas {alerts_generated} alertas"

    finally:
        db.close()