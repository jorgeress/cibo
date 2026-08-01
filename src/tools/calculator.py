"""
Calculadora precisa - Evita alucinaciones del LLM en matemáticas
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
        Evalúa expresión matemática de forma segura
        
        Args:
            expression: Expresión matemática (ej: "2 + 2", "sqrt(16)")
        
        Returns:
            Dict con resultado o error
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
        
        # Caracteres permitidos (seguridad)
        allowed_chars = set('0123456789+-*/().** ')
        
        # Reemplaza funciones comunes
        expression = self._prepare_expression(expression)
        
        # Valida caracteres después de preparación
        if not all(c in allowed_chars or c.isalpha() for c in expression):
            return {
                "success": False,
                "result": None,
                "error": "Caracteres no permitidos en la expresión"
            }
        
        # Contexto seguro para eval
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
            # Evalúa de forma segura
            result = eval(expression, safe_dict, {})
            
            # Formatea resultado
            if isinstance(result, float):
                # Redondea a 10 decimales para evitar imprecisiones
                result = round(result, 10)
                # Elimina .0 si es entero
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
        """Prepara expresión para evaluación segura"""
        # Reemplaza palabras comunes
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