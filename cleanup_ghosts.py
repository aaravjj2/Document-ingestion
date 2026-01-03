
import asyncio
from uuid import UUID
from src.core.database import get_async_session_context
from src.services.storage import DocumentRepository
from src.models import DocumentType

async def cleanup_ghosts():
    async with get_async_session_context() as session:
        repo = DocumentRepository(session)
        # Fetch all documents (pagination hack for loop)
        docs, _ = await repo.list_documents(page_size=100)
        
        ghosts = [
            d for d in docs 
            if d.document_type == DocumentType.UNKNOWN 
            and d.ocr_confidence == 0.0
        ]
        
        print(f"Found {len(ghosts)} ghost documents.")
        
        for doc in ghosts:
            print(f"Deleting ghost document: {doc.id} ({doc.filename})")
            await repo.delete_document(doc.id)
        
        await session.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_ghosts())
