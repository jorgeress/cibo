"""
Sanitización de datos antes de enviar a cloud
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
        Limpia datos sensibles antes de enviar a cloud
        
        Returns:
            (es_seguro, texto_limpio_o_error)
        """
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "⚠️ Datos sensibles detectados. No enviado a cloud."
        
        return True, text
    
    def redact_response(self, response: str) -> str:
        """Elimina info sensible de respuestas cloud"""
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