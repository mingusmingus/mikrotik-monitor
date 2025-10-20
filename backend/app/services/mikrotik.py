import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from librouteros import connect
from librouteros.exceptions import ConnectionError, LoginError, FatalError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.core.security import decrypt_credentials
from app.db.models.device import Device
from app.db.models.alert import Alert

logger = logging.getLogger(__name__)

def test_mikrotik_connection(host: str, port: int, username: str, password: str) -> bool:
    """
    Prueba la conexión a un dispositivo MikroTik.
    Retorna True si la conexión es exitosa, lanza una excepción en caso contrario.
    """
    try:
        api = connect(
            host=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )
        # Obtener información del sistema para verificar conexión
        system_resource = api.path('system', 'resource')
        for resource in system_resource:
            logger.info(f"Connected to MikroTik device: {resource.get('board-name', 'Unknown')}")
            return True
    except ConnectionError as e:
        logger.error(f"Connection error to MikroTik device {host}: {str(e)}")
        raise ValueError(f"Connection error: {str(e)}")
    except LoginError as e:
        logger.error(f"Login error to MikroTik device {host}: {str(e)}")
        raise ValueError(f"Login error: {str(e)}")
    except FatalError as e:
        logger.error(f"Fatal error connecting to MikroTik device {host}: {str(e)}")
        raise ValueError(f"Fatal error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error connecting to MikroTik device {host}: {str(e)}")
        raise ValueError(f"Unexpected error: {str(e)}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((ConnectionError, LoginError))
)
def connect_to_device(device: Device) -> Any:
    """
    Conecta a un dispositivo MikroTik utilizando sus credenciales.
    Implementa reintentos en caso de fallos temporales.
    """
    try:
        # Desencriptar contraseña
        password = decrypt_credentials(device.encrypted_password)
        
        # Conectar al dispositivo
        api = connect(
            host=device.ip_address,
            port=device.port,
            username=device.mikrotik_user,
            password=password,
            timeout=10
        )
        
        return api
    except Exception as e:
        logger.error(f"Error connecting to device {device.name} ({device.ip_address}): {str(e)}")
        raise

def get_system_info(device: Device) -> Dict[str, Any]:
    """
    Obtiene información del sistema del dispositivo MikroTik.
    """
    try:
        api = connect_to_device(device)
        system_resource = api.path('system', 'resource')
        
        for resource in system_resource:
            return {
                'board_name': resource.get('board-name', 'Unknown'),
                'version': resource.get('version', 'Unknown'),
                'uptime': resource.get('uptime', 'Unknown'),
                'cpu_load': resource.get('cpu-load', 0),
                'free_memory': resource.get('free-memory', 0),
                'total_memory': resource.get('total-memory', 0),
                'free_hdd_space': resource.get('free-hdd-space', 0),
                'total_hdd_space': resource.get('total-hdd-space', 0),
            }
    except Exception as e:
        logger.error(f"Error getting system info from device {device.name}: {str(e)}")
        raise ValueError(f"Error getting system info: {str(e)}")

