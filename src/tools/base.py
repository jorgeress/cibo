"""
La base de la que heredan todas las herramientas.

El reparto es este: cada herramienta implementa execute() y se despreocupa
de los errores, y run() se encarga de envolverla. Asi ninguna herramienta
puede tumbar al agente por una excepcion suelta, porque run() la captura y
la convierte en un diccionario de error normal.

El contrato de vuelta es siempre el mismo:

    {"success": bool, "result": Any, "error": str | None}

Quien llama mira 'success' y ya sabe que hacer, sin try/except por medio.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Tool(ABC):
    """Clase base para todas las herramientas"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.description = self.get_description()
        self.usage_count = 0
    
    @abstractmethod
    def get_description(self) -> str:
        """Descripción de qué hace la herramienta"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta la herramienta
        
        Returns:
            Dict con 'success' (bool), 'result' (Any), 'error' (Optional[str])
        """
        pass
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Llama a execute() con red de seguridad. Usa esto, no execute().

        Hace tres cosas: lleva la cuenta de usos, normaliza la respuesta si la
        herramienta devolvio un valor pelado en vez de un diccionario, y
        atrapa cualquier excepcion para devolverla como error.
        """
        self.usage_count += 1

        try:
            result = self.execute(**kwargs)

            # Por comodidad, execute() puede devolver el valor a secas
            if not isinstance(result, dict):
                result = {"success": True, "result": result}

            return result

        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa info de la herramienta"""
        return {
            "name": self.name,
            "description": self.description,
            "usage_count": self.usage_count
        }
    
    def __str__(self) -> str:
        return f"{self.name}: {self.description}"