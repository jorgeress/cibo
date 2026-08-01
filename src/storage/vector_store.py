"""
Sistema de memoria persistente con ChromaDB
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
        Guarda información en memoria
        
        Args:
            text: Texto a recordar
            metadata: Metadatos adicionales
            category: Categoría (general, user_info, preference, etc.)
        
        Returns:
            ID del documento guardado
        """
        # Genera ID único
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
        Recupera información relevante
        
        Args:
            query: Pregunta o tema
            n_results: Cantidad de resultados
            category: Filtrar por categoría
        
        Returns:
            Lista de resultados relevantes
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
        """Borra toda la memoria (CUIDADO)"""
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