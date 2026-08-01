"""
Clase base para todos los agentes
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict


class BaseAgent(ABC):
    """Interfaz común para todos los agentes (Ollama, Claude, Gemini)"""
    
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.usage_count = 0
    
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """
        Genera respuesta del agente
        
        Args:
            prompt: Prompt completo
            temperature: Creatividad
            max_tokens: Máximo de tokens
        
        Returns:
            Respuesta del modelo
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el agente está disponible"""
        pass
    
    def get_stats(self) -> Dict:
        """Estadísticas del agente"""
        return {
            "name": self.name,
            "model": self.model,
            "usage_count": self.usage_count
        }