import logging
import hashlib
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge_base import TranscriptDocument, TranscriptChunk
from app.services.chunking_service import get_chunking_service
from app.services.embedding_service import get_embedding_service, EmbeddingError, EmbeddingUnavailableError

logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunking_service = get_chunking_service()
        self.embedding_service = get_embedding_service()

    def _compute_content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _parse_transcript(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Parses a transcript file. 
        Assumes markdown format with optional frontmatter or title in the first few lines.
        Returns the full text and a dictionary of metadata.
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.error(f"Failed to read {file_path} with utf-8 encoding.")
            return "", {}

        metadata = {
            "source_path": str(file_path),
            "filename": file_path.name,
            "episode_title": file_path.stem.replace('_', ' ').replace('-', ' ').title()
        }

        # Simple extraction of title and guest if present at the top
        lines = content.split('\n')
        for line in lines[:10]:
            if line.startswith('# '):
                metadata['episode_title'] = line[2:].strip()
            elif line.lower().startswith('guest:'):
                metadata['guest'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('date:'):
                metadata['publication_date'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('url:'):
                metadata['source_url'] = line.split(':', 1)[1].strip()

        return content, metadata

    async def _process_document(self, file_path: Path, dry_run: bool = False) -> str:
        """Processes a single document. Returns a status string (skipped, updated, ingested, failed)."""
        content, metadata = self._parse_transcript(file_path)
        if not content:
            return "failed"

        content_hash = self._compute_content_hash(content)
        stable_doc_id = hashlib.md5(str(file_path.name).encode('utf-8')).hexdigest()

        # Check if document already exists
        result = await self.db.execute(select(TranscriptDocument).where(TranscriptDocument.stable_doc_id == stable_doc_id))
        existing_doc = result.scalars().first()

        if existing_doc:
            if existing_doc.content_hash == content_hash and existing_doc.status == "ingested":
                return "skipped"
            
            if not dry_run:
                # Update existing
                existing_doc.content_hash = content_hash
                existing_doc.status = "updated"
                existing_doc.episode_title = metadata.get("episode_title")
                existing_doc.guest = metadata.get("guest")
                existing_doc.publication_date = metadata.get("publication_date")
                existing_doc.source_url = metadata.get("source_url")
                existing_doc.source_metadata = metadata
                # Delete old chunks
                await self.db.execute(
                    TranscriptChunk.__table__.delete().where(TranscriptChunk.document_id == existing_doc.id)
                )
            doc_model = existing_doc
            status = "updated"
        else:
            doc_model = TranscriptDocument(
                stable_doc_id=stable_doc_id,
                episode_title=metadata.get("episode_title"),
                source_url=metadata.get("source_url"),
                guest=metadata.get("guest"),
                publication_date=metadata.get("publication_date"),
                content_hash=content_hash,
                source_path=metadata.get("source_path"),
                source_metadata=metadata,
                status="ingested"
            )
            if not dry_run:
                self.db.add(doc_model)
                await self.db.flush() # flush to get doc_model.id
            status = "ingested"

        if dry_run:
            return status

        # Chunk the text
        chunks = self.chunking_service.chunk_text(content, stable_doc_id)
        if not chunks:
            logger.warning(f"No chunks generated for {file_path}")
            doc_model.status = "failed"
            return "failed"

        # Embed the chunks
        texts_to_embed = [c.content for c in chunks]
        try:
            embeddings = self.embedding_service.embed_documents(texts_to_embed)
        except EmbeddingError as e:
            logger.error(f"Failed to embed document {file_path}: {e}")
            doc_model.status = "failed"
            return "failed"

        # Save chunks
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = TranscriptChunk(
                stable_chunk_id=chunk.stable_chunk_id,
                document_id=doc_model.id,
                chunk_index=chunk.metadata.chunk_index,
                content=chunk.content,
                embedding=embedding,
                embedding_model=self.embedding_service.model_id,
                start_char_offset=chunk.metadata.start_char_offset,
                end_char_offset=chunk.metadata.end_char_offset,
                speaker=chunk.metadata.speaker,
                timestamp_start=chunk.metadata.timestamp_start,
                timestamp_end=chunk.metadata.timestamp_end,
                token_count=chunk.metadata.token_count
            )
            self.db.add(db_chunk)

        doc_model.status = "ingested"
        return status

    async def run(self, source_path: str, dry_run: bool = False, full_reindex: bool = False) -> Dict[str, int]:
        """
        Run the ingestion pipeline on a directory or file.
        """
        path = Path(source_path)
        if not path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

        files_to_process = []
        if path.is_file():
            files_to_process.append(path)
        elif path.is_dir():
            # Process common transcript extensions
            for ext in ('*.md', '*.txt'):
                files_to_process.extend(path.rglob(ext))

        stats = {"processed": 0, "skipped": 0, "updated": 0, "failed": 0, "total": len(files_to_process)}
        
        if not files_to_process:
            logger.warning(f"No valid transcript files found in {source_path}")
            return stats

        if full_reindex and not dry_run:
            logger.info("Performing full re-index. Deleting all existing knowledge base data.")
            await self.db.execute(TranscriptChunk.__table__.delete())
            await self.db.execute(TranscriptDocument.__table__.delete())
            await self.db.commit()

        for file_path in files_to_process:
            try:
                status = await self._process_document(file_path, dry_run=dry_run)
                stats[status] += 1
                if status in ("ingested", "updated"):
                    stats["processed"] += 1
                
                if not dry_run and (stats["processed"] % 10 == 0):
                     await self.db.commit()
                     
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["failed"] += 1

        if not dry_run:
            await self.db.commit()

        return stats
