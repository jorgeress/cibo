"""
Traza paso a paso del agente ejecutando codigo.

El mas util de los cuatro cuando algo no funciona. En vez de decir si pasa
o falla, va imprimiendo cada fase (que detecta, que codigo extrae, que
devuelve CodeExecutor), asi que se ve exactamente en que punto se tuerce.

Necesita Ollama corriendo. Se lanza a mano, no con pytest.
"""

import sys
import os
sys.path.append('src')

from core.ollama_client import OllamaClient
from core.agent import Agent
from tools.calculator import Calculator
from tools.code_executor import CodeExecutor

print("="*60)
print("DEBUG: Agente + Codigo")
print("="*60)

# Inicializa
client = OllamaClient()
tools = [Calculator(), CodeExecutor()]
agent = Agent(client, tools)

question = "Ejecuta este codigo: print('Test exitoso')"

print(f"\n1. Pregunta: {question}")

print("\n2. Detectando tipo de query...")
is_code = agent._detect_code_query(question)
print(f"   Es codigo? {is_code}")

if is_code:
    print("\n3. Extrayendo codigo...")
    import re
    
    # Intenta extraer
    code_match = re.search(r'["\'](.+?)["\']', question)
    if code_match:
        code = code_match.group(1)
        print(f"   Codigo extraido (metodo 1): '{code}'")
    else:
        code_match = re.search(r':\s*(.+)$', question)
        if code_match:
            code = code_match.group(1)
            print(f"   Codigo extraido (metodo 2): '{code}'")
        else:
            print("   ❌ No se pudo extraer codigo")
            code = None
    
    if code:
        print("\n4. Ejecutando codigo...")
        try:
            executor = CodeExecutor()
            result = executor.run(code=code)
            
            print(f"   Success: {result.get('success')}")
            print(f"   Result keys: {result.keys()}")
            print(f"   Full result: {result}")
            
            if result.get('success'):
                print(f"\n✅ Codigo ejecutado correctamente")
                print(f"   Output: {result.get('output')}")
            else:
                print(f"\n❌ Error al ejecutar")
                print(f"   Error: {result.get('error')}")
        
        except Exception as e:
            print(f"\n❌ Excepcion: {e}")
            import traceback
            traceback.print_exc()

print("\n5. Procesando con agente completo...")
try:
    response = agent.process(question)
    print(f"✅ Respuesta: {response}")
except Exception as e:
    print(f"❌ Error en agent.process: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)