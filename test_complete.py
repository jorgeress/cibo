"""
Suite completa de tests - VERSION CORREGIDA
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.ollama_client import OllamaClient
from core.agent import Agent
from tools.calculator import Calculator
from tools.code_executor import CodeExecutor


def test_ollama_connection():
    """Test 1: Conexion con Ollama"""
    print("\n" + "="*60)
    print("TEST 1: Conexion con Ollama")
    print("="*60)
    
    client = OllamaClient()
    
    if client.is_running():
        print("✅ Ollama esta corriendo")
        models = client.get_models()
        print(f"✅ {len(models)} modelo(s) disponible(s)")
        print(f"   Usando: {client.model}")
        return True
    else:
        print("❌ Ollama NO esta corriendo")
        return False


def test_calculator():
    """Test 2: Calculadora"""
    print("\n" + "="*60)
    print("TEST 2: Calculadora")
    print("="*60)
    
    calc = Calculator()
    
    tests = [
        ("2 + 2", 4),
        ("1234 * 5678", 7006652),
        ("sqrt(144)", 12),
        ("3.14 * 5**2", 78.5),
    ]
    
    all_passed = True
    
    for expr, expected in tests:
        result = calc.run(expression=expr)
        
        if result["success"]:
            actual = result["result"]
            passed = abs(actual - expected) < 0.01
            
            status = "✅" if passed else "❌"
            print(f"{status} {expr} = {actual} (esperado: {expected})")
            
            if not passed:
                all_passed = False
        else:
            print(f"❌ {expr} - Error: {result['error']}")
            all_passed = False
    
    return all_passed


def test_code_executor():
    """Test 3: Ejecutor de codigo"""
    print("\n" + "="*60)
    print("TEST 3: Ejecutor de Codigo")
    print("="*60)
    
    executor = CodeExecutor()
    
    # Test exitoso
    code1 = 'print("Hola desde Python")'
    result1 = executor.run(code=code1)
    
    if result1["success"] and "Hola desde Python" in result1["output"]:
        print("✅ Ejecucion simple: OK")
        success1 = True
    else:
        print("❌ Ejecucion simple: FALLO")
        success1 = False
    
    # Test con calculo
    code2 = 'suma = sum(range(1, 11))\nprint(f"Suma: {suma}")'
    result2 = executor.run(code=code2)
    
    if result2["success"] and "55" in result2["output"]:
        print("✅ Calculo en codigo: OK")
        success2 = True
    else:
        print("❌ Calculo en codigo: FALLO")
        success2 = False
    
    # Test seguridad
    code3 = 'import os\nprint(os.listdir())'
    result3 = executor.run(code=code3)
    
    if not result3["success"] and "no permitida" in result3["error"]:
        print("✅ Seguridad (bloqueo import): OK")
        success3 = True
    else:
        print("❌ Seguridad: FALLO")
        success3 = False
    
    return success1 and success2 and success3


def test_agent_calculator():
    """Test 4: Agente usa calculadora"""
    print("\n" + "="*60)
    print("TEST 4: Agente + Calculadora")
    print("="*60)
    print("⚠️  NOTA: Este test puede tardar 10-30 segundos...")
    
    client = OllamaClient()
    tools = [Calculator(), CodeExecutor()]
    agent = Agent(client, tools)
    
    question = "Cuanto es 8347 * 9562?"
    print(f"Pregunta: {question}")
    print("Procesando...", end="", flush=True)
    
    try:
        response = agent.process(question)
        print(" OK")
        
        # CORRECCION: El resultado correcto es 79814014
        correct_answer = "79814014"
        
        # Limpia la respuesta de puntos y comas
        clean_response = response.replace(",", "").replace(".", "")
        
        if correct_answer in clean_response:
            print(f"✅ Respuesta correcta detectada")
            print(f"   Respuesta: {response}")
            return True
        else:
            print(f"❌ Respuesta incorrecta o no uso calculadora")
            print(f"   Respuesta: {response}")
            print(f"   Se esperaba: {correct_answer}")
            return False
    
    except Exception as e:
        print(f"\n❌ Error en agente: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_code():
    """Test 5: Agente ejecuta codigo"""
    print("\n" + "="*60)
    print("TEST 5: Agente + Codigo")
    print("="*60)
    print("⚠️  NOTA: Este test puede tardar 10-30 segundos...")
    
    client = OllamaClient()
    tools = [Calculator(), CodeExecutor()]
    agent = Agent(client, tools)
    
    question = "Ejecuta este codigo: print('Test exitoso')"
    print(f"Pregunta: {question}")
    print("Procesando...", end="", flush=True)
    
    try:
        response = agent.process(question)
        print(" OK")
        
        if "exitoso" in response.lower() or "Test exitoso" in response:
            print(f"✅ Codigo ejecutado correctamente")
            print(f"   Fragmento: ...{response[:80]}...")
            return True
        else:
            print(f"❌ No ejecuto el codigo")
            print(f"   Respuesta: {response}")
            return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_agent_conversation():
    """Test 6: Agente responde preguntas normales"""
    print("\n" + "="*60)
    print("TEST 6: Agente - Conversacion Normal")
    print("="*60)
    print("⚠️  NOTA: Este test puede tardar 5-15 segundos...")
    
    client = OllamaClient()
    tools = [Calculator(), CodeExecutor()]
    agent = Agent(client, tools)
    
    question = "Que es Python?"
    print(f"Pregunta: {question}")
    print("Procesando...", end="", flush=True)
    
    try:
        response = agent.process(question)
        print(" OK")
        
        if len(response) > 20 and "Python" in response:
            print(f"✅ Conversacion normal funciona")
            print(f"   Fragmento: ...{response[:80]}...")
            return True
        else:
            print(f"❌ Respuesta muy corta o irrelevante")
            print(f"   Respuesta: {response}")
            return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "🧪"*30)
    print("SUITE COMPLETA DE TESTS - CIBO")
    print("🧪"*30)
    
    results = []
    
    # Test 1: Conexion
    ollama_running = test_ollama_connection()
    
    if not ollama_running:
        print("\n" + "="*60)
        print("❌ ABORTADO: Ollama no esta corriendo")
        print("   Ejecuta en otra terminal: ollama serve")
        print("="*60 + "\n")
        return
    
    results.append(("Ollama", True))
    
    # Test 2: Calculadora
    results.append(("Calculadora", test_calculator()))
    
    # Test 3: Ejecutor
    results.append(("Ejecutor de Codigo", test_code_executor()))
    
    # Test 4: Agente + Calculadora
    results.append(("Agente + Calculadora", test_agent_calculator()))
    
    # Test 5: Agente + Codigo
    results.append(("Agente + Codigo", test_agent_code()))
    
    # Test 6: Agente conversacion
    results.append(("Agente + Conversacion", test_agent_conversation()))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("\n" + "="*60)
    print(f"RESULTADO: {passed}/{total} tests pasados")
    
    if passed == total:
        print("🎉 TODOS LOS TESTS PASARON!")
    else:
        print("⚠️  Algunos tests fallaron")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\nINICIANDO TESTS...\n")
    run_all_tests()