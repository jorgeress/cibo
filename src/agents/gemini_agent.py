"""
Agente que usa Gemini API (Google)
"""

from .base_agent import BaseAgent
from typing import Optional
import os


class GeminiAgent(BaseAgent):
    """Agente cloud con Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        super().__init__(name="Gemini API", model=model)
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("Se requiere GOOGLE_API_KEY")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(model)
        except ImportError:
            raise ImportError("Instala: pip install google-generativeai")
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Genera respuesta con Gemini"""
        self.usage_count += 1
        
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )
            
            return response.text
        
        except Exception as e:
            return f"Error Gemini API: {e}"
    
    def is_available(self) -> bool:
        """Verifica si la API key es válida"""
        return self.api_key is not None