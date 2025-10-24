from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from librouteros import connect
from librouteros.exceptions import ConnectionError, LoginError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.core.security import vault
from app.db.models.device import Device

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_fixed(2),
    retry=retry_if_exception_type((ConnectionError, LoginError))
)
def connect_to_device(device: Device) -> Any:
    """
    Conecta a un dispositivo MikroTik usando librouteros.
    Implementa reintentos en caso de fallos temporales.
    """
    try:
        # Desencriptar credenciales
        username = vault.decrypt(device.usuario_mk_enc)
        password = vault.decrypt(device.password_mk_enc)

        api = connect(
            username=username,
            password=password,
            host=device.ip,
            port=device.puerto,
            timeout=10
        )
        
        logger.info(f"Connected to MikroTik device {device.nombre} ({device.ip})")
        return api
        
    except Exception as e:
        logger.error(f"Error connecting to device {device.nombre} ({device.ip}): {str(e)}")
        raise

def get_health(device: Device) -> Dict[str, Any]:
    """
    Obtiene métricas de salud del sistema: CPU, memoria, uptime.
    """
    try:
        api = connect_to_device(device)
        
        # Obtener recursos del sistema 
        resources = tuple(api.path('system/resource'))[0]
        
        # Normalizar valores
        return {
            'cpu_load': int(resources.get('cpu-load', 0)),
            'memory_total': int(resources.get('total-memory', 0)),
            'memory_free': int(resources.get('free-memory', 0)), 
            'memory_used': int(resources.get('total-memory', 0)) - int(resources.get('free-memory', 0)),
            'uptime': resources.get('uptime', ''),
            'version': resources.get('version', ''),
            'board_name': resources.get('board-name', ''),
            'checked_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting health for device {device.nombre}: {str(e)}")
        raise ValueError(f"Error getting device health: {str(e)}")
    finally:
        if 'api' in locals():
            api.close()

def get_logs(device: Device, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Obtiene los últimos logs del dispositivo.
    """
    try:
        api = connect_to_device(device)

        # Obtener logs con límite
        logs = tuple(api.path('log'))[:limit]

        # Normalizar cada entrada de log
        normalized_logs = []
        for log in logs:
            normalized_logs.append({
                'time': log.get('time', ''),
                'topics': log.get('topics', []),
                'message': log.get('message', ''),
                'facility': log.get('facility', ''),
                'severity': log.get('severity', ''),
            })

        return normalized_logs

    except Exception as e:
        logger.error(f"Error getting logs from device {device.nombre}: {str(e)}")
        raise ValueError(f"Error getting logs: {str(e)}")
    finally:
        if 'api' in locals():
            api.close()

def test_mikrotik_connection(ip: str, port: int, username: str, password: str) -> bool:
    """
    Prueba credenciales y conexión.
    Returns True si la conexión es exitosa.
    """
    try:
        api = connect(
            username=username,
            password=password,
            host=ip,
            port=port,
            timeout=5
        )
        # Verificar que podemos hacer una operación básica
        tuple(api.path('system/resource'))
        api.close()
        return True
        
    except Exception as e:
        logger.warning(f"Connection test failed for {ip}: {str(e)}")
        raise ValueError(f"Connection test failed: {str(e)}")