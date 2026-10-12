import asyncio
import os
import glob
from app.db.session import AsyncSessionLocal
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import get_embedding_service
from app.models.knowledge_base import TranscriptDocument, TranscriptChunk

async def main():
    embedder = get_embedding_service()
    chunker = ChunkingService()
    
    transcripts_dir = "data/transcripts"
    markdown_files = glob.glob(os.path.join(transcripts_dir, "*.md"))
    
    async with AsyncSessionLocal() as db:
        for file_path in markdown_files:
            filename = os.path.basename(file_path)
            print(f"Processing {filename}...")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            import hashlib
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            stable_doc_id = hashlib.md5(filename.encode()).hexdigest()
            base_name = filename.replace(".md", "").replace("-", " ").title()

            existing_doc = await db.execute(
                __import__("sqlalchemy").select(TranscriptDocument)
                .where(TranscriptDocument.stable_doc_id == stable_doc_id)
            )
            if existing_doc.scalar_one_or_none():
                print(f"Skipping {filename}, already ingested.")
                continue

            doc = TranscriptDocument(
                stable_doc_id=stable_doc_id,
                episode_title=base_name,
                guest=base_name,
                source_path=file_path,
                content_hash=content_hash
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            
            chunks = chunker.chunk_text(content, str(doc.id))
            print(f"Generated {len(chunks)} chunks for {filename}")
            
            texts_to_embed = [c.content for c in chunks]
            embeddings = await embedder.embed_documents(texts_to_embed)
            
            for i, chunk_data in enumerate(chunks):
                stable_chunk_id = f"{doc.id}_{i}"
                db_chunk = TranscriptChunk(
                    stable_chunk_id=stable_chunk_id,
                    document_id=doc.id,
                    chunk_index=i,
                    content=chunk_data.content,
                    embedding=embeddings[i],
                    embedding_model=embedder.model_id,
                    start_char_offset=chunk_data.metadata.start_char_offset,
                    end_char_offset=chunk_data.metadata.end_char_offset
                )
                db.add(db_chunk)
            
            await db.commit()
            print(f"Successfully ingested {filename}")

if __name__ == "__main__":
    asyncio.run(main())
