"""
Calculadora, para que el modelo no se invente los numeros.

Un LLM no calcula, predice texto. Si le pides 8347 * 9562 te suelta un
numero con toda la seguridad del mundo y suele estar mal, porque lo que hace
es escribir algo que se parece a un resultado. Con siete u ocho cifras ya
falla casi siempre.

La solucion es no dejarle hacer cuentas. Se detecta la operacion antes, se
calcula aqui de verdad y se le da hecha.

Sobre el uso de eval(): si evaluas la expresion tal cual, cualquiera puede
colar `__import__("os").system(...)`. Aqui se cierra por dos lados. Primero
se filtran los caracteres contra una lista blanca, y despues se llama a eval
con __builtins__ vacio, de forma que dentro solo existe lo que se le pasa a
mano (sqrt, sin, cos, pi y poco mas). Sin builtins no hay ni import ni open
ni nada a lo que agarrarse.
"""

from .base import Tool
import math
import re
from typing import Dict, Any


class Calculator(Tool):
    """Calculadora para operaciones matemáticas precisas"""
    
    def get_description(self) -> str:
        return """
        Calculadora para operaciones matemáticas precisas.
        Soporta: +, -, *, /, **, sqrt, sin, cos, tan, log, etc.
        Usa esto SIEMPRE que necesites cálculos numéricos.
        
        Ejemplos:
        - "2 + 2" → 4
        - "sqrt(144)" → 12
        - "3.14 * 5**2" → 78.5
        """
    
    def execute(self, expression: str) -> Dict[str, Any]:
        """
        Evalúa una expresión matemática.

        Args:
            expression: la operación, en símbolos o con palabras en español
                        ("2 + 2", "sqrt(16)", "raiz(16)")

        Returns:
            Dict con el resultado, o con el error si la expresión no valía
        """
        # Limpieza de la expresión
        expression = expression.strip()
        
        # Validación básica
        if not expression:
            return {
                "success": False,
                "result": None,
                "error": "Expresión vacía"
            }
        
        allowed_chars = set('0123456789+-*/().** ')

        # Traduce "raiz" a "sqrt" y demas, antes de validar
        expression = self._prepare_expression(expression)

        # Se permiten letras porque los nombres de funcion las llevan. No es
        # gran filtro por si solo, pero combinado con el __builtins__ vacio de
        # abajo deja poco margen: una letra suelta no llega a ningun sitio
        if not all(c in allowed_chars or c.isalpha() for c in expression):
            return {
                "success": False,
                "result": None,
                "error": "Caracteres no permitidos en la expresión"
            }
        
        # Todo lo que va a existir dentro del eval. Lo que no este aqui, no
        # existe, y eso incluye import, open, exec y compania
        safe_dict = {
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
            'abs': abs,
            'round': round,
            'pow': pow,
            '__builtins__': {}  # Bloquea funciones peligrosas
        }
        
        try:
            result = eval(expression, safe_dict, {})

            if isinstance(result, float):
                # Los floats arrastran basura del binario: 0.1 + 0.2 da
                # 0.30000000000000004. Con 10 decimales sobra
                result = round(result, 10)
                # Y si al final era entero, se devuelve entero
                if result.is_integer():
                    result = int(result)
            
            return {
                "success": True,
                "result": result,
                "expression": expression
            }
        
        except ZeroDivisionError:
            return {
                "success": False,
                "result": None,
                "error": "División por cero"
            }
        
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"Error al evaluar: {str(e)}"
            }
    
    def _prepare_expression(self, expr: str) -> str:
        """
        Traduce los nombres de funcion en español a los de math.

        Como el asistente se usa en español, es normal que llegue "raiz(16)"
        en vez de "sqrt(16)". Se pasa todo a minusculas de paso, que math no
        entiende SQRT.
        """
        replacements = {
            'raiz': 'sqrt',
            'raíz': 'sqrt',
            'seno': 'sin',
            'coseno': 'cos',
            'tangente': 'tan',
            'logaritmo': 'log',
            'exponencial': 'exp',
        }
        
        expr_lower = expr.lower()
        for spanish, english in replacements.items():
            expr_lower = expr_lower.replace(spanish, english)
        
        return expr_lower


# === TESTS ===
if __name__ == "__main__":
    calc = Calculator()
    
    tests = [
        "2 + 2",
        "1234 * 5678",
        "sqrt(144)",
        "3.14 * 5**2",
        "sin(pi/2)",
        "log(100)",
        "raiz(16)",  # Español
        "1 / 0",     # Error
    ]
    
    print("="*60)
    print("TEST: Calculadora")
    print("="*60)
    
    for test in tests:
        result = calc.run(expression=test)
        
        print(f"\nExpresión: {test}")
        
        if result["success"]:
            print(f"Resultado: {result['result']}")
        else:
            print(f"Error: {result['error']}")
    
    print(f"\n{'='*60}")
    print(f"Herramienta usada {calc.usage_count} veces")