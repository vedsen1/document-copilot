"""
Docling-based document chunking for 10-K markdown files.

Converts each filing's markdown back into a DoclingDocument, then applies
HybridChunker with an OpenAI-compatible tokenizer so chunk boundaries align
exactly with text-embedding-3-small's token space.

Usage:
    from ingest.chunking import build_chunker, build_converter, chunk_document

    chunker   = build_chunker()    # once per process
    converter = build_converter()  # once per process

    chunks = chunk_document(markdown_text, chunker, converter)
"""
from __future__ import annotations

# Target chunk size.  text-embedding-3-small hard limit is 8 191 tokens;
# 512 keeps retrieval granular and avoids mid-table splits on dense filings.
CHUNK_MAX_TOKENS = 512


def build_chunker():
    """
    Return a reusable HybridChunker wired to text-embedding-3-small's tokenizer.

    HybridChunker applies tokenization-aware refinements on top of docling's
    hierarchical chunker: merges small sibling nodes and splits overlong ones so
    every output chunk fits within CHUNK_MAX_TOKENS.

    Called once per process — the chunker holds no per-document state.
    """
    import tiktoken
    from docling.chunking import HybridChunker
    from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

    # cl100k_base is the encoding used by text-embedding-3-small
    enc = tiktoken.encoding_for_model("text-embedding-3-small")
    tokenizer = OpenAITokenizer(tokenizer=enc, max_tokens=CHUNK_MAX_TOKENS)
    return HybridChunker(
        tokenizer=tokenizer,
        max_tokens=CHUNK_MAX_TOKENS,
        merge_peers=True,
    )


def build_converter():
    """
    Return a DocumentConverter for markdown → DoclingDocument conversion.

    For MD input docling uses a lightweight text pipeline with no ML models,
    so this is cheap and safe to create once at startup and reuse per filing.
    """
    from docling.document_converter import DocumentConverter

    return DocumentConverter()


def chunk_document(markdown_text: str, chunker, converter) -> list[dict]:
    """
    Chunk one filing's markdown using docling's HybridChunker.

    The markdown produced by convert_to_markdown.py is fed back through
    DocumentConverter (MD input, no model inference) to recover the
    DoclingDocument structure, then chunked natively.

    Each returned dict has:
        text           – raw chunk text (stored in document_chunks.text)
        embed_text     – context-enriched text with heading path prepended
                         (sent to OpenAI; richer context improves retrieval)
        section        – innermost heading label, capped at 256 chars
        chunk_index    – 0-based position within this document
        chunk_metadata – dict for the JSONB column; 'headings' is the full
                         ancestor heading path list
    """
    from docling.datamodel.base_models import InputFormat

    result = converter.convert_string(
        markdown_text, format=InputFormat.MD, name="doc.md"
    )
    dl_doc = result.document

    chunks: list[dict] = []
    for idx, chunk in enumerate(chunker.chunk(dl_doc=dl_doc)):
        embed_text = chunker.contextualize(chunk=chunk)
        headings: list[str] = list(chunk.meta.headings) if chunk.meta.headings else []
        section = headings[-1][:256] if headings else None
        chunks.append(
            {
                "text": chunk.text,
                "embed_text": embed_text,
                "section": section,
                "chunk_index": idx,
                "chunk_metadata": {"headings": headings},
            }
        )
    return chunks
