"""
Interfaz comun para cualquier modelo, local o de pago.

La gracia de esto es que Ollama, Claude y Gemini se usan de forma muy
distinta (uno es HTTP a pelo, los otros dos traen su propio SDK), pero desde
fuera se comportan igual: le pides generate() y te devuelve texto. Asi el
router puede cambiar de uno a otro sin que el resto del codigo lo note.

Los dos metodos que hay que implementar:

    generate()      genera texto y devuelve string, pase lo que pase
    is_available()  dice si se puede usar ahora mismo

is_available() existe porque la disponibilidad cambia sobre la marcha: el
servidor de Ollama puede estar apagado, o puede no haber API key. Se
pregunta antes de mandar nada, en vez de descubrirlo con una excepcion.

Detalle a tener en cuenta: el router busca los agentes por el .name pasado a
minusculas y con los espacios en guion bajo, o sea "Ollama Local" se
convierte en "ollama_local". Si añades un agente nuevo, el nombre importa.
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
        Genera una respuesta.

        Args:
            prompt: el prompt entero, ya montado. Aqui no se le añade nada
            temperature: 0 va a lo seguro, 1 se suelta
            max_tokens: tope de longitud de la respuesta

        Returns:
            El texto del modelo. Si algo falla, el mensaje de error como
            string. Nunca lanza excepcion, para que quien llama no tenga que
            envolverlo en try/except
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Se puede usar este agente ahora mismo?"""
        pass
    
    def get_stats(self) -> Dict:
        """Estadísticas del agente"""
        return {
            "name": self.name,
            "model": self.model,
            "usage_count": self.usage_count
        }