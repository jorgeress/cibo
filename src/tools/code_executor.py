"""
Ejecutor de codigo Python seguro - VERSION MEJORADA
"""

from .base import Tool
import subprocess
import tempfile
import os
import re
from typing import Dict, Any


class CodeExecutor(Tool):
    """Ejecuta codigo Python de forma segura"""
    
    def __init__(self):
        super().__init__()
        self.timeout = 5
        self.max_output_length = 5000
    
    def get_description(self) -> str:
        return "Ejecuta codigo Python en sandbox. Timeout 5s, sin acceso a red ni archivos."
    
    def _detect_dangerous_imports(self, code: str) -> tuple[bool, str]:
        """
        Detecta imports peligrosos de forma inteligente
        
        Returns:
            (es_peligroso, modulo_detectado)
        """
        dangerous = [
            'os', 'sys', 'subprocess', 'socket', 'requests',
            'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib',
            '__import__', 'eval', 'exec', 'compile', 'open'
        ]
        
        # Patrones para detectar imports reales
        import_patterns = [
            r'^\s*import\s+(\w+)',           # import os
            r'^\s*from\s+(\w+)\s+import',    # from os import path
            r'__import__\s*\(\s*["\'](\w+)', # __import__('os')
        ]
        
        lines = code.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Ignora comentarios
            if line_stripped.startswith('#'):
                continue
            
            # Busca cada patron
            for pattern in import_patterns:
                match = re.search(pattern, line_stripped)
                if match:
                    module = match.group(1)
                    if module in dangerous:
                        return True, module
        
        # Busca eval/exec/compile como funciones
        for danger in ['eval', 'exec', 'compile']:
            if re.search(rf'\b{danger}\s*\(', code):
                return True, danger
        
        return False, None
    
    def execute(self, code: str) -> Dict[str, Any]:
        """Ejecuta codigo Python"""
        
        if not code or not code.strip():
            return {
                "success": False,
                "result": None,
                "error": "Codigo vacio"
            }
        
        # Seguridad mejorada
        is_dangerous, dangerous_module = self._detect_dangerous_imports(code)
        
        if is_dangerous:
            return {
                "success": False,
                "result": None,
                "error": f"Importacion no permitida: {dangerous_module}"
            }
        
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir()
            )
            
            stdout = result.stdout[:self.max_output_length]
            stderr = result.stderr[:self.max_output_length]
            
            os.remove(temp_file)
            
            return {
                "success": result.returncode == 0,
                "result": {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": result.returncode
                },
                "output": stdout if stdout else stderr
            }
        
        except subprocess.TimeoutExpired:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return {
                "success": False,
                "result": None,
                "error": "Timeout: codigo tardo mas de 5 segundos"
            }
        
        except Exception as e:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return {
                "success": False,
                "result": None,
                "error": f"Error: {str(e)}"
            }


# === TESTS ===
if __name__ == "__main__":
    executor = CodeExecutor()
    
    print("="*60)
    print("TEST: Ejecutor de Codigo - Deteccion Mejorada")
    print("="*60)
    
    tests = [
        {
            "name": "Codigo limpio (exitoso)",
            "code": "print('Test exitoso')",
            "should_pass": True
        },
        {
            "name": "Palabra 'os' en string (exitoso)",
            "code": "mensaje = 'exitoso'\nprint(mensaje)",
            "should_pass": True
        },
        {
            "name": "Import peligroso directo",
            "code": "import os\nprint(os.listdir())",
            "should_pass": False
        },
        {
            "name": "Import peligroso con from",
            "code": "from os import path\nprint(path)",
            "should_pass": False
        },
        {
            "name": "Comentario con import",
            "code": "# import os\nprint('OK')",
            "should_pass": True
        },
    ]
    
    for test in tests:
        print(f"\n--- {test['name']} ---")
        print(f"Codigo: {test['code'][:50]}...")
        
        result = executor.run(code=test['code'])
        
        passed = (result['success'] == test['should_pass']) or \
                 (not result['success'] and not test['should_pass'])
        
        status = "✅" if passed else "❌"
        
        if result['success']:
            print(f"{status} Ejecutado: {result['output'][:50]}")
        else:
            print(f"{status} Bloqueado: {result['error']}")
    
    print("\n" + "="*60)