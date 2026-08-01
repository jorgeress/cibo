"""
Sistema base de herramientas
Todas las herramientas heredan de Tool
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
        Wrapper que añade logging y manejo de errores
        """
        self.usage_count += 1
        
        try:
            result = self.execute(**kwargs)
            
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