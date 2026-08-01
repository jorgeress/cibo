"""
Router - Decide qué agente usar según el query
"""

from typing import List, Optional
from ..agents.base_agent import BaseAgent
import re


class AgentRouter:
    """Decide qué agente usar según criterios"""
    
    def __init__(self, agents: List[BaseAgent], default_agent: str = "ollama"):
        """
        Args:
            agents: Lista de agentes disponibles
            default_agent: Nombre del agente por defecto
        """
        self.agents = {agent.name.lower().replace(" ", "_"): agent for agent in agents}
        self.default_agent = default_agent
    
    def route(self, query: str, privacy_mode: str = "balanced") -> BaseAgent:
        """
        Decide qué agente usar
        
        Args:
            query: Pregunta del usuario
            privacy_mode: "paranoid", "balanced", "performance"
        
        Returns:
            Agente seleccionado
        """
        
        # MODO PARANOID: Solo local
        if privacy_mode == "paranoid":
            return self._get_agent("ollama_local")
        
        # Detecta si tiene datos sensibles
        if self._is_sensitive(query):
            return self._get_agent("ollama_local")
        
        # Detecta si es tarea simple
        if self._is_simple_task(query):
            return self._get_agent("ollama_local")
        
        # MODO PERFORMANCE: Prioriza Claude para razonamiento complejo
        if privacy_mode == "performance":
            if self._needs_advanced_reasoning(query):
                claude = self._get_agent("claude_api")
                if claude and claude.is_available():
                    return claude
        
        # MODO BALANCED o fallback
        return self._get_agent("ollama_local")
    
    def _is_sensitive(self, text: str) -> bool:
        """Detecta datos sensibles"""
        sensitive_patterns = [
            r'\b\d{16}\b',  # Tarjetas
            r'password', r'contraseña',
            r'api[_-]?key', r'token',
            r'\b\d{3}-\d{2}-\d{4}\b'  # SSN
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_simple_task(self, text: str) -> bool:
        """Detecta si es tarea simple"""
        simple_keywords = ['hola', 'que es', 'explica', 'define']
        return any(keyword in text.lower() for keyword in simple_keywords)
    
    def _needs_advanced_reasoning(self, text: str) -> bool:
        """Detecta si necesita razonamiento avanzado"""
        complex_keywords = ['analiza', 'compara', 'evalua', 'critica', 'argumento']
        return any(keyword in text.lower() for keyword in complex_keywords)
    
    def _get_agent(self, name: str) -> Optional[BaseAgent]:
        """Obtiene agente por nombre"""
        agent = self.agents.get(name)
        
        if agent and agent.is_available():
            return agent
        
        # Fallback al default
        return self.agents.get(self.default_agent)