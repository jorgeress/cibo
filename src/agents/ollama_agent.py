"""
Agente que usa Ollama (local)
"""

from .base_agent import BaseAgent
from typing import Optional
import requests


class OllamaAgent(BaseAgent):
    """Agente local con Ollama"""
    
    def __init__(self, model: str = "qwen2.5:32b-instruct-q4_K_M", base_url: str = "http://localhost:11434"):
        super().__init__(name="Ollama Local", model=model)
        self.base_url = base_url
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Genera respuesta con Ollama"""
        self.usage_count += 1
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error HTTP {response.status_code}"
        
        except Exception as e:
            return f"Error: {e}"
    
    def is_available(self) -> bool:
        """Verifica si Ollama está corriendo"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False