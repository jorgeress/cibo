"""
Ultima parada antes de que algo salga a internet.

Funciona en las dos direcciones. A la ida, si encuentra un patron sensible
bloquea el envio entero en vez de tachar la parte fea: prefiere no mandar
nada a mandar algo a medio limpiar. A la vuelta, tacha IPs y emails de lo
que conteste el modelo.

Esto es la segunda barrera, no la unica. El router ya hace una comprobacion
parecida antes de elegir agente; aqui se repite porque quien llame al codigo
puede saltarse el router.

Y lo de siempre con las expresiones regulares: pilla lo que reconoce. Una
clave que no se parezca a una clave pasa sin enterarse.
"""

import re
from typing import Tuple


class SecurityLayer:
    """Capa de seguridad antes de enviar a APIs cloud"""
    
    FORBIDDEN_PATTERNS = [
        r'api[_-]?key',
        r'password',
        r'token',
        r'secret',
        r'\b\d{16}\b',  # Tarjetas de crédito
        r'ssh[_-]?key',
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    ]
    
    def sanitize_before_cloud(self, text: str) -> Tuple[bool, str]:
        """
        Se puede mandar esto fuera?

        Returns:
            (True, texto) si esta limpio, o (False, aviso) si no. Cuando
            devuelve False el segundo valor es el mensaje para el usuario,
            no el texto tachado: aqui no se envia nada.
        """
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "⚠️ Datos sensibles detectados. No enviado a cloud."
        
        return True, text
    
    def redact_response(self, response: str) -> str:
        """
        Tacha IPs y emails de lo que devuelve la nube.

        Aqui si se tacha en vez de bloquear, porque la respuesta ya la tienes
        y lo que interesa es no dejarla escrita tal cual en el historial.
        """
        # Redacta IPs
        response = re.sub(
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            '[IP_REDACTED]',
            response
        )
        
        # Redacta emails
        response = re.sub(
            r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            '[EMAIL_REDACTED]',
            response
        )
        
        return response