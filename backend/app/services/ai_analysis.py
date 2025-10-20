import logging
import json
import requests
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.db.models.device import Device
from app.db.models.alert import Alert

logger = logging.getLogger(__name__)

def analyze_logs_with_ai(logs: List[Dict[str, Any]], device_name: str) -> Dict[str, Any]:
    """
    Analiza logs utilizando una API de IA para detectar patrones y problemas.
    """
    try:
        # Preparar datos para la API
        prompt = f"""
        Analiza los siguientes logs del dispositivo MikroTik '{device_name}' y proporciona:
        1. Un resumen de los problemas detectados
        2. Nivel de severidad (Aviso, Alerta Menor, Alerta Severa, Alerta Crítica)
        3. Recomendaciones para resolver los problemas
        
        Logs:
        {json.dumps(logs, indent=2)}
        
        Responde en formato JSON con las siguientes claves:
        - summary: resumen de los problemas
        - severity: nivel de severidad
        - recommendations: lista de recomendaciones
        """
        
        # Llamar a la API de IA
        response = requests.post(
            settings.AI_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.AI_API_KEY}"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Eres un experto en análisis de logs de dispositivos MikroTik. Tu tarea es analizar logs y detectar problemas, asignar severidad y proporcionar recomendaciones."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            },
            timeout=30
        )
        
        # Verificar respuesta
        if response.status_code != 200:
            logger.error(f"Error from AI API: {response.status_code} - {response.text}")
            return {
                "summary": "No se pudo analizar los logs con IA",
                "severity": "Aviso",
                "recommendations": ["Revisar los logs manualmente"]
            }
        
        # Extraer respuesta JSON
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        # Extraer JSON de la respuesta (puede estar dentro de bloques de código)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parsear JSON
        analysis = json.loads(content)
        
        return {
            "summary": analysis.get("summary", "No se pudo analizar los logs"),
            "severity": analysis.get("severity", "Aviso"),
            "recommendations": analysis.get("recommendations", ["Revisar los logs manualmente"])
        }
    
    except Exception as e:
        logger.error(f"Error analyzing logs with AI: {str(e)}")
        return {
            "summary": "Error al analizar logs con IA",
            "severity": "Aviso",
            "recommendations": ["Revisar los logs manualmente"]
        }

def generate_alert_from_ai_analysis(analysis: Dict[str, Any], device: Device) -> Optional[Alert]:
    """
    Genera una alerta basada en el análisis de IA.
    """
    # Mapear severidad a estado
    severity_map = {
        "Aviso": "Aviso",
        "Alerta Menor": "Alerta Menor",
        "Alerta Severa": "Alerta Severa",
        "Alerta Crítica": "Alerta Crítica"
    }
    
    # Mapear severidad a color
    color_map = {
        "Aviso": "#3498db",  # Azul
        "Alerta Menor": "#f39c12",  # Naranja
        "Alerta Severa": "#e74c3c",  # Rojo
        "Alerta Crítica": "#8e44ad",  # Púrpura
    }
    
    # Obtener estado y color
    state = severity_map.get(analysis.get("severity", "Aviso"), "Aviso")
    color = color_map.get(state)
    
    # Crear alerta
    alert = Alert(
        title=f"Análisis IA: {device.name}",
        description=analysis.get("summary", "No se pudo analizar los logs"),
        state=state,
        color=color,
        recommendation=", ".join(analysis.get("recommendations", ["Revisar los logs manualmente"])),
        device_id=device.id
    )
    
    return alert