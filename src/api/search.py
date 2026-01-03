"""Search API endpoints."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.models import DocumentStatus, DocumentType
from src.schemas import SearchResponse, SearchResult
from src.services.storage import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search documents",
    description="Full-text search across all documents",
)
async def search_documents(
    q: str = Query(..., min_length=1, description="Search query"),
    document_type: DocumentType | None = Query(None, alias="type"),
    status: DocumentStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> SearchResponse:
    """
    Search documents using full-text search.
    
    Supports:
    - Natural language queries
    - Filtering by document type and status
    - Date range filtering
    - Pagination
    """
    search_service = SearchService(session)
    
    results, total = await search_service.search(
        query=q,
        document_type=document_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    
    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                document_id=r["document_id"],
                filename=r["filename"],
                document_type=r["document_type"],
                snippet=r["snippet"],
                relevance_score=r["relevance_score"],
                upload_timestamp=r["upload_timestamp"],
            )
            for r in results
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/metadata",
    summary="Search in metadata fields",
    description="Search within extracted metadata fields",
)
async def search_metadata(
    field: str = Query(..., description="Metadata field to search"),
    value: str = Query(..., description="Value to search for"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Search within specific metadata fields (e.g., vendor_name, invoice_number)."""
    search_service = SearchService(session)
    
    results, total = await search_service.search_in_metadata(
        field=field,
        value=value,
        page=page,
        page_size=page_size,
    )
    
    return {
        "field": field,
        "value": value,
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/amount",
    summary="Search by amount range",
    description="Search documents by monetary amount",
)
async def search_by_amount(
    min_amount: float | None = Query(None, description="Minimum amount"),
    max_amount: float | None = Query(None, description="Maximum amount"),
    field: str = Query("total_amount", description="Amount field to search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Search documents by amount range (e.g., total_amount > 500)."""
    if min_amount is None and max_amount is None:
        return {"error": "Provide at least min_amount or max_amount"}
    
    search_service = SearchService(session)
    
    results, total = await search_service.search_by_amount_range(
        min_amount=min_amount,
        max_amount=max_amount,
        amount_field=field,
        page=page,
        page_size=page_size,
    )
    
    return {
        "min_amount": min_amount,
        "max_amount": max_amount,
        "field": field,
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/suggestions",
    summary="Get search suggestions",
    description="Get autocomplete suggestions based on partial input",
)
async def get_suggestions(
    q: str = Query(..., min_length=2, description="Partial search query"),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get search suggestions for autocomplete."""
    search_service = SearchService(session)
    
    suggestions = await search_service.get_search_suggestions(
        partial_query=q,
        limit=limit,
    )
    
    return {
        "query": q,
        "suggestions": suggestions,
    }
