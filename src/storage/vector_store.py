"""
Memoria que sobrevive al cierre del programa, con ChromaDB.

La idea es guardar frases y luego recuperarlas por significado, no por
palabras exactas. Si guardas "prefiero Python a Java" y luego preguntas
"que lenguaje me gusta", una busqueda de texto normal no encuentra nada
porque no comparten ni una palabra. Una base vectorial si: convierte cada
texto en una lista de numeros que representa lo que significa, y busca los
mas cercanos.

Hay dos colecciones separadas a proposito. `cibo_memory` guarda lo general y
`user_context` lo que es del usuario, para poder consultar solo una de las
dos o borrar la del usuario sin tocar el resto.

La telemetria de ChromaDB va desactivada: seria contradictorio que un
asistente que presume de local mandara estadisticas a un servidor.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
from datetime import datetime
import os


class VectorMemory:
    """Memoria vectorial persistente para CIBO"""
    
    def __init__(self, persist_directory: str = "./data/vector_db"):
        """Inicializa ChromaDB"""
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False  # Privacidad
            )
        )
        
        # Colección para memoria general
        self.memory_collection = self.client.get_or_create_collection(
            name="cibo_memory",
            metadata={"description": "Memoria general de CIBO"}
        )
        
        # Colección para contexto de usuario
        self.user_context = self.client.get_or_create_collection(
            name="user_context",
            metadata={"description": "Información sobre el usuario"}
        )
    
    def remember(self, text: str, metadata: Optional[Dict] = None, category: str = "general") -> str:
        """
        Guarda algo en la memoria.

        Args:
            text: lo que hay que recordar
            metadata: datos extra que quieras adjuntar
            category: "user_info" va a la coleccion del usuario, cualquier
                      otra cosa a la general

        Returns:
            El ID del documento, o None si fallo
        """
        # El ID sale de un hash del propio texto, asi guardar dos veces lo
        # mismo no crea duplicados: cae en el mismo ID
        text_hash = hashlib.md5(text.encode()).hexdigest()
        doc_id = f"{category}_{text_hash[:8]}"
        
        # Metadatos
        meta = metadata or {}
        meta.update({
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "source": "conversation"
        })
        
        # Decide colección
        collection = self.user_context if category == "user_info" else self.memory_collection
        
        # Guarda
        try:
            collection.add(
                documents=[text],
                metadatas=[meta],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Error guardando memoria: {e}")
            return None
    
    def recall(self, query: str, n_results: int = 3, category: Optional[str] = None) -> List[Dict]:
        """
        Busca lo mas parecido a la pregunta.

        Consulta las dos colecciones, junta los resultados y los ordena por
        `distance`: cuanto mas bajo, mas se parece. Como cada coleccion
        devuelve hasta n_results por su cuenta, al final se recorta.

        Args:
            query: sobre que buscar
            n_results: cuantos devolver, ya ordenados
            category: para mirar solo una categoria

        Returns:
            Lista de dicts con 'text', 'metadata' y 'distance'
        """
        # Filtra por categoría si se especifica
        where_filter = {"category": category} if category else None
        
        # Busca en ambas colecciones
        results = []
        
        for collection in [self.memory_collection, self.user_context]:
            try:
                res = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_filter
                )
                
                if res['documents'] and res['documents'][0]:
                    for i, doc in enumerate(res['documents'][0]):
                        results.append({
                            'text': doc,
                            'metadata': res['metadatas'][0][i],
                            'distance': res['distances'][0][i]
                        })
            except Exception as e:
                continue
        
        # Ordena por relevancia
        results.sort(key=lambda x: x['distance'])
        
        return results[:n_results]
    
    def forget(self, doc_id: str):
        """Elimina un recuerdo"""
        try:
            self.memory_collection.delete(ids=[doc_id])
        except:
            pass
        
        try:
            self.user_context.delete(ids=[doc_id])
        except:
            pass
    
    def clear_all(self):
        """
        Borra la memoria entera. No hay vuelta atras.

        Elimina las dos colecciones y las vuelve a crear vacias. Ojo: las
        recrea sin los metadatos de descripcion que tenian al principio.
        """
        self.client.delete_collection("cibo_memory")
        self.client.delete_collection("user_context")
        
        # Recrea colecciones
        self.memory_collection = self.client.create_collection("cibo_memory")
        self.user_context = self.client.create_collection("user_context")
    
    def get_stats(self) -> Dict:
        """Estadísticas de la memoria"""
        return {
            "total_memories": self.memory_collection.count(),
            "user_context_items": self.user_context.count()
        }