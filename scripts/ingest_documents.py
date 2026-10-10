"""Ingest all knowledge base documents into PostgreSQL."""

import asyncio
import logging
from pathlib import Path

from infrastructure.database.session import get_engine
from infrastructure.knowledge.ingest import ingest_starter_corpus
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)


async def main():
    engine = get_engine()
    docs_dir = Path("infrastructure/knowledge/documents").resolve()
    print(f"Reading documents from {docs_dir}...")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        counts = await ingest_starter_corpus(session, docs_dir)
        await session.commit()
        print("Successfully ingested documents:")
        for doc_id, n_chunks in counts.items():
            print(f"  - {doc_id}: {n_chunks} chunks")


if __name__ == "__main__":
    asyncio.run(main())
