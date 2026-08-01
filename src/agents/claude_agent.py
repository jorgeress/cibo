"""
Agente de pago, contra la API de Claude.

Opcional. Hace falta la libreria `anthropic` y una clave en ANTHROPIC_API_KEY,
y si falta cualquiera de las dos el constructor revienta a proposito, para
enterarte al arrancar y no a mitad de una conversacion. El __init__.py del
paquete lo importa dentro de un try, asi que sin clave el resto sigue
funcionando igual.

Lo que se manda aqui sale del equipo. Antes de llegar a este punto deberia
haber pasado por SecurityLayer, y el router solo lo elige si el modo de
privacidad lo permite.

OJO CON EL MODELO POR DEFECTO: se escribio en febrero de 2026 apuntando a
claude-3-5-sonnet-20241022, que Anthropic retiro en octubre de 2025. Ese ID
ya devuelve 404, asi que hay que pasarle un modelo actual al construirlo.
En agosto de 2026 los vigentes son claude-opus-5, claude-sonnet-5 y
claude-haiku-4-5. Buen ejemplo de por que el proyecto esta en pausa: se
queda obsoleto sin que toques una linea.
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