"""
Test de diagnóstico simple
"""

print("="*60)
print("INICIANDO TESTS...")
print("="*60)

# Test 1: Imports
print("\n[1/5] Testeando imports...")
try:
    import sys
    import os
    print("✅ Imports básicos OK")
except Exception as e:
    print(f"❌ Error en imports: {e}")
    exit(1)

# Test 2: Path
print("\n[2/5] Configurando path...")
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    print(f"✅ Path configurado: {sys.path[-1]}")
except Exception as e:
    print(f"❌ Error en path: {e}")
    exit(1)

# Test 3: Import del cliente
print("\n[3/5] Importando OllamaClient...")
try:
    from core.ollama_client import OllamaClient
    print("✅ OllamaClient importado")
except Exception as e:
    print(f"❌ Error importando OllamaClient: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Import de herramientas
print("\n[4/5] Importando herramientas...")
try:
    from tools.calculator import Calculator
    from tools.code_executor import CodeExecutor
    print("✅ Herramientas importadas")
except Exception as e:
    print(f"❌ Error importando herramientas: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Import del agente
print("\n[5/5] Importando Agent...")
try:
    from core.agent import Agent
    print("✅ Agent importado")
except Exception as e:
    print(f"❌ Error importando Agent: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 6: Conexión Ollama
print("\n[6/6] Verificando Ollama...")
try:
    client = OllamaClient()
    if client.is_running():
        print("✅ Ollama está corriendo")
        print(f"   Modelo: {client.model}")
    else:
        print("❌ Ollama NO está corriendo")
        print("   Ejecuta en otra terminal: ollama serve")
except Exception as e:
    print(f"❌ Error conectando a Ollama: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Calculadora básica
print("\n[7/7] Test calculadora...")
try:
    calc = Calculator()
    result = calc.run(expression="2+2")
    if result["success"] and result["result"] == 4:
        print(f"✅ Calculadora funciona: 2+2 = {result['result']}")
    else:
        print(f"❌ Calculadora falló: {result}")
except Exception as e:
    print(f"❌ Error en calculadora: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("DIAGNÓSTICO COMPLETO")
print("="*60)