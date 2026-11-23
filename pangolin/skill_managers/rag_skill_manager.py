#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from pathlib import Path
from ..core.exceptions import PangolinValueError, PangolinImportError
from ..core.interfaces import SkillManager, RAGComponent, RAGComponentAsync

LOGGER = logging.getLogger(__name__)

# bge-small-en-v1.5: 384 dims, ~67MB, truncates at 512 tokens.
# Prefixes are optional for this model. query_embed / passage_embed still
# matter if the model name changes to one that requires them.
_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_MODEL_DIM = 384
_COLLECTION = "skills"


class RAGSkillManager(SkillManager, RAGComponent, RAGComponentAsync):
    '''
    SkillManager whose skills() string is the chunks retrieved for this turn.
    Indexing is explicit. Retrieval overwrites the stash. It does not append.
    '''
    def __init__(self,
                 docs_folder: str | Path = Path.cwd().joinpath('skills'),
                 db_path: str | Path = Path.cwd().joinpath('db', 'chroma'),
                 cache_dir: str | Path = Path.cwd().joinpath('db', 'fastembed_cache'),
                 process_last_n_user_records: int = 1,
                 n_results: int = 4,
                 max_distance: float = 0.45,
                 max_chars: int = 6000,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 embed_batch: int = 64,
                 model_name: str =_MODEL_NAME,
                 model_dim: int = _MODEL_DIM,
                 collection_name: str = _COLLECTION
                 ):
        try:
            import fastembed
            import chromadb
        except ImportError:
            raise PangolinImportError('RAGSkillManager requires extra dependencies run pip install pangolin[rag]')
        
        self.skills_this_turn: str = ''
        self.docs_folder = Path(docs_folder)
        self.db_path = Path(db_path)
        self.cache_dir = Path(cache_dir)
        self.process_last_n_user_records = process_last_n_user_records
        self.n_results = n_results
        self.max_distance = max_distance
        self.max_chars = max_chars
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embed_batch = embed_batch
        self.model_name = model_name
        self.model_dim = model_dim
        self.collection_name = collection_name
        self.embed_model = self.model()
        self.db_client = chromadb.PersistentClient(path=str(self.db_path))
        self.db_collection = self.collection()

    def skills(self) -> str:
        return self.skills_this_turn

    def model(self):
        '''
            # Local embedder. fastembed runs an ONNX model on CPU. No API key.
    # First call downloads the weights once into cache_dir; after that
    # it is offline. Lazy so import and construction do not pay for it.
    #
    # Only _embed_docs and _embed_query touch this object. Docs go through
    # passage_embed, the query through query_embed. Some models need that
    # split. This one does not, but the calls stay so a swap does not silently
    # drop the prefixes.
    #
    # Another fastembed model: change _MODEL_NAME, set _MODEL_DIM to that
    # model's dim (TextEmbedding.list_supported_models()), delete db_path,
    # reindex. The collection metadata check will refuse a mismatch.
    #
    # An API, or any other library: do not put the client here. Replace
    # _embed_docs and _embed_query so they still return list[list[float]]
    # and list[float], point _MODEL_NAME and _MODEL_DIM at whatever you
    # actually called, delete db_path, and reindex. Old vectors are not
    comparable to new ones. This property can go.
    '''
        from fastembed import TextEmbedding
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        embed_model = TextEmbedding(model_name=self.model_name, cache_dir=str(self.cache_dir))
        if embed_model.embedding_size != self.model_dim:
            raise PangolinValueError(
                f'{self.model_name} reported dim {self.embed_model.embedding_size}, expected {self.model_dim}'
            )
        return embed_model

    def collection(self):
        self.db_path.mkdir(parents=True, exist_ok=True)
        try:
            col = self.db_client.get_collection(self.collection_name)
        except Exception:
            col = None
        if col is None:
            col = self.db_client.get_or_create_collection(
                self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embed_model": self.model_name,
                    "embed_dim": self.model_dim,
                },
            )
        else:
            meta = col.metadata or {}
            if meta.get("embed_model") != self.model_name or meta.get("embed_dim") != self.model_dim:
                raise PangolinValueError(
                    f'collection was indexed with {meta.get("embed_model")} '
                    f'dim={meta.get("embed_dim")}; this process is {self.model_name} '
                    f'dim={self.model_dim}. delete {self.db_path} and reindex.'
                )
        return col

    def _embed_docs(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.embed_model.passage_embed(texts)]

    def _embed_query(self, text: str) -> list[float]:
        return next(self.embed_model.query_embed(text)).tolist()

    def _format(self, hits: dict) -> str:
        docs = (hits.get("documents") or [[]])[0]
        metas = (hits.get("metadatas") or [[]])[0]
        dists = (hits.get("distances") or [[]])[0]
        blocks = []
        for doc, meta, dist in zip(docs, metas, dists):
            if not doc or dist is None or dist > self.max_distance:
                LOGGER.debug('dropping hit dist=%s source=%s', dist, (meta or {}).get("source"))
                continue
            source = (meta or {}).get("source", "unknown")
            blocks.append(f"source: {source}\n{doc}")
        text = "\n\n".join(blocks)
        if len(text) > self.max_chars:
            text = text[:self.max_chars] + "\n[truncated]"
        return text

    def _query_text(self, chat_history) -> str:
        texts = []
        for record in reversed(chat_history):
            if getattr(record, "role", None) != "user":
                continue
            parts = getattr(record, "content", None) or []
            if not parts:
                continue
            data = getattr(parts[0], "data", None) or {}
            text = data.get("text", "")
            if text and text.strip():
                texts.append(text.strip())
            if len(texts) >= self.process_last_n_user_records:
                break
        texts.reverse()
        return "\n".join(texts)

    def reload_skills(self) -> int:
        ''' Simple wipe and reload, only needs to be run once as long as the database storage persists and the source files have not changed. '''
        self.db_collection.delete(where={"source": {"$ne": ""}})
        if self.chunk_overlap >= self.chunk_size:
            raise PangolinValueError('chunk_overlap must be smaller than chunk_size')
        ids, docs, metas = [], [], []
        step = self.chunk_size - self.chunk_overlap
        for path in sorted(self.docs_folder.rglob("*.md")):
            raw = path.read_text(encoding="utf-8", errors="replace")
            for i, start in enumerate(range(0, max(len(raw), 1), step)):
                chunk = raw[start:start + self.chunk_size].strip()
                if not chunk:
                    continue
                ids.append(f"{path}:{i}")
                docs.append(chunk)
                metas.append({"source": str(path)})
                if start + self.chunk_size >= len(raw):
                    break
        if not ids:
            LOGGER.warning('index_docs found no markdown under %s', self.docs_folder)
            return 0
        for start in range(0, len(ids), self.embed_batch):
            stop = start + self.embed_batch
            vectors = self._embed_docs(docs[start:stop])
            self.db_collection.upsert(
                ids=ids[start:stop],
                embeddings=vectors,
                documents=docs[start:stop],
                metadatas=metas[start:stop],
            )
        LOGGER.info('indexed %s chunks from %s', len(ids), self.docs_folder)
        return len(ids)

    def retrieve_with_chat_history(self, chat_history):
        query = self._query_text(chat_history)
        if not query:
            self.skills_this_turn = ""
            return
        vec = self._embed_query(query)
        hits = self.db_collection.query(
            query_embeddings=[vec],
            n_results=self.n_results,
            include=["documents", "metadatas", "distances"],
        )
        self.skills_this_turn = self._format(hits)

    async def retrieve_with_chat_history_async(self, chat_history):
        query = self._query_text(chat_history)
        if not query:
            self.skills_this_turn = ""
            return
        vec = self._embed_query(query)
        hits = self.db_collection.query(
            query_embeddings=[vec],
            n_results=self.n_results,
            include=["documents", "metadatas", "distances"],
        )
        self.skills_this_turn = self._format(hits)
