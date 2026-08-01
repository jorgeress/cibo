from .base_agent import BaseAgent
from .ollama_agent import OllamaAgent

# Cloud agents (opcionales)
try:
    from .claude_agent import ClaudeAgent
    CLAUDE_AVAILABLE = True
except:
    CLAUDE_AVAILABLE = False
    ClaudeAgent = None

try:
    from .gemini_agent import GeminiAgent
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False
    GeminiAgent = None

__all__ = ['BaseAgent', 'OllamaAgent', 'ClaudeAgent', 'GeminiAgent']