"""
Búsqueda web. Sin implementar.

Este archivo se quedó vacío. La idea era una herramienta más, heredando de
Tool igual que Calculator y CodeExecutor, que buscara con duckduckgo-search
y limpiara el HTML de los resultados con beautifulsoup4. Las dos librerías
están en requirements.txt esperando, pero el proyecto se paró antes.

Si alguien quiere retomarlo, el esqueleto sería este:

    class WebSearch(Tool):
        def get_description(self) -> str:
            ...
        def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
            ...

Y habría que darlo de alta en dos sitios: en el __init__.py del paquete y en
la lista de herramientas de main.py. Ojo también con el modo de privacidad,
que esta herramienta sale a internet y en modo paranoid no debería ni
cargarse.
"""
