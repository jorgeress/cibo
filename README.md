# CIBO

Empecé esto el 26 de enero de 2026 con la idea de entender de verdad cómo funciona un LLM por dentro, en vez de quedarme en usar ChatGPT y ya. Quería montar un modelo local, escribir yo el código que lo rodea y de paso soltarme con Python: clases abstractas, subprocesos, APIs HTTP, todo eso que se aprende mejor cuando lo necesitas para algo tuyo.

CIBO es un asistente que corre entero en local con [Ollama](https://ollama.com/). Sabe cuándo le conviene tirar de una herramienta (una calculadora de verdad, un ejecutor de Python) en lugar de improvisar la respuesta, y si se lo permito puede mandar consultas a modelos en la nube. Por defecto no sale nada del equipo.

> **Proyecto en pausa indefinida.** Lo dejé aparcado y no tengo previsto retomarlo a corto plazo. Los motivos están explicados abajo, en [Estado del proyecto](#estado-del-proyecto). Lo publico porque el código sirve para ver cómo se monta esto por dentro, no como algo terminado ni mantenido.

Hay piezas a medio hacer. Las tengo listadas al final, sin maquillar.

## Cómo ha ido creciendo

**26 de enero de 2026.** Lo mínimo para hablar con el modelo: cliente HTTP contra Ollama con streaming token a token, el bucle de consola y el modelfile con la personalidad de CIBO.

**28 de enero.** El sistema de herramientas. Aquí es donde empezó lo interesante, porque un LLM de 8B es malísimo con los números y hacía falta que delegase en una calculadora real. De paso, un ejecutor de Python en subproceso y los scripts de prueba.

**7 de febrero.** La capa de arriba: memoria vectorial con ChromaDB, agentes intercambiables (Ollama, Claude, Gemini) tras una interfaz común, un router que decide cuál usar y la parte de privacidad.

## Qué hace

Corre local por defecto. El modelo va en Ollama contra mi GPU y no hace llamadas a internet salvo que yo active los agentes de nube.

Usa herramientas cuando toca. El agente lee la intención de lo que escribes: si detecta matemáticas llama a `Calculator`, y si le pides ejecutar algo llama a `CodeExecutor`, que corre el código en un subproceso con timeout.

Recuerda entre sesiones. ChromaDB guarda información en una base vectorial persistente. Es opcional y viene desactivado.

Cambia de modelo según el caso. Ollama, Claude y Gemini comparten la misma interfaz, así que el router puede elegir uno u otro sin que el resto del código se entere.

Protege lo que no debe salir. Hay tres modos de privacidad (`paranoid`, `balanced`, `performance`) y una capa que detecta API keys, contraseñas, tarjetas o números de la seguridad social antes de que puedan viajar a la nube. También redacta IPs y emails de las respuestas que vuelven.

## Requisitos

| Requisito | Versión / nota |
|---|---|
| Python | 3.10 o superior (lo desarrollo con 3.13) |
| Ollama | corriendo en `localhost:11434` |
| Modelo | `llama3.1:8b`, o el propio `cibo:latest` |
| GPU | recomendada, con 8 GB de VRAM llega justo para un 8B. En CPU va, pero lento |

## Instalación

```bash
git clone https://github.com/jorgeress/cibo-project.git
cd cibo-project

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

pip install -r requirements.txt

cp .env.example .env         # y ajusta los valores
```

Arranca Ollama y baja el modelo base:

```bash
ollama serve
ollama pull llama3.1:8b
```

### Modelo propio (opcional)

`cibo-config.modelfile` define la personalidad de CIBO y sus parámetros de rendimiento: 8192 tokens de contexto, temperatura 0.7 y `repeat_penalty` 1.15. Para construirlo:

```bash
ollama create cibo -f cibo-config.modelfile
```

Luego pon `MODEL_NAME=cibo:latest` en tu `.env`.

## Uso

```bash
python main.py
```

Se abre una consola interactiva:

```
👤 Tú: cuánto es 8347 * 9562
🤖 CIBO: El resultado es 79.814.014

👤 Tú: ejecuta: print("hola")
🤖 CIBO: Codigo ejecutado. Salida:
hola
```

### Comandos

| Comando | Acción |
|---|---|
| `/help` | Ayuda y capacidades |
| `/tools` | Herramientas cargadas y veces usadas |
| `/models` | Modelos disponibles en Ollama |
| `/history` | Historial de la sesión |
| `/save` | Exporta la conversación a `data/conversations/` |
| `/clear` | Limpia pantalla e historial |
| `/exit` | Salir |

## Arquitectura

```
main.py                    Consola interactiva (bucle + comandos)
│
└── src/
    ├── core/
    │   ├── ollama_client.py   Cliente HTTP de Ollama (chat, streaming, historial)
    │   └── agent.py           Agente: detecta intención y ejecuta herramientas
    │
    ├── tools/
    │   ├── base.py            Clase abstracta Tool (run() envuelve errores y contadores)
    │   ├── calculator.py      Evaluación matemática con lista blanca de caracteres
    │   ├── code_executor.py   Python en subproceso: timeout 5s, imports peligrosos bloqueados
    │   └── web_search.py      (vacío, pendiente)
    │
    ├── agents/
    │   ├── base_agent.py      Interfaz común: generate() / is_available()
    │   ├── ollama_agent.py    Backend local
    │   ├── claude_agent.py    Backend Anthropic (opcional)
    │   └── gemini_agent.py    Backend Google (opcional)
    │
    ├── orchestrator/
    │   ├── router.py          Elige agente según sensibilidad, complejidad y modo
    │   └── coordinator.py     Une router, memoria y herramientas
    │
    ├── storage/
    │   └── vector_store.py    Memoria persistente con ChromaDB
    │
    └── security/
        ├── privacy.py         Modos paranoid / balanced / performance
        └── sanitizer.py       Bloqueo de datos sensibles y redacción de respuestas
```

### Cómo decide el agente

`Agent.process()` va en cascada, de lo más barato a lo más caro:

1. Mira si es una pregunta matemática, por palabras clave (`calcula`, `cuánto`, `multiplica`) o por patrones tipo `\d+ [+-*/] \d+`. Si lo es, extrae la expresión y llama a `Calculator` sin molestar al LLM.
2. Mira si le piden ejecutar código, por verbos como `ejecuta`, `corre` o `run`. Distingue "ejecuta este código" de "me gusta Python", que solo lo menciona.
3. Si no está claro, pregunta al LLM con el system prompt, los últimos 10 mensajes del historial y lo que haya recordado de la memoria. El modelo puede contestar con `<tool>Nombre</tool><params>{...}</params>`.
4. Si pidió una herramienta y la reconoce, la ejecuta.
5. Si no, devuelve la respuesta tal cual.

### Cómo decide el router

`AgentRouter.route()` pone la privacidad por delante de la potencia:

- En modo `paranoid` siempre va local, sin excepciones.
- Si detecta datos sensibles (tarjetas, contraseñas, tokens, números de la seguridad social) también va local.
- Si la tarea es simple, tipo saludos o definiciones, la resuelve en local y no gasta API.
- En modo `performance`, si la pregunta pide razonamiento complejo (`analiza`, `compara`, `evalúa`), tira de Claude si está disponible.
- En cualquier otro caso, local.

### Modos de privacidad

| Modo | Agentes | Internet | Memoria en la nube |
|---|---|---|---|
| `paranoid` | solo Ollama | ❌ | ❌ |
| `balanced` *(por defecto)* | Ollama + Claude | ✅ | ❌ |
| `performance` | Ollama + Claude + Gemini | ✅ | ✅ |

## Seguridad

`CodeExecutor` lanza el código en un subproceso con 5 segundos de timeout y bloquea por análisis estático los imports de `os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, `http`, `ftplib` y `smtplib`, además de `eval`, `exec`, `compile` y `open`.

Aclaro una cosa: eso es una barrera contra código que la líe sin querer, no un sandbox de verdad. No hay aislamiento a nivel de sistema operativo. Si algún día expongo esto a entrada de terceros habrá que meterlo en un contenedor.

`Calculator` valida los caracteres contra una lista blanca antes de evaluar y solo expone funciones de `math`.

`SecurityLayer` se aplica antes de cualquier salida a la nube y bloquea el envío entero si encuentra un patrón sensible.

## Tests

Scripts de comprobación manual en la raíz. Necesitan Ollama corriendo:

```bash
python test_simple.py        # diagnóstico de imports y conexión
python test_complete.py      # suite completa: cliente, herramientas, agente
python test_stress.py        # casos límite y uso realista
python test_debug_agent.py   # traza del agente ejecutando código
```

No son tests de `pytest`: se lanzan directamente e imprimen resultados por pantalla. La carpeta `tests/` la tengo reservada para cuando monte la suite automatizada.

## Estado del proyecto

En pausa indefinida desde febrero de 2026, por dos razones.

La primera es la GPU. Con 8 GB de VRAM te mueves en modelos de 7B u 8B cuantizados, y ahí se nota el techo enseguida: el modelo se lía con instrucciones de varios pasos, se inventa cosas y hay que sujetarlo con detección por palabras clave en vez de dejar que decida él. Buena parte del código que hay aquí existe precisamente para compensar eso. Los modelos que sí razonan bien no me caben en local, y montar la infraestructura para ir más allá se salía de lo que quería aprender.

La segunda es que esto se mueve muy rápido. Entre que empecé y lo dejé, salieron modelos mejores, Ollama cambió cosas y aparecieron librerías que resuelven de un plumazo lo que aquí está hecho a mano. Reescribirlo cada pocas semanas para ir detrás del estado del arte no era el objetivo.

Y el objetivo era aprender, que eso sí salió. Entender cómo se habla con un modelo por HTTP, por qué un LLM necesita herramientas externas para no inventarse los números, cómo se aísla la ejecución de código, qué es una base vectorial y para qué sirve, cómo se diseña una interfaz común para intercambiar backends. Todo eso está en el repo y funciona.

Así que lo dejo publicado como está. Si alguien lo mira buscando referencia de cómo se monta un asistente local con herramientas, le puede servir. No busques aquí una librería mantenida.

## Lo que funciona y lo que falta

Lo que funciona:

- La consola `main.py` con Ollama local, `Calculator` y `CodeExecutor`.
- Historial de sesión, exportación a JSON y los comandos de consola.

Lo que está a medias:

- `src/tools/web_search.py` está vacío, aunque `duckduckgo-search` y `beautifulsoup4` ya figuran en `requirements.txt`.
- `ClaudeAgent` trae como modelo por defecto `claude-3-5-sonnet-20241022`, que Anthropic retiró en octubre de 2025 y hoy devuelve 404. Hay que pasarle un modelo actual al construirlo. Es un buen ejemplo de lo que cuento arriba sobre la velocidad a la que se queda todo viejo.
- `Coordinator` y `AgentRouter` están escritos pero `main.py` todavía no los usa: la consola instancia `Agent` directamente, así que al multi-agente solo se llega importándolo desde código.
- La memoria vectorial (`use_memory=True`) es opcional y viene desactivada. Hacen falta `chromadb` y `sentence-transformers` instalados.
- `Agent.process()` lee de la memoria pero nunca escribe en ella sola. Hay que llamar a `save_to_memory()` a mano.
- El router busca los agentes por las claves `ollama_local` y `claude_api`, que salen de `BaseAgent.name`. Si añado un agente con otro nombre tendré que revisar eso.
- `requirements.txt` arrastra dependencias que aún no uso (`streamlit`, `discord.py`, `langchain`, `faiss-cpu`), de las interfaces que tengo pensadas.

Lo que llegué a planear y se queda sin hacer, por la pausa:

- Interfaz web con Streamlit y un bot de Discord.
- RAG sobre documentos locales, en `data/documents/`.
- Integración con Telegram y WhatsApp.

## Licencia

Proyecto personal, sin licencia definida. Todos los derechos reservados.
