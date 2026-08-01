# CIBO

Asistente de IA **local y privado** construido sobre [Ollama](https://ollama.com/). CIBO ejecuta un LLM en tu propia GPU, decide por su cuenta cuándo usar herramientas (calculadora, ejecutor de código) y opcionalmente enruta consultas a modelos cloud sólo cuando tú lo permites.

El principio de diseño es simple: **por defecto nada sale de tu máquina**. Las APIs cloud son opcionales, y una capa de seguridad bloquea el envío de datos sensibles aunque estén activadas.

---

## Características

- **100% local por defecto** — el modelo corre en Ollama, sin llamadas a internet.
- **Sistema de herramientas** — el agente detecta la intención y usa `Calculator` para matemáticas exactas (los LLM alucinan con números) o `CodeExecutor` para correr Python en sandbox.
- **Memoria vectorial persistente** — ChromaDB para recordar información entre sesiones (opcional).
- **Multi-agente** — interfaz común para Ollama, Claude y Gemini, con un router que elige cuál usar.
- **Modos de privacidad** — `paranoid` / `balanced` / `performance` controlan qué agentes y herramientas se permiten.
- **Sanitización de datos** — detecta API keys, contraseñas, tarjetas y SSN antes de que puedan enviarse a cloud, y redacta IPs y emails de las respuestas.

---

## Requisitos

| Requisito | Versión / nota |
|---|---|
| Python | 3.10+ (desarrollado con 3.13) |
| Ollama | corriendo en `localhost:11434` |
| Modelo | `llama3.1:8b` o el modelo propio `cibo:latest` |
| GPU | recomendada (probado en RTX 4060 8 GB), funciona en CPU más lento |

---

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

Arranca Ollama y descarga el modelo base:

```bash
ollama serve
ollama pull llama3.1:8b
```

### Modelo propio (opcional)

`cibo-config.modelfile` define la personalidad e identidad de CIBO junto a sus parámetros de rendimiento (contexto de 8192 tokens, temperatura 0.7, `repeat_penalty` 1.15). Para construirlo:

```bash
ollama create cibo -f cibo-config.modelfile
```

Luego pon `MODEL_NAME=cibo:latest` en tu `.env`.

---

## Uso

```bash
python main.py
```

Se abre una consola interactiva:

```
👤 Tú: cuánto es 8347 * 9562
🤖 CIBO: El resultado es 79.813.014

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

---

## Arquitectura

```
main.py                    Consola interactiva (REPL + comandos)
│
└── src/
    ├── core/
    │   ├── ollama_client.py   Cliente HTTP de Ollama (chat, streaming, historial)
    │   └── agent.py           Agente: detecta intención y ejecuta herramientas
    │
    ├── tools/
    │   ├── base.py            Clase abstracta Tool (run() envuelve errores y contadores)
    │   ├── calculator.py      Evaluación matemática segura con whitelist
    │   ├── code_executor.py   Python en subproceso: timeout 5s, imports peligrosos bloqueados
    │   └── web_search.py      (vacío — pendiente)
    │
    ├── agents/
    │   ├── base_agent.py      Interfaz común: generate() / is_available()
    │   ├── ollama_agent.py    Backend local
    │   ├── claude_agent.py    Backend Anthropic (opcional)
    │   └── gemini_agent.py    Backend Google (opcional)
    │
    ├── orchestrator/
    │   ├── router.py          Elige agente según sensibilidad, complejidad y modo
    │   └── coordinator.py     Une router + memoria + herramientas
    │
    ├── storage/
    │   └── vector_store.py    Memoria persistente con ChromaDB
    │
    └── security/
        ├── privacy.py         Modos paranoid / balanced / performance
        └── sanitizer.py       Bloqueo de datos sensibles y redacción de respuestas
```

### Cómo decide el agente

`Agent.process()` sigue una cascada, de lo más barato a lo más caro:

1. **Detección matemática** — palabras clave (`calcula`, `cuánto`, `multiplica`…) o patrones `\d+ [+-*/] \d+`. Extrae la expresión y llama a `Calculator` directamente, sin pasar por el LLM.
2. **Detección de código** — verbos de ejecución (`ejecuta`, `corre`, `run`). Distingue "ejecuta este código" de "me gusta Python", que sólo lo menciona.
3. **Consulta al LLM** — si no es obvio, se envía el system prompt + historial reciente (últimos 10 mensajes) + memoria relevante. El modelo puede responder con `<tool>Nombre</tool><params>{...}</params>`.
4. **Ejecución de la herramienta** que el modelo pidió, si la reconoce.
5. **Respuesta directa** en cualquier otro caso.

### Cómo decide el router

`AgentRouter.route()` prioriza privacidad sobre potencia:

- Modo `paranoid` → siempre local, sin excepciones.
- Datos sensibles detectados (tarjetas, contraseñas, tokens, SSN) → siempre local.
- Tarea simple (saludos, definiciones) → local, no vale la pena gastar API.
- Modo `performance` + razonamiento complejo (`analiza`, `compara`, `evalúa`) → Claude, si está disponible.
- Cualquier otro caso → local.

### Modos de privacidad

| Modo | Agentes | Internet | Memoria cloud |
|---|---|---|---|
| `paranoid` | sólo Ollama | ❌ | ❌ |
| `balanced` *(por defecto)* | Ollama + Claude | ✅ | ❌ |
| `performance` | Ollama + Claude + Gemini | ✅ | ✅ |

---

## Seguridad

**`CodeExecutor`** ejecuta en subproceso con timeout de 5 s y bloquea por análisis estático los imports de `os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, `http`, `ftplib`, `smtplib`, además de `eval`, `exec`, `compile` y `open`. Es una barrera contra código accidentalmente destructivo, **no un sandbox real**: no hay aislamiento a nivel de sistema operativo. No lo expongas a entrada no confiable sin añadir un contenedor.

**`Calculator`** valida caracteres contra una whitelist antes de evaluar y expone sólo funciones de `math`.

**`SecurityLayer`** se aplica antes de cualquier salida a cloud y bloquea el envío completo si detecta un patrón sensible.

---

## Tests

Scripts de verificación manual en la raíz (requieren Ollama corriendo):

```bash
python test_simple.py        # diagnóstico de imports y conexión
python test_complete.py      # suite completa: cliente, herramientas, agente
python test_stress.py        # casos límite y uso realista
python test_debug_agent.py   # traza del agente con ejecución de código
```

No son tests de `pytest`: se ejecutan directamente e imprimen resultados. `tests/` está reservado para la suite automatizada.

---

## Estado actual y limitaciones conocidas

Proyecto en desarrollo activo. Lo que funciona y lo que no, sin adornos:

**Funciona**
- Consola `main.py` con Ollama local, `Calculator` y `CodeExecutor`.
- Historial de sesión, exportación a JSON, comandos de consola.

**Parcial o pendiente**
- `src/tools/web_search.py` está vacío pese a que `duckduckgo-search` y `beautifulsoup4` figuran en `requirements.txt`.
- `Coordinator` y `AgentRouter` están implementados pero **`main.py` no los usa todavía**: la consola instancia `Agent` directamente. El sistema multi-agente sólo es accesible importándolo desde código.
- La memoria vectorial (`use_memory=True`) es opcional y está desactivada por defecto; `chromadb` y `sentence-transformers` deben estar instalados.
- `Agent.process()` consulta la memoria pero nunca escribe en ella automáticamente — hay que llamar a `save_to_memory()` a mano.
- El router referencia agentes por las claves `ollama_local` y `claude_api`, derivadas de `BaseAgent.name`. Añadir un agente con otro nombre exige revisar esas claves.
- `requirements.txt` incluye dependencias aún no utilizadas (`streamlit`, `discord.py`, `langchain`, `faiss-cpu`) correspondientes a las interfaces previstas.

**Previsto**
- Interfaz web con Streamlit y bot de Discord.
- RAG sobre documentos locales (`data/documents/`).
- Integración con Telegram / WhatsApp.

---

## Licencia

Proyecto personal, sin licencia definida. Todos los derechos reservados.
