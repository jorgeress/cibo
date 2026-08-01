"""
Configuración de niveles de privacidad
"""

from typing import Dict, List


class PrivacyMode:
    """Configuración de privacidad del usuario"""
    
    MODES = {
        "paranoid": {
            "agents": ["ollama_local"],
            "tools": ["calculator", "code_executor"],
            "internet": False,
            "memory_cloud": False,
            "logs": "encrypted_local",
            "description": "100% local, máxima privacidad"
        },
        
        "balanced": {
            "agents": ["ollama_local", "claude_api"],
            "tools": ["calculator", "code_executor", "web_search"],
            "internet": True,
            "memory_cloud": False,
            "logs": "local",
            "data_sanitization": True,
            "description": "Híbrido seguro, datos sensibles locales"
        },
        
        "performance": {
            "agents": ["ollama_local", "claude_api", "gemini_api"],
            "tools": ["all"],
            "internet": True,
            "memory_cloud": True,
            "logs": "cloud_allowed",
            "description": "Máximo rendimiento, menos restricciones"
        }
    }
    
    def __init__(self, mode: str = "balanced"):
        """
        Args:
            mode: 'paranoid', 'balanced', o 'performance'
        """
        if mode not in self.MODES:
            raise ValueError(f"Modo debe ser: {', '.join(self.MODES.keys())}")
        
        self.mode = mode
        self.config = self.MODES[mode]
    
    def allows_agent(self, agent_name: str) -> bool:
        """Verifica si un agente está permitido"""
        return agent_name in self.config["agents"] or "all" in self.config.get("agents", [])
    
    def allows_tool(self, tool_name: str) -> bool:
        """Verifica si una herramienta está permitida"""
        return tool_name in self.config["tools"] or "all" in self.config.get("tools", [])
    
    def allows_internet(self) -> bool:
        """Verifica si permite acceso a internet"""
        return self.config.get("internet", False)
    
    def get_description(self) -> str:
        """Descripción del modo actual"""
        return self.config.get("description", "")