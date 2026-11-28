"""RAG constants (Amendment A1 §6.13; code, not environment, as IMD-29; Proposed values)."""

from typing import Final

RAG_EMBED_DIM: Final = 768  # fixed by migration 0007
RAG_EMBED_BATCH: Final = 32
# D3: Gemini counts each text of a batch against its per-minute quota, so batches are paced, a 429
# is waited out and retried, and one embedding run stops after this budget (the rest stays queued).
RAG_EMBED_PACE_S: Final = 2.0
RAG_EMBED_BACKOFF_S: Final = 10.0  # doubled after each 429 in a row, or Retry-After if longer
RAG_EMBED_BUDGET_S: Final = 90.0  # inside IMPORT_TIMEOUT_S with the fetch steps
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
