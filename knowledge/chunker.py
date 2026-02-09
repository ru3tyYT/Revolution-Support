"""Document chunking utilities with overlap and token counting."""

import re
from dataclasses import dataclass
from typing import List, Optional, Iterator
import tiktoken


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    chunk_size: int = 1000
    chunk_overlap: int = 200
    separator: str = "\n"
    min_chunk_size: int = 100
    max_chunks: Optional[int] = None


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    content: str
    index: int
    token_count: int
    start_pos: int
    end_pos: int
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextChunker:
    """Smart text chunking with overlap support."""

    # Tokenizer cache
    _encoders = {}

    def __init__(
        self, config: Optional[ChunkConfig] = None, encoding_name: str = "cl100k_base"
    ):
        """Initialize the text chunker.

        Args:
            config: Chunking configuration
            encoding_name: Tokenizer encoding name (cl100k_base for GPT-4)
        """
        self.config = config or ChunkConfig()
        self.encoding_name = encoding_name
        self._encoder = self._get_encoder(encoding_name)

    def _get_encoder(self, encoding_name: str):
        """Get or create a tokenizer encoder."""
        if encoding_name not in self._encoders:
            try:
                self._encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
            except Exception:
                # Fallback to approximate token counting
                self._encoders[encoding_name] = None
        return self._encoders[encoding_name]

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self._encoder:
            return len(self._encoder.encode(text))
        else:
            # Approximate: ~4 characters per token for English
            return len(text) // 4

    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[TextChunk]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        if metadata is None:
            metadata = {}

        chunks = []
        separator = self.config.separator

        # Split by separator first
        if separator in text:
            sections = text.split(separator)
        else:
            # No separator, split by sentences
            sections = self._split_sentences(text)

        current_chunk = []
        current_size = 0
        chunk_index = 0
        current_pos = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            section_tokens = self.count_tokens(section)

            # If single section is larger than chunk size, split it
            if section_tokens > self.config.chunk_size:
                # Add current chunk if exists
                if current_chunk:
                    chunk_text = separator.join(current_chunk)
                    chunks.append(
                        self._create_chunk(
                            chunk_text, chunk_index, current_pos, metadata
                        )
                    )
                    chunk_index += 1
                    current_pos += len(chunk_text) + len(separator)

                    if self.config.max_chunks and chunk_index >= self.config.max_chunks:
                        break

                # Split large section
                large_chunks = self._chunk_large_section(section, metadata)
                for chunk in large_chunks:
                    chunk.index = chunk_index
                    chunks.append(chunk)
                    chunk_index += 1
                    current_pos = chunk.end_pos

                    if self.config.max_chunks and chunk_index >= self.config.max_chunks:
                        break

                current_chunk = []
                current_size = 0
                continue

            # Check if adding this section would exceed chunk size
            if current_size + section_tokens > self.config.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = separator.join(current_chunk)
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, current_pos, metadata)
                )
                chunk_index += 1
                current_pos += len(chunk_text) + len(separator)

                if self.config.max_chunks and chunk_index >= self.config.max_chunks:
                    break

                # Start new chunk with overlap
                overlap_size = 0
                overlap_sections = []

                # Add previous sections for overlap
                for prev_section in reversed(current_chunk):
                    prev_tokens = self.count_tokens(prev_section)
                    if overlap_size + prev_tokens <= self.config.chunk_overlap:
                        overlap_sections.insert(0, prev_section)
                        overlap_size += prev_tokens
                    else:
                        break

                current_chunk = overlap_sections + [section]
                current_size = overlap_size + section_tokens
            else:
                current_chunk.append(section)
                current_size += section_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = separator.join(current_chunk)
            token_count = self.count_tokens(chunk_text)

            # Only add if meets minimum size
            if token_count >= self.config.min_chunk_size:
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, current_pos, metadata)
                )

        return chunks

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        metadata: dict,
    ) -> TextChunk:
        """Create a text chunk."""
        return TextChunk(
            content=content,
            index=index,
            token_count=self.count_tokens(content),
            start_pos=start_pos,
            end_pos=start_pos + len(content),
            metadata=metadata.copy(),
        )

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _chunk_large_section(self, section: str, metadata: dict) -> List[TextChunk]:
        """Chunk a section that's larger than chunk_size."""
        chunks = []
        words = section.split()
        chunk_index = 0
        pos = 0

        while words and (
            not self.config.max_chunks or chunk_index < self.config.max_chunks
        ):
            current_words = []
            current_tokens = 0

            while words and current_tokens < self.config.chunk_size:
                word = words[0]
                word_tokens = self.count_tokens(word + " ")

                if (
                    current_tokens + word_tokens > self.config.chunk_size
                    and current_words
                ):
                    break

                current_words.append(words.pop(0))
                current_tokens += word_tokens

            if current_words:
                chunk_text = " ".join(current_words)
                chunks.append(
                    TextChunk(
                        content=chunk_text,
                        index=chunk_index,
                        token_count=current_tokens,
                        start_pos=pos,
                        end_pos=pos + len(chunk_text),
                        metadata=metadata.copy(),
                    )
                )
                pos += len(chunk_text)
                chunk_index += 1

            # Add overlap
            if words and self.config.chunk_overlap > 0:
                overlap_words = []
                overlap_tokens = 0

                for word in reversed(current_words):
                    word_tokens = self.count_tokens(word + " ")
                    if overlap_tokens + word_tokens <= self.config.chunk_overlap:
                        overlap_words.insert(0, word)
                        overlap_tokens += word_tokens
                    else:
                        break

                words = overlap_words + words

        return chunks

    def chunk_markdown(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> List[TextChunk]:
        """Chunk markdown text, respecting headers.

        Args:
            text: Markdown text
            metadata: Optional metadata

        Returns:
            List of chunks with header context preserved
        """
        if metadata is None:
            metadata = {}

        chunks = []
        lines = text.split("\n")
        current_section = []
        current_headers = []
        chunk_index = 0
        pos = 0

        for line in lines:
            # Track headers
            if line.startswith("#"):
                # Save current section if exists
                if current_section:
                    section_text = "\n".join(current_section)
                    section_chunks = self.chunk_text(section_text, metadata)

                    for chunk in section_chunks:
                        chunk.index = chunk_index
                        chunk.metadata["headers"] = current_headers.copy()
                        chunks.append(chunk)
                        chunk_index += 1

                    pos += len(section_text) + 1

                # Update headers
                header_level = len(line) - len(line.lstrip("#"))
                current_headers = current_headers[: header_level - 1]
                current_headers.append(line.strip())
                current_section = [line]
            else:
                current_section.append(line)

        # Handle final section
        if current_section:
            section_text = "\n".join(current_section)
            section_chunks = self.chunk_text(section_text, metadata)

            for chunk in section_chunks:
                chunk.index = chunk_index
                chunk.metadata["headers"] = current_headers.copy()
                chunks.append(chunk)
                chunk_index += 1

        return chunks

    def chunk_by_paragraphs(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> List[TextChunk]:
        """Chunk text by paragraphs.

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of paragraph-based chunks
        """
        if metadata is None:
            metadata = {}

        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        pos = 0

        for paragraph in paragraphs:
            para_tokens = self.count_tokens(paragraph)

            if current_tokens + para_tokens > self.config.chunk_size and current_chunk:
                # Save chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, pos, metadata)
                )
                chunk_index += 1
                pos += len(chunk_text) + 2

                if self.config.max_chunks and chunk_index >= self.config.max_chunks:
                    break

                current_chunk = [paragraph]
                current_tokens = para_tokens
            else:
                current_chunk.append(paragraph)
                current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            token_count = self.count_tokens(chunk_text)
            if token_count >= self.config.min_chunk_size:
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, pos, metadata)
                )

        return chunks
