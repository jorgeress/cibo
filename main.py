"""
CIBO: consola interactiva del asistente.

Punto de entrada del proyecto. Monta las piezas y se queda en un bucle
leyendo lo que escribes: comprueba que Ollama responda, carga las
herramientas, crea el agente, y a partir de ahi cada linea que empieza por
"/" es un comando y el resto va al agente.

El agente es quien decide si una pregunta necesita calculadora, ejecutar
codigo o simplemente responder. Aqui no hay nada de esa logica, solo la
interfaz: la cascada de decision esta en src/core/agent.py.

Para arrancarlo:  python main.py   (con `ollama serve` levantado)
"""

import sys
import os

# main.py vive fuera de src/, asi que hay que meter esa carpeta en el path
# para poder importar core, tools y compañia como paquetes de primer nivel
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.ollama_client import OllamaClient
from core.agent import Agent
from tools.calculator import Calculator
from tools.code_executor import CodeExecutor


def clear_screen():
    """Limpia pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Header del programa"""
    print("\n" + "="*60)
    print("  🤖 CIBO - Asistente con Herramientas")
    print("="*60)


def print_help():
    """Muestra comandos y capacidades"""
    print("""
📚 COMANDOS:
  /exit      - Salir
  /clear     - Limpiar pantalla e historial
  /history   - Ver conversaciones previas
  /save      - Guardar conversación
  /tools     - Ver herramientas disponibles
  /models    - Ver modelos disponibles
  /help      - Esta ayuda

🛠️  CAPACIDADES:
  ✅ Cálculos matemáticos precisos (usa Calculator automáticamente)
  ✅ Ejecutar código Python (usa CodeExecutor)
  ✅ Conversación natural
  ✅ Memoria durante la sesión
""")


def print_tools(agent):
    """Muestra herramientas disponibles"""
    print("\n" + "="*60)
    print("🛠️  HERRAMIENTAS DISPONIBLES")
    print("="*60)
    
    for name, tool in agent.tools.items():
        print(f"\n📦 {name}")
        print(f"   {tool.description.strip()[:100]}...")
        print(f"   Usada: {tool.usage_count} veces")
    
    print("\n" + "="*60 + "\n")


def print_history(client):
    """Muestra historial formateado"""
    history = client.get_history()
    
    if not history:
        print("\n📭 Sin historial\n")
        return
    
    print("\n" + "="*60)
    print(f"📜 HISTORIAL ({len(history)//2} intercambios)")
    print("="*60)
    
    for i in range(0, len(history), 2):
        if i+1 < len(history):
            user_msg = history[i]["content"][:150]
            bot_msg = history[i+1]["content"][:150]
            
            print(f"\n[{i//2 + 1}]")
            print(f"👤: {user_msg}{'...' if len(history[i]['content']) > 150 else ''}")
            print(f"🤖: {bot_msg}{'...' if len(history[i+1]['content']) > 150 else ''}")
    
    print("\n" + "="*60 + "\n")


def main():
    """Arranca el sistema y se queda en el bucle de conversacion"""
    clear_screen()
    print_header()

    # === INICIALIZACIÓN ===
    print("\n🔧 Inicializando sistema...")

    client = OllamaClient()

    # Se comprueba antes de nada porque el fallo mas comun con diferencia es
    # olvidarse de arrancar el servidor
    if not client.is_running():
        print("❌ Ollama no está corriendo")
        print("   Ejecuta: ollama serve\n")
        return

    print("✅ Ollama conectado")

    # Para añadir una herramienta basta con instanciarla aqui: el agente las
    # indexa por su nombre de clase y las reconoce sola
    tools = [
        Calculator(),
        CodeExecutor()
    ]

    print(f"✅ {len(tools)} herramientas cargadas")

    # Sin memoria persistente: use_memory=True la activa, pero pide chromadb
    agent = Agent(client, tools)
    print("✅ Agente inicializado")
    
    # Info del modelo
    models = client.get_models()
    print(f"\n📦 Modelo: {client.model}")
    print(f"💡 Escribe /help para ver capacidades\n")
    
    # === LOOP PRINCIPAL ===
    while True:
        try:
            # Input usuario
            user_input = input("👤 Tú: ").strip()
            
            if not user_input:
                continue
            
            # === COMANDOS ===
            if user_input.startswith("/"):
                cmd = user_input.lower()
                
                # Salir
                if cmd in ["/exit", "/quit", "/q"]:
                    print("\n👋 ¡Hasta luego!\n")
                    break
                
                # Limpiar
                elif cmd == "/clear":
                    client.clear_history()
                    clear_screen()
                    print_header()
                    print("\n✓ Historial limpiado\n")
                
                # Historial
                elif cmd == "/history":
                    print_history(client)
                
                # Guardar
                elif cmd == "/save":
                    if not client.get_history():
                        print("\n⚠️  No hay nada que guardar\n")
                    else:
                        filename = input("Nombre (Enter=chat.json): ").strip()
                        if not filename:
                            filename = "chat.json"
                        if not filename.endswith('.json'):
                            filename += '.json'
                        
                        filepath = os.path.join("data", "conversations", filename)
                        client.export_history(filepath)
                        print()
                
                # Herramientas
                elif cmd == "/tools":
                    print_tools(agent)
                
                # Modelos
                elif cmd == "/models":
                    print("\n📦 MODELOS DISPONIBLES:")
                    for model in client.get_models():
                        current = " ⭐" if model == client.model else ""
                        print(f"   • {model}{current}")
                    print()
                
                # Ayuda
                elif cmd == "/help":
                    print_help()
                
                # Comando desconocido
                else:
                    print(f"\n❌ Comando desconocido: {user_input}")
                    print("   Usa /help\n")
                
                continue
            
            # === PROCESAMIENTO CON AGENTE ===
            print("🤖 CIBO: ", end="", flush=True)
            
            # El agente decide si usar herramientas o responder normal
            response = agent.process(user_input)
            
            # Imprime respuesta
            print(response)
            print()
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Usa /exit para salir limpiamente\n")
            continue
        
        except Exception as e:
            print(f"\n\n❌ Error inesperado: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()