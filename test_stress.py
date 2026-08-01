"""
Test de estres - Casos complejos y edge cases
Simula uso real del asistente
"""

import sys
import os
sys.path.append('src')

from core.ollama_client import OllamaClient
from core.agent import Agent
from tools.calculator import Calculator
from tools.code_executor import CodeExecutor
import time


class StressTest:
    def __init__(self):
        self.client = OllamaClient()
        self.tools = [Calculator(), CodeExecutor()]
        self.agent = Agent(self.client, self.tools)
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def run_test(self, name: str, query: str, expected_behavior: str, validator):
        """
        Ejecuta un test individual
        
        Args:
            name: Nombre del test
            query: Pregunta del usuario
            expected_behavior: Comportamiento esperado
            validator: Funcion que valida si paso (recibe response, retorna bool)
        """
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"Esperado: {expected_behavior}")
        print("Procesando...", end="", flush=True)
        
        start_time = time.time()
        
        try:
            response = self.agent.process(query)
            elapsed = time.time() - start_time
            
            print(f" OK ({elapsed:.1f}s)")
            print(f"Respuesta: {response[:200]}{'...' if len(response) > 200 else ''}")
            
            # Valida
            passed = validator(response)
            
            if passed:
                print("✅ TEST PASADO")
                self.passed += 1
            else:
                print("❌ TEST FALLIDO")
                self.failed += 1
            
            self.results.append({
                "name": name,
                "passed": passed,
                "query": query,
                "response": response[:300],
                "time": elapsed
            })
        
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ EXCEPCION: {e}")
            self.failed += 1
            self.results.append({
                "name": name,
                "passed": False,
                "query": query,
                "response": f"ERROR: {e}",
                "time": elapsed
            })
    
    def run_all(self):
        print("\n" + "🔥"*30)
        print("TEST DE ESTRES - CASOS COMPLEJOS")
        print("🔥"*30)
        
        # ===== CATEGORIA 1: MATEMATICAS AMBIGUAS =====
        print("\n" + "="*60)
        print("CATEGORIA 1: MATEMATICAS AMBIGUAS")
        print("="*60)
        
        self.run_test(
            "Matematicas con texto mezclado",
            "Tengo 15 manzanas y compro 23 mas, cuantas tengo?",
            "Deberia usar Calculator para sumar 15 + 23",
            lambda r: "38" in r.replace(" ", "")
        )
        
        self.run_test(
            "Operacion compleja",
            "Calcula (25 * 4) + (100 / 2) - 10",
            "Deberia usar Calculator",
            lambda r: "140" in r.replace(" ", "")
        )
        
        self.run_test(
            "Numero muy grande",
            "Multiplica 999999 por 888888",
            "Deberia usar Calculator (no calcular mentalmente)",
            lambda r: "888887111112" in r.replace(".", "").replace(",", "").replace(" ", "")
        )
        
        self.run_test(
            "Division con decimales",
            "Cuanto es 22 dividido entre 7?",
            "Deberia dar ~3.14",
            lambda r: "3.14" in r or "3,14" in r or "3.1" in r
        )
        
        # ===== CATEGORIA 2: CODIGO COMPLEJO =====
        print("\n" + "="*60)
        print("CATEGORIA 2: CODIGO COMPLEJO")
        print("="*60)
        
        self.run_test(
            "Codigo con bucle",
            "Ejecuta: for i in range(3): print(i)",
            "Deberia ejecutar y mostrar 0 1 2",
            lambda r: ("0" in r and "1" in r and "2" in r) or "ejecutado" in r.lower()
        )
        
        self.run_test(
            "Codigo con lista",
            "Corre esto: nums = [1,2,3]; print(sum(nums))",
            "Deberia mostrar 6",
            lambda r: "6" in r or "ejecutado" in r.lower()
        )
        
        self.run_test(
            "Codigo multilinea",
            """Ejecuta este codigo:
x = 10
y = 20
print(x + y)""",
            "Deberia mostrar 30",
            lambda r: "30" in r or "ejecutado" in r.lower()
        )
        
        # ===== CATEGORIA 3: CASOS AMBIGUOS =====
        print("\n" + "="*60)
        print("CATEGORIA 3: CASOS AMBIGUOS (DIFICILES)")
        print("="*60)
        
        self.run_test(
            "Pregunta conceptual con numeros",
            "Que es Python 3.11?",
            "NO deberia usar Calculator (es pregunta conceptual)",
            lambda r: len(r) > 30 and "Python" in r and "error" not in r.lower()
        )
        
        self.run_test(
            "Mencion de codigo sin pedirlo",
            "Me gusta usar print() en Python",
            "NO deberia ejecutar nada (solo menciona print)",
            lambda r: "ejecutado" not in r.lower() and len(r) > 20
        )
        
        self.run_test(
            "Matematicas conceptuales",
            "Explica que es una suma",
            "NO deberia usar Calculator (es explicacion)",
            lambda r: len(r) > 30 and ("suma" in r.lower() or "adicion" in r.lower())
        )
        
        # ===== CATEGORIA 4: ERRORES Y EDGE CASES =====
        print("\n" + "="*60)
        print("CATEGORIA 4: MANEJO DE ERRORES")
        print("="*60)
        
        self.run_test(
            "Division por cero",
            "Cuanto es 10 / 0?",
            "Deberia detectar division por cero",
            lambda r: "cero" in r.lower() or "error" in r.lower() or "infinito" in r.lower()
        )
        
        self.run_test(
            "Codigo con error de sintaxis",
            "Ejecuta: print('hola'",
            "Deberia reportar error de sintaxis",
            lambda r: "error" in r.lower() or "sintaxis" in r.lower()
        )
        
        self.run_test(
            "Expresion matematica invalida",
            "Calcula sqrt(-1)",
            "Deberia manejar raiz cuadrada de negativo",
            lambda r: "error" in r.lower() or "complejo" in r.lower() or "math domain" in r.lower() or "nan" in r.lower()
        )
        
        # ===== CATEGORIA 5: CONVERSACION NATURAL =====
        print("\n" + "="*60)
        print("CATEGORIA 5: CONVERSACION NATURAL")
        print("="*60)
        
        self.run_test(
            "Saludo simple",
            "Hola, como estas?",
            "Deberia responder naturalmente",
            lambda r: len(r) > 10 and "hola" in r.lower() and "herramienta" not in r.lower()
        )
        
        self.run_test(
            "Pregunta sobre el mismo CIBO",
            "Que eres tu?",
            "Deberia explicar que es CIBO",
            lambda r: len(r) > 20 and ("asistente" in r.lower() or "cibo" in r.lower() or "ayuda" in r.lower())
        )
        
        self.run_test(
            "Pregunta sobre capacidades",
            "Que puedes hacer?",
            "Deberia mencionar sus herramientas",
            lambda r: len(r) > 30 and ("calculadora" in r.lower() or "codigo" in r.lower() or "matematicas" in r.lower())
        )
        
        # ===== CATEGORIA 6: CONTEXTO Y MEMORIA =====
        print("\n" + "="*60)
        print("CATEGORIA 6: MEMORIA CONVERSACIONAL")
        print("="*60)
        
        self.agent.client.clear_history()  # Reset
        
        self.run_test(
            "Contexto - Parte 1",
            "Mi numero favorito es el 42",
            "Deberia recordar el numero",
            lambda r: len(r) > 10
        )
        
        self.run_test(
            "Contexto - Parte 2",
            "Cual es mi numero favorito?",
            "Deberia recordar que es 42",
            lambda r: "42" in r
        )
        
        # ===== RESUMEN =====
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumen final"""
        print("\n" + "="*60)
        print("RESUMEN FINAL - TEST DE ESTRES")
        print("="*60)
        
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\nTests ejecutados: {total}")
        print(f"✅ Pasados: {self.passed}")
        print(f"❌ Fallidos: {self.failed}")
        print(f"📊 Tasa de exito: {percentage:.1f}%")
        
        # Tiempo promedio
        avg_time = sum(r['time'] for r in self.results) / len(self.results) if self.results else 0
        print(f"⏱️  Tiempo promedio: {avg_time:.2f}s")
        
        # Detalles de fallos
        if self.failed > 0:
            print(f"\n{'='*60}")
            print("DETALLES DE FALLOS:")
            print(f"{'='*60}")
            
            for result in self.results:
                if not result['passed']:
                    print(f"\n❌ {result['name']}")
                    print(f"   Query: {result['query'][:80]}")
                    print(f"   Respuesta: {result['response'][:150]}...")
        
        # Evaluacion final
        print(f"\n{'='*60}")
        if percentage >= 90:
            print("🎉 EXCELENTE - Sistema muy robusto")
        elif percentage >= 75:
            print("✅ BUENO - Sistema funcional con areas de mejora")
        elif percentage >= 60:
            print("⚠️  REGULAR - Necesita mejoras importantes")
        else:
            print("❌ CRITICO - Sistema necesita revision profunda")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    if not OllamaClient().is_running():
        print("❌ Ollama no esta corriendo. Ejecuta: ollama serve\n")
        exit(1)
    
    test = StressTest()
    test.run_all()