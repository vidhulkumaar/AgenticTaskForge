"""
Chunking service for splitting transcripts into semantically useful passages.

Preserves paragraph and speaker boundaries where practical.
Uses configurable chunk size (in tokens) and overlap.
"""
import hashlib
import logging
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Lazy-loaded tokenizer
_tokenizer = None


def _get_tokenizer():
    """Get a tiktoken tokenizer for token counting."""
    global _tokenizer
    if _tokenizer is None:
        try:
            import tiktoken
            _tokenizer = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not available, falling back to word-based estimation")
            _tokenizer = "fallback"
    return _tokenizer


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    tokenizer = _get_tokenizer()
    if tokenizer == "fallback":
        # Rough estimate: ~4 chars per token
        return len(text) // 4
    return len(tokenizer.encode(text))


@dataclass
class ChunkMetadata:
    """Metadata for a single chunk."""
    chunk_index: int
    start_char_offset: int
    end_char_offset: int
    token_count: int
    speaker: Optional[str] = None
    timestamp_start: Optional[str] = None
    timestamp_end: Optional[str] = None


@dataclass
class Chunk:
    """A chunk of text with metadata."""
    content: str
    metadata: ChunkMetadata
    stable_chunk_id: str = ""


class ChunkingService:
    """
    Splits transcript text into semantically useful passages.
    
    Configuration:
        chunk_size: Target number of tokens per chunk (default: 700)
        chunk_overlap: Number of overlapping tokens between chunks (default: 100)
    
    The service:
    - Preserves paragraph boundaries where practical
    - Preserves speaker boundaries (lines starting with "Speaker:" patterns)
    - Avoids empty chunks and duplicate adjacent chunks
    - Assigns deterministic chunk IDs
    """

    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 100):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _detect_speaker(self, text: str) -> Optional[str]:
        """Detect speaker from a line of text. Returns speaker name or None."""
        # Common transcript speaker patterns:
        # "Speaker Name:" or "**Speaker Name:**" or "[Speaker Name]"
        patterns = [
            r'^(?:\*\*)?([A-Za-z\s\.\-\']+?)(?:\*\*)?:\s',  # Name: text
            r'^\[([A-Za-z\s\.\-\']+?)\]\s',                   # [Name] text
        ]
        for pattern in patterns:
            match = re.match(pattern, text.strip())
            if match:
                return match.group(1).strip()
        return None

    def _detect_timestamp(self, text: str) -> Optional[str]:
        """Detect timestamp from text. Returns timestamp string or None."""
        # Common patterns: [00:00:00], (00:00), 00:00:00
        patterns = [
            r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]',
            r'\((\d{1,2}:\d{2}(?::\d{2})?)\)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs while preserving meaningful boundaries."""
        # Split on double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\s*\n', text)
        # Filter out empty paragraphs
        return [p.strip() for p in paragraphs if p.strip()]

    def _generate_chunk_id(self, doc_id: str, chunk_index: int, content: str) -> str:
        """Generate a deterministic, stable chunk ID."""
        # Use document ID + chunk index for stability
        id_source = f"{doc_id}::chunk::{chunk_index}"
        return hashlib.sha256(id_source.encode('utf-8')).hexdigest()[:32]

    def chunk_text(self, text: str, document_id: str) -> List[Chunk]:
        """
        Split text into chunks with configurable size and overlap.
        
        Args:
            text: The full transcript text to chunk.
            document_id: Stable document identifier for generating chunk IDs.
            
        Returns:
            List of Chunk objects with metadata.
        """
        if not text or not text.strip():
            return []

        paragraphs = self._split_into_paragraphs(text)
        if not paragraphs:
            return []

        chunks: List[Chunk] = []
        current_chunk_parts: List[str] = []
        current_tokens = 0
        current_start_offset = 0
        chunk_index = 0
        current_speaker = None
        current_timestamp = None

        # Track character offsets in original text
        char_pos = 0

        for para in paragraphs:
            # Find paragraph position in original text
            para_start = text.find(para, char_pos)
            if para_start == -1:
                para_start = char_pos
            para_end = para_start + len(para)

            para_tokens = count_tokens(para)
            
            # Detect speaker and timestamp
            speaker = self._detect_speaker(para)
            timestamp = self._detect_timestamp(para)
            if speaker:
                current_speaker = speaker
            if timestamp:
                current_timestamp = timestamp

            # If single paragraph exceeds chunk_size, split it further
            if para_tokens > self.chunk_size:
                # Flush current buffer if not empty
                if current_chunk_parts:
                    chunk_text = "\n\n".join(current_chunk_parts)
                    if chunk_text.strip():
                        chunk_id = self._generate_chunk_id(document_id, chunk_index, chunk_text)
                        chunks.append(Chunk(
                            content=chunk_text,
                            metadata=ChunkMetadata(
                                chunk_index=chunk_index,
                                start_char_offset=current_start_offset,
                                end_char_offset=para_start,
                                token_count=count_tokens(chunk_text),
                                speaker=current_speaker,
                                timestamp_start=current_timestamp,
                            ),
                            stable_chunk_id=chunk_id
                        ))
                        chunk_index += 1
                    current_chunk_parts = []
                    current_tokens = 0

                # Split the large paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_parts: List[str] = []
                sub_tokens = 0
                sub_start = para_start

                for sent in sentences:
                    sent_tokens = count_tokens(sent)
                    if sub_tokens + sent_tokens > self.chunk_size and sub_parts:
                        chunk_text = " ".join(sub_parts)
                        if chunk_text.strip():
                            chunk_id = self._generate_chunk_id(document_id, chunk_index, chunk_text)
                            chunks.append(Chunk(
                                content=chunk_text,
                                metadata=ChunkMetadata(
                                    chunk_index=chunk_index,
                                    start_char_offset=sub_start,
                                    end_char_offset=sub_start + len(chunk_text),
                                    token_count=count_tokens(chunk_text),
                                    speaker=current_speaker,
                                    timestamp_start=current_timestamp,
                                ),
                                stable_chunk_id=chunk_id
                            ))
                            chunk_index += 1
                        
                        # Apply overlap: keep last few sentences
                        overlap_parts: List[str] = []
                        overlap_tokens = 0
                        for s in reversed(sub_parts):
                            s_tokens = count_tokens(s)
                            if overlap_tokens + s_tokens <= self.chunk_overlap:
                                overlap_parts.insert(0, s)
                                overlap_tokens += s_tokens
                            else:
                                break
                        sub_parts = overlap_parts
                        sub_tokens = overlap_tokens
                        sub_start = sub_start + len(chunk_text) - sum(len(s) for s in overlap_parts)
                    
                    sub_parts.append(sent)
                    sub_tokens += sent_tokens

                # Remaining sentences go to current_chunk_parts for next chunk
                if sub_parts:
                    current_chunk_parts = [" ".join(sub_parts)]
                    current_tokens = sub_tokens
                    current_start_offset = sub_start
                continue

            # Check if adding this paragraph would exceed chunk_size
            if current_tokens + para_tokens > self.chunk_size and current_chunk_parts:
                # Create chunk from current buffer
                chunk_text = "\n\n".join(current_chunk_parts)
                if chunk_text.strip():
                    chunk_id = self._generate_chunk_id(document_id, chunk_index, chunk_text)
                    chunks.append(Chunk(
                        content=chunk_text,
                        metadata=ChunkMetadata(
                            chunk_index=chunk_index,
                            start_char_offset=current_start_offset,
                            end_char_offset=para_start,
                            token_count=count_tokens(chunk_text),
                            speaker=current_speaker,
                            timestamp_start=current_timestamp,
                        ),
                        stable_chunk_id=chunk_id
                    ))
                    chunk_index += 1

                # Apply overlap: keep trailing text from previous chunk
                if self.chunk_overlap > 0 and current_chunk_parts:
                    overlap_parts: List[str] = []
                    overlap_tokens = 0
                    for part in reversed(current_chunk_parts):
                        part_tokens = count_tokens(part)
                        if overlap_tokens + part_tokens <= self.chunk_overlap:
                            overlap_parts.insert(0, part)
                            overlap_tokens += part_tokens
                        else:
                            break
                    current_chunk_parts = overlap_parts
                    current_tokens = overlap_tokens
                    current_start_offset = para_start - sum(len(p) for p in overlap_parts)
                else:
                    current_chunk_parts = []
                    current_tokens = 0
                    current_start_offset = para_start

            if not current_chunk_parts:
                current_start_offset = para_start

            current_chunk_parts.append(para)
            current_tokens += para_tokens
            char_pos = para_end

        # Flush remaining buffer
        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts)
            if chunk_text.strip():
                chunk_id = self._generate_chunk_id(document_id, chunk_index, chunk_text)
                chunks.append(Chunk(
                    content=chunk_text,
                    metadata=ChunkMetadata(
                        chunk_index=chunk_index,
                        start_char_offset=current_start_offset,
                        end_char_offset=len(text),
                        token_count=count_tokens(chunk_text),
                        speaker=current_speaker,
                        timestamp_start=current_timestamp,
                    ),
                    stable_chunk_id=chunk_id
                ))

        # Deduplicate adjacent chunks with identical content
        if len(chunks) > 1:
            deduped = [chunks[0]]
            for c in chunks[1:]:
                if c.content != deduped[-1].content:
                    deduped.append(c)
            chunks = deduped

        return chunks


def get_chunking_service() -> ChunkingService:
    """Factory function to create a ChunkingService from application settings."""
    from app.core.config import settings
    return ChunkingService(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
