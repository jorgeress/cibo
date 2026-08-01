"""
El agente: decide si una pregunta se resuelve con una herramienta o
hablando con el modelo.

La idea de fondo es que un modelo de 8B no es de fiar para segun que cosas.
Le pides una multiplicacion de seis cifras y se inventa el resultado con
total seguridad. Asi que antes de pasarle nada al modelo, aqui se mira si
la pregunta cae en un caso que sabemos resolver de forma exacta.

El orden de process() va de lo barato a lo caro:

    1. Es matematicas?  -> Calculator, sin tocar el modelo
    2. Piden ejecutar codigo? -> CodeExecutor, sin tocar el modelo
    3. Ni idea -> se lo preguntamos al modelo, que puede pedir herramienta
    4. Pidio herramienta? -> se ejecuta
    5. Si no, su respuesta tal cual

Los pasos 1 y 2 son deteccion por palabras clave y expresiones regulares.
Es tosco y se le escapan casos, pero es instantaneo y no falla, mientras
que dejarselo decidir al modelo sale caro en tiempo y acierta a medias.
"""

from typing import List, Dict, Any
from .ollama_client import OllamaClient

import re
import json


class Agent:
    """Orquesta el modelo y las herramientas"""

    def __init__(self, client: OllamaClient, tools: List[Any], use_memory: bool = False):
        """
        Args:
            client: cliente de Ollama ya configurado
            tools: lista de herramientas. Se indexan por su atributo .name,
                   que es el nombre de la clase (Calculator, CodeExecutor)
            use_memory: si activarla memoria vectorial persistente. Va
                        desactivada porque arrastra chromadb y sentence-transformers,
                        que son varios cientos de MB
        """
        self.client = client
        self.tools = {tool.name: tool for tool in tools}
        self.system_prompt = self._build_system_prompt()

        # Memoria vectorial (opcional: requiere chromadb instalado)
        self.memory = self._init_memory() if use_memory else None

    def _init_memory(self):
        """
        Carga VectorMemory solo cuando hace falta.

        Se importa aqui dentro y no arriba a proposito: asi quien no use
        memoria no necesita tener chromadb instalado. Si algo falla, avisa
        y devuelve None, porque quedarse sin memoria no es motivo para no
        arrancar.
        """
        try:
            from ..storage.vector_store import VectorMemory
        except ImportError:
            # main.py añade src/ al path, asi que 'storage' es top-level
            try:
                from storage.vector_store import VectorMemory
            except ImportError as e:
                print(f"Memoria desactivada (falta dependencia): {e}")
                return None

        try:
            return VectorMemory()
        except Exception as e:
            print(f"Memoria desactivada (error al inicializar): {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """Construye prompt optimizado"""
        return """Eres CIBO, un asistente inteligente con acceso a herramientas especializadas.

IMPORTANTE: Puedes responder preguntas normales SIN usar herramientas. Solo usalas cuando sea necesario.

HERRAMIENTAS DISPONIBLES:
1. Calculator - Para operaciones matematicas precisas
2. CodeExecutor - Para ejecutar codigo Python que el usuario proporcione

CUANDO USAR HERRAMIENTAS:

Calculator:
- Usuario pregunta "cuanto es", "calcula", "suma", "multiplica", etc.
- Hay numeros y operaciones matematicas
- CRITICO: Eres malo en matematicas, SIEMPRE usa Calculator para calculos

CodeExecutor:
- Usuario dice explicitamente "ejecuta", "corre", "run" seguido de codigo
- Usuario muestra codigo Python y pide ejecutarlo

CUANDO NO USAR HERRAMIENTAS:
- Preguntas conceptuales: "Que es Python?", "Explica X"
- Conversacion general: "Hola", "Como estas?"
- Definiciones, explicaciones, tutoriales
- Cualquier cosa que puedas responder con tu conocimiento

FORMATO para herramientas:
<tool>NombreHerramienta</tool>
<params>{"param": "valor"}</params>

EJEMPLOS:

Usuario: Cuanto es 8347 * 9562?
Tu: <tool>Calculator</tool><params>{"expression": "8347 * 9562"}</params>

Usuario: Ejecuta: print('Hola')
Tu: <tool>CodeExecutor</tool><params>{"code": "print('Hola')"}</params>

Usuario: Que es Python?
Tu: Python es un lenguaje de programacion interpretado, de alto nivel y proposito general. Fue creado por Guido van Rossum y se caracteriza por su sintaxis clara y legible...

Usuario: Hola
Tu: ¡Hola! ¿En que puedo ayudarte hoy?"""
    
    def _detect_math_query(self, text: str) -> bool:
        """
        Es una pregunta de matematicas?

        Dos vias: que aparezca un verbo de calculo, o que se vea un patron
        numero-operador-numero. Con la primera pillamos "multiplica 8 por 9"
        y con la segunda "8 * 9" a secas.

        Da falsos positivos ("cuanto tarda un tren en llegar"), pero eso lo
        absorbe _extract_math_expression: si no encuentra expresion devuelve
        None y process() sigue por el camino normal.
        """
        math_keywords = [
            'cuanto', 'calcula', 'suma', 'resta', 'multiplica', 'divide',
            'raiz', 'potencia', 'resultado', 'operacion'
        ]
        
        if any(keyword in text.lower() for keyword in math_keywords):
            return True
        
        if re.search(r'\d+\s*[+\-*/^]\s*\d+', text):
            return True
        
        return False
    
    def _extract_math_expression(self, text: str) -> str:
        """
        Saca la operacion de la frase y la deja lista para Calculator.

        Ejemplos:
        - "Calcula (25 * 4) + (100 / 2) - 10" -> "(25 * 4) + (100 / 2) - 10"
        - "Multiplica 999999 por 888888" -> "999999 * 888888"
        - "Cuanto es 5 mas 3?" -> "5 + 3"

        Va probando patrones de mas a menos especifico. Primero busca una
        expresion ya escrita en simbolos, y si no la hay traduce las formas
        habituales en castellano ("multiplica X por Y", "divide X entre Y").

        Devuelve None si no encuentra nada aprovechable, y entonces la
        pregunta sigue su curso hacia el modelo.
        """
        # Patron 1: Expresion matematica con operadores y parentesis
        # Incluye espacios, numeros, operadores, parentesis
        math_expr = re.search(
            r'([\d\s+\-*/().^]+)',
            text
        )
        if math_expr:
            expr = math_expr.group(1).strip()
            # Valida que tenga al menos un operador
            if any(op in expr for op in ['+', '-', '*', '/', '^', '(']):
                return expr
        
        # Patron 2: Texto descriptivo ("multiplica X por Y")
        multiply_match = re.search(r'multiplica?\s+(\d+)\s+por\s+(\d+)', text, re.IGNORECASE)
        if multiply_match:
            return f"{multiply_match.group(1)} * {multiply_match.group(2)}"
        
        # "suma X y Y" -> "X + Y"
        add_match = re.search(r'suma?\s+(\d+)\s+y\s+(\d+)', text, re.IGNORECASE)
        if add_match:
            return f"{add_match.group(1)} + {add_match.group(2)}"
        
        # "X mas Y" -> "X + Y"
        mas_match = re.search(r'(\d+)\s+m[aá]s\s+(\d+)', text, re.IGNORECASE)
        if mas_match:
            return f"{mas_match.group(1)} + {mas_match.group(2)}"
        
        # "divide X entre Y" -> "X / Y"
        div_match = re.search(r'divid[ei]?\s+(\d+)\s+entre\s+(\d+)', text, re.IGNORECASE)
        if div_match:
            return f"{div_match.group(1)} / {div_match.group(2)}"
        
        # Patron 3: Solo numeros y operadores simples
        simple = re.search(r'(\d+\s*[+\-*/]\s*\d+)', text)
        if simple:
            return simple.group(1)
        
        return None
    
    def _detect_code_query(self, text: str) -> bool:
        """
        Estan pidiendo ejecutar codigo, o solo hablando de codigo?

        La distincion importa: "ejecuta print('hola')" hay que correrlo, pero
        "me gusta Python" no. Por eso no basta con ver si aparece codigo en la
        frase, tiene que haber un verbo de ejecucion.
        """
        execute_keywords = ['ejecuta', 'corre', 'run', 'ejecutar', 'correr']

        if any(keyword in text.lower() for keyword in execute_keywords):
            return True

        # Verbos de opinion: hablan de codigo pero no piden nada
        mention_keywords = ['me gusta', 'uso', 'utilizo', 'prefiero', 'suelo']
        if any(keyword in text.lower() for keyword in mention_keywords):
            return False

        return False
    
    def _extract_code(self, text: str) -> str:
        """
        Separa el codigo de la frase que lo envuelve.

        Ejemplos:
        - "Ejecuta: print('Hola')" -> "print('Hola')"
        - 'Ejecuta este codigo: print("Test")' -> 'print("Test")'
        - "Corre print(5)" -> "print(5)"

        Lo normal es que venga detras de dos puntos, asi que ese es el primer
        intento. Si no, busca construcciones de Python reconocibles, y como
        ultimo recurso corta por el verbo de ejecucion.
        """
        # Patron 1: Despues de ":" hasta el final
        match = re.search(r':\s*(.+)$', text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            # Elimina comillas externas si las tiene
            if (code.startswith('"') and code.endswith('"')) or \
               (code.startswith("'") and code.endswith("'")):
                code = code[1:-1]
            return code
        
        # Patron 2: Si contiene print(), for, def, etc., toma desde ahi
        code_match = re.search(r'(print\(.*?\)|for .+?:|def .+?:|.+ = .+)', text)
        if code_match:
            return code_match.group(1)
        
        # Patron 3: Toma todo despues de palabra clave
        for keyword in ['ejecuta', 'corre', 'run']:
            if keyword in text.lower():
                parts = text.lower().split(keyword)
                if len(parts) > 1:
                    return parts[1].strip()
        
        return text
    
    def save_to_memory(self, text: str, category: str = "general"):
        """
        Guarda algo en la memoria persistente.

        Hay que llamarla a mano. El agente lee de la memoria en cada turno
        pero no escribe solo, porque decidir que merece recordarse es un
        problema aparte que no llegue a resolver.
        """
        if self.memory:
            return self.memory.remember(text, category=category)
        return None

    def process(self, user_input: str) -> str:
        """
        Punto de entrada: recibe lo que escribe el usuario y devuelve texto.

        Sigue la cascada descrita arriba en el modulo. Siempre devuelve un
        string, tambien cuando algo falla, para que quien llame no tenga que
        distinguir entre respuesta y error.
        """
        # Lo recordado se inyecta en el prompt del paso 3, si se llega
        context_from_memory = ""
        if self.memory:
            relevant_memories = self.memory.recall(user_input, n_results=3)

            if relevant_memories:
                context_from_memory = "\n\nINFORMACIÓN RECORDADA:\n"
                for mem in relevant_memories:
                    context_from_memory += f"- {mem['text']}\n"
        
        # PASO 1: Deteccion explicita para matematicas
        if self._detect_math_query(user_input):
            expression = self._extract_math_expression(user_input)
            
            if expression:
                result = self.tools['Calculator'].run(expression=expression)
                
                if result.get('success'):
                    # El :, mete comas como separador de miles y luego se
                    # cambian por puntos, que es como se escribe en español
                    return f"El resultado es {result['result']:,}".replace(',', '.')
                else:
                    error = result.get('error', 'Error desconocido')
                    return f"Error al calcular: {error}"
        
        # PASO 2: Deteccion explicita para codigo
        if self._detect_code_query(user_input):
            code = self._extract_code(user_input)
            
            if code:
                try:
                    result = self.tools['CodeExecutor'].run(code=code)
                    
                    if result.get('success'):
                        # CodeExecutor devuelve la salida en 'output', pero
                        # tambien la deja dentro de 'result'. Se miran las dos
                        # por si acaso
                        output = ''
                        if 'output' in result:
                            output = result['output']
                        elif 'result' in result and isinstance(result['result'], dict):
                            output = result['result'].get('stdout', '')

                        if output:
                            return f"Codigo ejecutado. Salida:\n{output}"
                        else:
                            return "Codigo ejecutado correctamente (sin salida)"

                    else:
                        # Un fallo puede venir como 'error' (lo bloqueamos
                        # nosotros) o como stderr (peto al ejecutarse)
                        error_msg = result.get('error')
                        
                        if not error_msg and 'result' in result and isinstance(result['result'], dict):
                            error_msg = result['result'].get('stderr', 'Error desconocido')
                        
                        if not error_msg:
                            error_msg = 'Error desconocido al ejecutar'
                        
                        return f"Error al ejecutar codigo:\n{error_msg}"
                
                except Exception as e:
                    return f"Error inesperado al ejecutar: {str(e)}"
        
        # PASO 3: no esta claro, que decida el modelo.
        # Se le monta el prompt entero a mano: instrucciones + lo recordado +
        # los ultimos 10 mensajes. El corte de 10 es para no pasarse del
        # contexto de 8192 tokens, que con conversaciones largas se llena.
        history_context = ""
        for msg in self.client.conversation_history[-10:]:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            history_context += f"{role}: {msg['content']}\n\n"

        decision_prompt = f"{self.system_prompt}\n\n{context_from_memory}\n\n{history_context}Usuario: {user_input}\n\nAsistente:"

        # Temperatura baja: aqui no queremos creatividad, queremos que siga
        # el formato de herramientas al pie de la letra
        response = self.client.chat(decision_prompt, temperature=0.2)

        # PASO 4: pidio una herramienta?
        # El formato <tool>...</tool><params>...</params> viene del system
        # prompt. Se parsea con regex y no con un parser de verdad porque el
        # modelo se lo salta la mitad de las veces, asi que tampoco compensa
        tool_match = re.search(r'<tool>(.*?)</tool>', response)
        params_match = re.search(r'<params>(.*?)</params>', response, re.DOTALL)

        if tool_match and params_match:
            tool_name = tool_match.group(1).strip()
            params_str = params_match.group(1).strip()
            
            if tool_name in self.tools:
                try:
                    params = json.loads(params_str)
                    tool_result = self.tools[tool_name].run(**params)
                    
                    if tool_result.get('success'):
                        if tool_name == 'Calculator':
                            result_value = tool_result.get('result', 0)
                            return f"El resultado es {result_value:,}".replace(',', '.')
                        
                        elif tool_name == 'CodeExecutor':
                            output = ''
                            if 'output' in tool_result:
                                output = tool_result['output']
                            elif 'result' in tool_result and isinstance(tool_result['result'], dict):
                                output = tool_result['result'].get('stdout', '')
                            
                            if output:
                                return f"Codigo ejecutado. Salida:\n{output}"
                            else:
                                return "Codigo ejecutado correctamente"
                        
                        else:
                            return str(tool_result.get('result', ''))
                    else:
                        error = tool_result.get('error', 'Error desconocido')
                        return f"Error: {error}"
                
                except Exception as e:
                    # Casi siempre es que los params no eran JSON valido
                    return f"Error al usar {tool_name}: {str(e)}"

        # PASO 5: contesto normal, se devuelve tal cual
        return response