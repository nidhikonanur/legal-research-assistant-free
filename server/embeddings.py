import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import nltk
nltk.download('punkt', quiet=True)
try:
    nltk.download('punkt_tab', quiet=True)
except Exception:
    pass
from nltk.tokenize import sent_tokenize

DEFAULT_CHUNK_SIZE = 800  # chars

def chunk_text(txt, chunk_size=DEFAULT_CHUNK_SIZE, overlap=200):
    if not txt:
        return []
    sentences = sent_tokenize(txt)
    chunks = []
    current = ''
    for s in sentences:
        if len(current) + len(s) + 1 <= chunk_size:
            current = current + ' ' + s if current else s
        else:
            chunks.append(current.strip())
            # start with overlap if needed
            current = s
    if current:
        chunks.append(current.strip())
    # merge small tail chunks
    merged = []
    for c in chunks:
        if merged and len(merged[-1]) < chunk_size//3:
            merged[-1] = merged[-1] + ' ' + c
        else:
            merged.append(c)
    return merged

class EmbeddingIndex:
    def __init__(self, persist_directory='vector_store'):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = self._create_client()
        self.collection = None
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def _create_client(self):
        # Support both the newer PersistentClient API and older Settings-based clients.
        persistent_client = getattr(chromadb, 'PersistentClient', None)
        if persistent_client is not None:
            return persistent_client(path=self.persist_directory)
        return chromadb.Client(
            Settings(chroma_db_impl='duckdb+parquet', persist_directory=self.persist_directory)
        )

    def load_if_exists(self):
        # create or get collection
        try:
            self.collection = self.client.get_collection(name='cases')
        except Exception:
            self.collection = self.client.create_collection(name='cases')

    def add_documents(self, texts, metadatas=None, ids_prefix='doc'):
        if not texts:
            return
        self.load_if_exists()
        start_id = self._next_id()
        ids = [f"{ids_prefix}_{i}" for i in range(start_id, start_id + len(texts))]
        # embed
        embs = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        docs = [{'id': ids[i], 'embedding': embs[i], 'metadata': metadatas[i] if metadatas else {}, 'text': texts[i]} for i in range(len(texts))]
        # chroma expects lists
        ids_list = [d['id'] for d in docs]
        metadatas_list = [d['metadata'] for d in docs]
        documents = [d['text'] for d in docs]
        embeddings = embs.tolist()
        # add to collection
        self.collection.add(ids=ids_list, metadatas=metadatas_list, documents=documents, embeddings=embeddings)
        persist = getattr(self.client, 'persist', None)
        if callable(persist):
            persist()

    def _next_id(self):
        try:
            return self.collection.count() if self.collection else 0
        except Exception:
            return 0

    def similarity_search(self, query, k=4):
        self.load_if_exists()
        q_emb = self.model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=['metadatas', 'documents', 'distances'],
        )
        docs = []
        for i in range(len(results['ids'][0])):
            docs.append({'id': results['ids'][0][i], 'metadata': results['metadatas'][0][i], 'text': results['documents'][0][i], 'distance': results['distances'][0][i]})
        return docs
