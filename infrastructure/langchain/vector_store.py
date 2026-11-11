import os
import json
import math
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from application.interfaces import IVectorStoreManager
from utils.logger import logger
from config.config import settings

# Attempt LangChain production imports
try:
    from langchain_core.documents import Document
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    LANGCHAIN_PROD_AVAILABLE = True
except ImportError:
    LANGCHAIN_PROD_AVAILABLE = False
    logger.warning("[VectorStore] LangChain components missing or partially loaded. Bootstrapping mathematical vector fallback engine.")

class VectorStoreManager(IVectorStoreManager):
    def __init__(self):
        self.openai_api_key = settings.azure.openai_api_key
        self.vector_store_path = settings.langchain.vector_store_dir
        self.use_azure_openai = bool(self.openai_api_key)
        
        self.local_db_file = self.vector_store_path / "vector_db.json"
        self._initialize_db()

    def _initialize_db(self):
        if not self.local_db_file.exists():
            with open(self.local_db_file, "w") as f:
                json.dump([], f)

    def _read_local_db(self) -> List[Dict[str, Any]]:
        try:
            with open(self.local_db_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_local_db(self, data: List[Dict[str, Any]]):
        with open(self.local_db_file, "w") as f:
            json.dump(data, f, indent=2)

    def index_evidence(self, case_id: str, content: str, metadata: Dict[str, Any]) -> None:
        logger.info(f"[VectorStore] Indexing Evidence for Case {case_id}. Size: {len(content)} chars.")
        
        # 1. Production LangChain workflow
        if self.use_azure_openai and LANGCHAIN_PROD_AVAILABLE:
            try:
                embeddings = OpenAIEmbeddings(
                    openai_api_key=self.openai_api_key,
                    model=settings.azure.openai_embeddings_deployment or "text-embedding-ada-002"
                )
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                docs = text_splitter.split_documents([Document(page_content=content, metadata=metadata)])
                
                # Check if FAISS index exists
                faiss_path = self.vector_store_path / f"faiss_index_{case_id}"
                if faiss_path.exists():
                    db = FAISS.load_local(str(faiss_path), embeddings, allow_dangerous_deserialization=True)
                    db.add_documents(docs)
                else:
                    db = FAISS.from_documents(docs, embeddings)
                db.save_local(str(faiss_path))
                logger.info(f"[VectorStore] Successfully updated FAISS index for case {case_id}.")
            except Exception as e:
                logger.error(f"[VectorStore] Production LangChain index failed: {e}. Defaulting to mathematical DB.")

        # 2. Local Document Indexing
        db = self._read_local_db()
        db.append({
            "case_id": case_id,
            "content": content,
            "metadata": metadata
        })
        self._write_local_db(db)

    def retrieve_evidence(self, case_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        logger.info(f"[VectorStore] Retrieving contexts for Case {case_id}. Query: '{query}'")
        
        # 1. Query production LangChain index
        if self.use_azure_openai and LANGCHAIN_PROD_AVAILABLE:
            try:
                embeddings = OpenAIEmbeddings(
                    openai_api_key=self.openai_api_key,
                    model=settings.azure.openai_embeddings_deployment or "text-embedding-ada-002"
                )
                faiss_path = self.vector_store_path / f"faiss_index_{case_id}"
                if faiss_path.exists():
                    db = FAISS.load_local(str(faiss_path), embeddings, allow_dangerous_deserialization=True)
                    docs = db.similarity_search(query, k=limit)
                    logger.info(f"[VectorStore] Retrieved {len(docs)} documents from FAISS index.")
                    return [{"content": d.page_content, "metadata": d.metadata, "case_id": case_id} for d in docs]
            except Exception as e:
                logger.error(f"[VectorStore] Production retrieval failed: {e}. Falling back to mathematical TF-IDF engine.")

        # 2. Local Mathematical TF-IDF Vectorizer + Cosine Similarity implementation
        db = self._read_local_db()
        docs = [doc for doc in db if doc["case_id"] == case_id]
        if not docs:
            return []

        # Simple tokenizer helper
        def tokenize(text: str) -> List[str]:
            return [w for w in text.lower().replace(".", " ").replace(",", " ").split() if len(w) > 2]

        query_tokens = tokenize(query)
        if not query_tokens:
            return docs[:limit]

        # Calculate TF-IDF matrix
        # Vocabulary definition
        vocab = list(set(tokenize(" ".join([d["content"] for d in docs] + [query]))))
        vocab_index = {word: i for i, word in enumerate(vocab)}

        # Inverse Document Frequency (IDF)
        num_docs = len(docs)
        df = {word: 0 for word in vocab}
        for d in docs:
            tokens = set(tokenize(d["content"]))
            for t in tokens:
                if t in df:
                    df[t] += 1

        idf = {}
        for word, count in df.items():
            idf[word] = math.log((1 + num_docs) / (1 + count)) + 1

        # Vector representation for query
        query_vector = np.zeros(len(vocab))
        for t in query_tokens:
            if t in vocab_index:
                query_vector[vocab_index[t]] += 1
        query_vector = query_vector * np.array([idf[w] for w in vocab])

        # Vector representation for documents
        doc_vectors = []
        for d in docs:
            vector = np.zeros(len(vocab))
            tokens = tokenize(d["content"])
            for t in tokens:
                if t in vocab_index:
                    vector[vocab_index[t]] += 1
            vector = vector * np.array([idf[w] for w in vocab])
            doc_vectors.append(vector)

        # Compute Cosine Similarity
        def cosine_similarity(v1, v2) -> float:
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))

        scored_docs = []
        for idx, d in enumerate(docs):
            similarity = cosine_similarity(query_vector, doc_vectors[idx])
            
            # Boost score for exact match in metadata attributes (e.g. searching "handgun")
            meta_str = str(d.get("metadata", {})).lower()
            boost = sum(0.3 for t in query_tokens if t in meta_str)
            
            scored_docs.append((similarity + boost, d))

        # Sort by similarity descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Return top matches
        results = [item[1] for item in scored_docs if item[0] > 0][:limit]
        
        # If no similarity score above zero, return the first few documents by default
        if not results:
            return docs[:limit]
            
        return results
