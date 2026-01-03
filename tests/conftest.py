"""Pytest configuration and fixtures."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.database import Base
from src.models import Document, DocumentStatus, DocumentType, ExtractedMetadata


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
SYNC_TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Close the loop more gracefully
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
    except Exception:
        pass
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async database engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session


@pytest.fixture(scope="function")
def sync_engine():
    """Create sync database engine for tests."""
    engine = create_engine(SYNC_TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Create sync session for tests."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf(temp_dir: Path) -> Path:
    """Create a sample PDF file for testing."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    pdf_path = temp_dir / "sample.pdf"
    
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Invoice #12345")
    c.drawString(100, 730, "Date: 2024-01-15")
    c.drawString(100, 710, "Vendor: Acme Corporation")
    c.drawString(100, 690, "Total Amount: $1,234.56")
    c.save()
    
    return pdf_path


@pytest.fixture
def sample_image(temp_dir: Path) -> Path:
    """Create a sample image file for testing."""
    from PIL import Image, ImageDraw, ImageFont
    
    img_path = temp_dir / "sample.png"
    
    # Create image with text
    img = Image.new("RGB", (800, 600), color="white")
    draw = ImageDraw.Draw(img)
    
    # Add text
    draw.text((100, 100), "INVOICE", fill="black")
    draw.text((100, 150), "Invoice Number: INV-2024-001", fill="black")
    draw.text((100, 200), "Date: January 15, 2024", fill="black")
    draw.text((100, 250), "Total: $500.00", fill="black")
    
    img.save(img_path)
    return img_path


@pytest_asyncio.fixture
async def sample_document(async_session: AsyncSession) -> Document:
    """Create a sample document in the database."""
    document = Document(
        id=uuid4(),
        filename="test_document.pdf",
        original_filename="test_document.pdf",
        file_path="/tmp/test_document.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        document_type=DocumentType.INVOICE,
        ocr_confidence=0.95,
        raw_text="Invoice #12345\nDate: 2024-01-15\nTotal: $1,234.56",
    )
    async_session.add(document)
    await async_session.commit()
    await async_session.refresh(document)
    return document


@pytest_asyncio.fixture
async def sample_metadata(
    async_session: AsyncSession,
    sample_document: Document,
) -> ExtractedMetadata:
    """Create sample extracted metadata."""
    metadata = ExtractedMetadata(
        document_id=sample_document.id,
        document_type="invoice",
        data={
            "invoice_number": "12345",
            "date": "2024-01-15",
            "total_amount": 1234.56,
            "vendor_name": "Acme Corporation",
        },
        extraction_model="gpt-4o-mini",
        extraction_confidence=0.9,
    )
    async_session.add(metadata)
    await async_session.commit()
    return metadata
