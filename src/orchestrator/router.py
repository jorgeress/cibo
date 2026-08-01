"""
El router: elige a que modelo mandar cada pregunta.

Aqui la privacidad va por delante de la potencia. El orden de las
comprobaciones no es casual, cada una puede cortar antes de llegar a la
siguiente:

    1. Modo paranoid          -> local, sin discusion
    2. Datos sensibles        -> local, aunque el modo permita cloud
    3. Pregunta simple        -> local, no gastamos API en un "hola"
    4. Modo performance
       y razonamiento duro    -> Claude, si esta disponible
    5. Todo lo demas          -> local

Las comprobaciones 2 y 3 son las que importan: aunque tengas activado el
modo mas permisivo, una contraseña o un numero de tarjeta no salen de aqui.
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
        # Las claves salen del .name de cada agente, en minusculas y con los
        # espacios en guion bajo: "Ollama Local" -> "ollama_local". Si añades
        # un agente nuevo, revisa que el nombre cuadre con lo que busca route()
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
        """
        Hay algo en la pregunta que no deberia salir del equipo?

        Es deteccion por patrones, o sea que se le escapan cosas: no reconoce
        una contraseña que no se llame contraseña. Por eso esto no sustituye a
        SecurityLayer, que vuelve a comprobar justo antes de enviar.
        """
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
        """
        Esto lo resuelve el modelo local sin despeinarse?

        Saludos y definiciones no justifican pagar una llamada a la nube.
        """
        simple_keywords = ['hola', 'que es', 'explica', 'define']
        return any(keyword in text.lower() for keyword in simple_keywords)

    def _needs_advanced_reasoning(self, text: str) -> bool:
        """
        Merece la pena el modelo grande?

        Verbos de analisis, comparacion y critica, que es donde mas se nota
        la diferencia entre un 8B local y un modelo de pago.
        """
        complex_keywords = ['analiza', 'compara', 'evalua', 'critica', 'argumento']
        return any(keyword in text.lower() for keyword in complex_keywords)

    def _get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Devuelve un agente por nombre, o el de reserva si no puede.

        Comprueba is_available() antes de devolverlo, asi que si Ollama esta
        apagado o falta una API key, la peticion no se pierde: cae al agente
        por defecto en vez de reventar.
        """
        agent = self.agents.get(name)

        if agent and agent.is_available():
            return agent

        return self.agents.get(self.default_agent)