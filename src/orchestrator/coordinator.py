"""
El coordinador: junta router, memoria y herramientas en un solo sitio.

Es la version "de arriba" de lo que hace core/agent.py. La diferencia es que
Agent habla siempre con Ollama y decide entre sus dos herramientas, mientras
que Coordinator no sabe con que modelo va a acabar hablando: se lo pregunta
al router en cada turno.

Cada llamada a process() sigue el mismo camino: mira la memoria, elige
agente, monta el prompt con lo que haya recordado y genera.

AVISO: esto funciona pero main.py todavia no lo usa. La consola instancia
Agent directamente, asi que al multi-agente solo se llega importandolo desde
codigo. Era el siguiente paso cuando el proyecto se paro.
"""

from typing import List, Dict, Any
from ..agents.base_agent import BaseAgent
from ..storage.vector_store import VectorMemory
from .router import AgentRouter


class Coordinator:
    """Orquestador principal de CIBO"""
    
    def __init__(self, agents: List[BaseAgent], tools: Dict[str, Any], use_memory: bool = True, privacy_mode: str = "balanced"):
        """
        Args:
            agents: Lista de agentes disponibles
            tools: Diccionario de herramientas {nombre: herramienta}
            use_memory: Si usar memoria persistente
            privacy_mode: Nivel de privacidad
        """
        self.router = AgentRouter(agents)
        self.tools = tools
        self.privacy_mode = privacy_mode
        
        # Memoria
        self.memory = VectorMemory() if use_memory else None
    
    def process(self, query: str) -> str:
        """
        Procesa una pregunta de principio a fin.

        Ojo: el diccionario de herramientas se guarda y se lista en las
        estadisticas, pero aqui nadie las ejecuta. Quien decide usarlas es el
        modelo, y esa parte esta en core/agent.py. Otra costura a medio coser.
        """
        
        # 1. Recupera contexto de memoria
        context = ""
        if self.memory:
            memories = self.memory.recall(query, n_results=2)
            if memories:
                context = "INFORMACIÓN RECORDADA:\n"
                for mem in memories:
                    context += f"- {mem['text']}\n"
                context += "\n"
        
        # 2. Decide qué agente usar
        agent = self.router.route(query, self.privacy_mode)
        
        print(f"🤖 Usando: {agent.name}")
        
        # 3. Construye prompt completo
        full_prompt = f"{context}Usuario: {query}\n\nAsistente:"
        
        # 4. Genera respuesta
        response = agent.generate(full_prompt)
        
        return response
    
    def get_stats(self) -> Dict:
        """Estadísticas del sistema"""
        stats = {
            "privacy_mode": self.privacy_mode,
            "agents": {name: agent.get_stats() for name, agent in self.router.agents.items()},
            "tools": list(self.tools.keys())
        }
        
        if self.memory:
            stats["memory"] = self.memory.get_stats()
        
        return stats