def get_logs(device: Device, limit: int = 100, topics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Obtiene los logs del dispositivo MikroTik.
    """
    try:
        api = connect_to_device(device)
        log_path = api.path('log')
        
        # Construir parámetros de consulta
        query = {'limit': limit}
        
        # Filtrar por temas si se proporcionan
        if topics:
            query['topics'] = topics
        
        logs = []
        for log in log_path:
            logs.append({
                'time': log.get('time', ''),
                'topics': log.get('topics', ''),
                'message': log.get('message', ''),
            })
        
        return logs
    except Exception as e:
        logger.error(f"Error getting logs from device {device.name}: {str(e)}")
        raise ValueError(f"Error getting logs: {str(e)}")

def get_interfaces(device: Device) -> List[Dict[str, Any]]:
    """
    Obtiene información de las interfaces del dispositivo MikroTik.
    """
    try:
        api = connect_to_device(device)
        interface_path = api.path('interface')
        
        interfaces = []
        for interface in interface_path:
            interfaces.append({
                'name': interface.get('name', 'Unknown'),
                'type': interface.get('type', 'Unknown'),
                'mac_address': interface.get('mac-address', ''),
                'running': interface.get('running', False),
                'disabled': interface.get('disabled', True),
                'comment': interface.get('comment', ''),
            })
        
        return interfaces
    except Exception as e:
        logger.error(f"Error getting interfaces from device {device.name}: {str(e)}")
        raise ValueError(f"Error getting interfaces: {str(e)}")

def analyze_device_health(device: Device, db_session) -> List[Alert]:
    """
    Analiza la salud del dispositivo y genera alertas si es necesario.
    """
    alerts = []
    
    try:
        # Obtener información del sistema
        system_info = get_system_info(device)
        
        # Verificar uso de CPU
        cpu_load = system_info.get('cpu_load', 0)
        if cpu_load > 90:
            alert = Alert(
                title=f"CPU crítico en {device.name}",
                description=f"El uso de CPU ha alcanzado {cpu_load}%",
                state="Alerta Crítica",
                color="#8e44ad",
                recommendation="Revisar procesos en ejecución y considerar reiniciar el dispositivo si persiste",
                device_id=device.id,
                event_date=datetime.utcnow(),
            )
            db_session.add(alert)
            alerts.append(alert)
        elif cpu_load > 75:
            alert = Alert(
                title=f"CPU alto en {device.name}",
                description=f"El uso de CPU ha alcanzado {cpu_load}%",
                state="Alerta Severa",
                color="#e74c3c",
                recommendation="Monitorear el dispositivo y verificar procesos en ejecución",
                device_id=device.id,
                event_date=datetime.utcnow(),
            )
            db_session.add(alert)
            alerts.append(alert)
        
        # Verificar memoria disponible
        free_memory = system_info.get('free_memory', 0)
        total_memory = system_info.get('total_memory', 1)
        memory_percent = 100 - (free_memory / total_memory * 100)
        
        if memory_percent > 90:
            alert = Alert(
                title=f"Memoria crítica en {device.name}",
                description=f"El uso de memoria ha alcanzado {memory_percent:.1f}%",
                state="Alerta Crítica",
                color="#8e44ad",
                recommendation="Revisar procesos en ejecución y considerar reiniciar el dispositivo",
                device_id=device.id,
                event_date=datetime.utcnow(),
            )
            db_session.add(alert)
            alerts.append(alert)
        elif memory_percent > 80:
            alert = Alert(
                title=f"Memoria alta en {device.name}",
                description=f"El uso de memoria ha alcanzado {memory_percent:.1f}%",
                state="Alerta Severa",
                color="#e74c3c",
                recommendation="Monitorear el dispositivo y verificar procesos en ejecución",
                device_id=device.id,
                event_date=datetime.utcnow(),
            )
            db_session.add(alert)
            alerts.append(alert)
        
        # Verificar interfaces
        interfaces = get_interfaces(device)
        for interface in interfaces:
            # Ignorar interfaces deshabilitadas
            if interface.get('disabled', True):
                continue
            
            # Verificar interfaces caídas
            if not interface.get('running', False):
                alert = Alert(
                    title=f"Interfaz caída en {device.name}",
                    description=f"La interfaz {interface.get('name', 'Unknown')} no está funcionando",
                    state="Alerta Severa",
                    color="#e74c3c",
                    recommendation="Verificar conexión física y configuración de la interfaz",
                    device_id=device.id,
                    event_date=datetime.utcnow(),
                )
                db_session.add(alert)
                alerts.append(alert)
        
        # Obtener logs recientes para análisis
        logs = get_logs(device, limit=50)
        
        # Analizar logs en busca de patrones problemáticos
        error_keywords = ['critical', 'error', 'failed', 'failure', 'denied']
        warning_keywords = ['warning', 'timeout', 'retry']
        
        for log in logs:
            message = log.get('message', '').lower()
            
            # Verificar errores críticos
            if any(keyword in message for keyword in error_keywords):
                alert = Alert(
                    title=f"Error detectado en {device.name}",
                    description=f"Log: {log.get('time', '')} - {log.get('message', '')}",
                    state="Alerta Menor",
                    color="#f39c12",
                    recommendation="Revisar los logs completos del dispositivo para más detalles",
                    device_id=device.id,
                    event_date=datetime.utcnow(),
                )
                db_session.add(alert)
                alerts.append(alert)
            
            # Verificar advertencias
            elif any(keyword in message for keyword in warning_keywords):
                alert = Alert(
                    title=f"Advertencia en {device.name}",
                    description=f"Log: {log.get('time', '')} - {log.get('message', '')}",
                    state="Aviso",
                    color="#3498db",
                    recommendation="Monitorear el dispositivo para detectar problemas adicionales",
                    device_id=device.id,
                    event_date=datetime.utcnow(),
                )
                db_session.add(alert)
                alerts.append(alert)
        
        # Actualizar timestamp de última verificación
        device.last_check = datetime.utcnow()
        db_session.add(device)
        
        # Guardar cambios en la base de datos
        db_session.commit()
        
        return alerts
    
    except Exception as e:
        logger.error(f"Error analyzing device health for {device.name}: {str(e)}")
        
        # Crear alerta de error de conexión
        alert = Alert(
            title=f"Error de conexión con {device.name}",
            description=f"No se pudo conectar al dispositivo: {str(e)}",
            state="Alerta Crítica",
            color="#8e44ad",
            recommendation="Verificar conectividad de red y credenciales del dispositivo",
            device_id=device.id,
            event_date=datetime.utcnow(),
        )
        db_session.add(alert)
        db_session.commit()
        
        return [alert]