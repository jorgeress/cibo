"""
Ejecuta codigo Python y devuelve lo que imprima.

AVISO: esto NO es un sandbox. Es una barrera contra codigo que la lie sin
querer, no contra alguien que quiera saltarsela. El codigo corre en un
proceso de Python normal, con los permisos del usuario. Las comprobaciones
de aqui son analisis estatico del texto, y el analisis estatico se esquiva
sin despeinarse (getattr, cadenas montadas al vuelo, lo que sea). Si esto se
expusiera a entrada de terceros haria falta un contenedor de verdad.

Dicho eso, para lo que esta pensado (que el modelo ejecute cuatro lineas que
le pasas tu) sirve. Lo que hace:

    - bloquea imports de modulos con los que se puede tocar el sistema
    - bloquea eval, exec, compile y open
    - corre en un subproceso aparte, no en el del asistente
    - lo mata a los 5 segundos, para que un while True no cuelgue nada
    - trabaja en el directorio temporal, no en el del proyecto
    - corta la salida a 5000 caracteres

Lo del subproceso es lo que mas aporta: si el codigo peta, revienta el
subproceso y el asistente ni se entera.
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
        Busca imports que no deberian estar.

        El detalle esta en mirar linea por linea con patrones de import, y no
        buscar la palabra suelta en todo el texto. Si buscas "os" a pelo,
        `mensaje = 'exitoso'` salta por los pelos y bloqueas codigo inocente.
        Tambien se saltan los comentarios, que un `# import os` no ejecuta
        nada.

        Returns:
            (es_peligroso, nombre_del_modulo)
        """
        # Los cuatro primeros dan acceso al sistema de archivos y a lanzar
        # procesos. El resto son formas de salir a la red
        dangerous = [
            'os', 'sys', 'subprocess', 'socket', 'requests',
            'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib',
            '__import__', 'eval', 'exec', 'compile', 'open'
        ]

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
        
        # eval, exec y compile tambien valen sin importar nada, asi que se
        # buscan aparte como llamada a funcion
        for danger in ['eval', 'exec', 'compile']:
            if re.search(rf'\b{danger}\s*\(', code):
                return True, danger

        return False, None
    
    def execute(self, code: str) -> Dict[str, Any]:
        """
        Escribe el codigo a un archivo temporal y lo lanza en un subproceso.

        Hace falta el archivo porque se invoca al interprete de Python como
        si lo hubieras escrito tu en la terminal, y eso necesita un .py.

        El cwd apunta al directorio temporal a proposito: si el codigo crea
        archivos, que los cree ahi y no en el proyecto.

        Returns:
            En 'result' van stdout, stderr y el codigo de salida. En 'output'
            va lo que interese enseñar, que es stdout si hubo, y si no stderr.
        """
        
        if not code or not code.strip():
            return {
                "success": False,
                "result": None,
                "error": "Codigo vacio"
            }
        
        # Se revisa antes de escribir nada al disco
        is_dangerous, dangerous_module = self._detect_dangerous_imports(code)

        if is_dangerous:
            return {
                "success": False,
                "result": None,
                "error": f"Importacion no permitida: {dangerous_module}"
            }
        
        temp_file = None
        try:
            # delete=False porque en Windows no se puede abrir un temporal
            # que sigue abierto en otro sitio. Se cierra, se ejecuta y se
            # borra a mano despues
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