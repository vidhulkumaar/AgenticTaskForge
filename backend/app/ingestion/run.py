import asyncio
import argparse
import logging
from pathlib import Path

from app.db.session import AsyncSessionLocal
from app.ingestion.pipeline import IngestionPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_ingestion(source_path: str, dry_run: bool, full_reindex: bool):
    async with AsyncSessionLocal() as db:
        pipeline = IngestionPipeline(db)
        
        logger.info(f"Starting ingestion from {source_path}")
        if dry_run:
            logger.info("DRY RUN ENABLED - No changes will be saved to the database")
        if full_reindex:
            logger.warning("FULL RE-INDEX ENABLED - Existing knowledge base will be cleared")
            
        stats = await pipeline.run(source_path, dry_run=dry_run, full_reindex=full_reindex)
        
        logger.info("Ingestion complete. Statistics:")
        logger.info(f"  Total files found: {stats['total']}")
        logger.info(f"  Successfully processed: {stats['processed']}")
        logger.info(f"  Updated: {stats['updated']}")
        logger.info(f"  Skipped (unchanged): {stats['skipped']}")
        logger.info(f"  Failed: {stats['failed']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest transcripts into the knowledge base.")
    parser.add_argument("--source", type=str, required=True, help="Path to the transcript file or directory")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving to the database")
    parser.add_argument("--full-reindex", action="store_true", help="Delete existing knowledge base and re-index all documents")
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"Source path {source_path} does not exist.")
        exit(1)
        
    try:
        asyncio.run(run_ingestion(str(source_path), args.dry_run, args.full_reindex))
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        exit(1)
