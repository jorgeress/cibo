"""
Cliente HTTP contra la API de Ollama.

Ollama levanta un servidor local en el puerto 11434 y se habla con el por
HTTP normal y corriente, sin SDK de por medio. Solo se usan dos endpoints:

    POST /api/generate  genera texto
    GET  /api/tags      lista los modelos instalados

Hay dos formas de generar. Sin streaming espera a que termine y devuelve el
texto entero, que es lo comodo para llamar desde codigo. Con streaming el
servidor va mandando un JSON por linea segun genera, y se van soltando los
tokens segun llegan, que es lo que hace falta para que en pantalla aparezca
escribiendose en vez de salir de golpe tras diez segundos en blanco.

El historial se guarda aqui, en memoria y mientras dure el proceso. Ollama
no recuerda nada entre peticiones: cada llamada va sola, y si quieres que el
modelo tenga contexto se lo tienes que meter tu en el prompt.
"""

import requests
import json
import os
from typing import Optional, Dict, List, Generator
from dotenv import load_dotenv

load_dotenv()

class OllamaClient:
    """Cliente para interactuar con Ollama"""

    def __init__(self, 
                 model: Optional[str] = None,
                 base_url: Optional[str] = None):
        
        self.model = model or os.getenv("MODEL_NAME", "cibo:latest")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.conversation_history: List[Dict] = []
    
    def chat(self,
             prompt: str,
             system: Optional[str] = None,
             temperature: float = 0.7) -> str:
        """
        Genera una respuesta completa y la devuelve.

        Bloquea hasta que el modelo termina. El timeout es de 3 minutos
        porque en CPU, o con el contexto lleno, un 8B puede tardar bastante.

        Los errores se devuelven como texto en vez de lanzar excepcion, para
        que un fallo de red no tumbe la conversacion entera.
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            
            result = response.json()["response"]
            
            # Guarda en historial
            self._add_to_history("user", prompt)
            self._add_to_history("assistant", result)
            
            return result
                
        except requests.exceptions.Timeout:
            return "Error: Timeout"
        except requests.exceptions.RequestException as e:
            return f"Error: {e}"
    
    def chat_stream(self, prompt: str, system: Optional[str] = None) -> Generator[str, None, None]:
        """
        Igual que chat() pero soltando los tokens segun llegan.

        Con stream=True, Ollama responde con un JSON por linea. Cada uno trae
        un trozo de texto en "response", y el ultimo trae "done": true.

        El decode_unicode=True de iter_lines es importante: sin el, los
        acentos y las ñ llegan partidos entre dos trozos y se ven mal.

        Yields:
            Cada token segun lo genera el modelo
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.7}
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=180)
            response.raise_for_status()
            
            full_response = ""
            
            # iter_lines con decode_unicode para evitar problemas de encoding
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        
                        # Ollama envía done=true cuando termina
                        if data.get("done", False):
                            break
                        
                        # Cada "response" es un token
                        token = data.get("response", "")
                        if token:
                            full_response += token
                            yield token
                    
                    except json.JSONDecodeError:
                        continue
            
            # Guarda en historial cuando termina
            if full_response:
                self._add_to_history("assistant", full_response)
        
        except Exception as e:
            yield f"\nError: {e}"
    
    def chat_with_context(self, prompt: str, max_history: int = 10) -> str:
        """
        Como chat(), pero arrastrando la conversacion anterior.

        Como Ollama no guarda estado, el "contexto" es literalmente pegar los
        mensajes previos delante del prompt, con su etiqueta de quien habla.

        Args:
            max_history: cuantos intercambios recuperar. Se multiplica por 2
                         porque cada intercambio son dos mensajes, el del
                         usuario y el del asistente
        """
        context_messages = self.conversation_history[-(max_history*2):]
        
        context = ""
        for msg in context_messages:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            context += f"{role}: {msg['content']}\n\n"
        
        full_prompt = f"{context}Usuario: {prompt}\n\nAsistente:"
        
        return self.chat(full_prompt)
    
    def chat_with_context_stream(self, prompt: str, max_history: int = 10) -> Generator[str, None, None]:
        """
        Contexto y streaming a la vez, que es lo que quiere una interfaz.

        Aqui la pregunta se mete en el historial antes de mandar nada, porque
        chat_stream solo apunta la respuesta del asistente. Si se hiciera
        despues, el turno del usuario se perderia.
        """
        self._add_to_history("user", prompt)
        
        # Construye contexto
        context_messages = self.conversation_history[-(max_history*2+1):]  # +1 para incluir pregunta actual
        
        context = ""
        for msg in context_messages:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            context += f"{role}: {msg['content']}\n\n"
        
        # No añadas el prompt de nuevo, ya está en el contexto
        full_prompt = context + "Asistente:"
        
        # Usa chat_stream
        for token in self.chat_stream(full_prompt):
            yield token
    
    def _add_to_history(self, role: str, content: str):
        """Añade mensaje al historial"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def clear_history(self):
        """Limpia historial"""
        self.conversation_history = []
        print("✓ Historial limpiado")
    
    def get_history(self) -> List[Dict]:
        """Retorna historial completo"""
        return self.conversation_history
    
    def export_history(self, filepath: str):
        """
        Vuelca la conversacion a un JSON.

        Con ensure_ascii=False para que los acentos se guarden como acentos y
        no como secuencias \\uXXXX ilegibles.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_history, f, indent=2, ensure_ascii=False)
        print(f"Guardado en {filepath}")

    def get_models(self) -> List[str]:
        """Nombres de los modelos que hay instalados en Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
            return []
        except:
            return []
    
    def is_running(self) -> bool:
        """
        Esta el servidor de Ollama levantado?

        Se pregunta antes de arrancar, porque el fallo mas comun con
        diferencia es olvidarse de lanzar `ollama serve`. Timeout corto: si
        no contesta en 2 segundos es que no esta.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_model_info(self) -> Optional[Dict]:
        """Info detallada del modelo"""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None


# === TESTS ===
if __name__ == "__main__":
    print("="*60)
    print("TEST: Streaming Token por Token")
    print("="*60)
    
    client = OllamaClient()
    
    if not client.is_running():
        print("Ollama no está corriendo")
        exit(1)
    
    print(f"Modelo: {client.model}\n")
    
    # Test streaming
    print("CIBO: ", end="", flush=True)
    
    for token in client.chat_stream("Di 'Hola' y explica qué es Python en una línea"):
        print(token, end="", flush=True)
    
    print("\n\nTest completado")