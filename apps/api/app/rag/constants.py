"""RAG constants (Amendment A1 §6.13; code, not environment, as IMD-29; Proposed values)."""

from typing import Final

RAG_EMBED_DIM: Final = 768  # fixed by migration 0007
RAG_EMBED_BATCH: Final = 32
RAG_CHUNK_MAX_CHARS: Final = 800
RAG_CHUNK_OVERLAP_CHARS: Final = 120
RAG_QUERY_MAX_CHARS: Final = 1000
RAG_GUIDE_CANDIDATES: Final = 20
RAG_TOP_K_GUIDE: Final = 6
RAG_MMR_LAMBDA: Final = 0.7
RAG_MAX_CHUNKS_PER_DOCUMENT: Final = 2
RAG_TOP_K_PLACE: Final = 6
RAG_MAX_PASSAGES: Final = 12
GUIDE_MIN_CHARS: Final = 300
GUIDE_MAX_CHARS: Final = 6000
