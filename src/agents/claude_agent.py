"""
Agente que usa Claude API (Anthropic)
"""

from .base_agent import BaseAgent
from typing import Optional
import os


class ClaudeAgent(BaseAgent):
    """Agente cloud con Claude API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(name="Claude API", model=model)
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("Se requiere ANTHROPIC_API_KEY")
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Instala: pip install anthropic")
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Genera respuesta con Claude"""
        self.usage_count += 1
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
        
        except Exception as e:
            return f"Error Claude API: {e}"
    
    def is_available(self) -> bool:
        """Verifica si la API key es válida"""
        return self.api_key is not None