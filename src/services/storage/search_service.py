"""Full-text search service using PostgreSQL."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


class SearchService:
    """
    Full-text search service using PostgreSQL TSVECTOR.
    
    Enables high-speed text search across all documents.
    """

    def __init__(self, session: AsyncSession):
        """Initialize search service with database session."""
        self.session = session

    async def search(
        self,
        query: str,
        document_type: DocumentType | None = None,
        status: DocumentStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Perform full-text search on documents.
        
        Args:
            query: Search query string
            document_type: Filter by document type
            status: Filter by status
            date_from: Filter by upload date (from)
            date_to: Filter by upload date (to)
            page: Page number
            page_size: Results per page
            
        Returns:
            Tuple of (search results, total count)
        """
        if not query or not query.strip():
            return [], 0

        # Build the search query using plainto_tsquery for natural language
        # or to_tsquery for advanced syntax
        search_query = """
            SELECT 
                d.id,
                d.filename,
                d.document_type,
                d.status,
                d.upload_timestamp,
                d.ocr_confidence,
                ts_rank(d.text_search_vector, query) as rank,
                ts_headline(
                    'english',
                    d.raw_text,
                    query,
                    'MaxWords=50, MinWords=20, StartSel=<mark>, StopSel=</mark>'
                ) as snippet
            FROM 
                documents d,
                plainto_tsquery('english', :query) query
            WHERE 
                d.text_search_vector @@ query
        """

        params: dict[str, Any] = {"query": query}
        count_conditions = "d.text_search_vector @@ plainto_tsquery('english', :query)"

        # Add filters
        if document_type:
            search_query += " AND d.document_type = :doc_type"
            count_conditions += " AND d.document_type = :doc_type"
            params["doc_type"] = document_type.value

        if status:
            search_query += " AND d.status = :status"
            count_conditions += " AND d.status = :status"
            params["status"] = status.value

        if date_from:
            search_query += " AND d.upload_timestamp >= :date_from"
            count_conditions += " AND d.upload_timestamp >= :date_from"
            params["date_from"] = date_from

        if date_to:
            search_query += " AND d.upload_timestamp <= :date_to"
            count_conditions += " AND d.upload_timestamp <= :date_to"
            params["date_to"] = date_to

        # Order by relevance rank
        search_query += " ORDER BY rank DESC"

        # Add pagination
        search_query += " LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        # Execute search
        result = await self.session.execute(text(search_query), params)
        rows = result.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM documents d
            WHERE {count_conditions}
        """
        count_result = await self.session.execute(text(count_query), params)
        total = count_result.scalar_one()

        # Format results
        search_results = []
        for row in rows:
            search_results.append({
                "document_id": row.id,
                "filename": row.filename,
                "document_type": row.document_type,
                "status": row.status,
                "upload_timestamp": row.upload_timestamp,
                "relevance_score": float(row.rank),
                "snippet": row.snippet,
            })

        logger.info(f"Search for '{query}' returned {len(search_results)} results (total: {total})")
        return search_results, total

    async def search_in_metadata(
        self,
        field: str,
        value: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Search within JSONB metadata fields.
        
        Args:
            field: JSONB field to search (e.g., 'vendor_name')
            value: Value to search for
            page: Page number
            page_size: Results per page
            
        Returns:
            Tuple of (results, total count)
        """
        # Use JSONB containment operator for flexible matching
        search_query = """
            SELECT 
                d.id,
                d.filename,
                d.document_type,
                d.status,
                d.upload_timestamp,
                em.data
            FROM 
                documents d
            JOIN 
                extracted_metadata em ON d.id = em.document_id
            WHERE 
                em.data->>:field ILIKE :value
            ORDER BY d.upload_timestamp DESC
            LIMIT :limit OFFSET :offset
        """

        params = {
            "field": field,
            "value": f"%{value}%",
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        result = await self.session.execute(text(search_query), params)
        rows = result.fetchall()

        # Get total count
        count_query = """
            SELECT COUNT(*) FROM extracted_metadata em
            WHERE em.data->>:field ILIKE :value
        """
        count_result = await self.session.execute(
            text(count_query),
            {"field": field, "value": f"%{value}%"},
        )
        total = count_result.scalar_one()

        results = []
        for row in rows:
            results.append({
                "document_id": row.id,
                "filename": row.filename,
                "document_type": row.document_type,
                "status": row.status,
                "upload_timestamp": row.upload_timestamp,
                "extracted_data": row.data,
            })

        return results, total

    async def search_by_amount_range(
        self,
        min_amount: float | None = None,
        max_amount: float | None = None,
        amount_field: str = "total_amount",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Search documents by monetary amount range.
        
        Args:
            min_amount: Minimum amount
            max_amount: Maximum amount
            amount_field: JSONB field containing the amount
            page: Page number
            page_size: Results per page
            
        Returns:
            Tuple of (results, total count)
        """
        conditions = []
        params: dict[str, Any] = {
            "field": amount_field,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        if min_amount is not None:
            conditions.append("(em.data->>:field)::numeric >= :min_amount")
            params["min_amount"] = min_amount

        if max_amount is not None:
            conditions.append("(em.data->>:field)::numeric <= :max_amount")
            params["max_amount"] = max_amount

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        search_query = f"""
            SELECT 
                d.id,
                d.filename,
                d.document_type,
                d.status,
                d.upload_timestamp,
                em.data
            FROM 
                documents d
            JOIN 
                extracted_metadata em ON d.id = em.document_id
            WHERE 
                em.data ? :field AND {where_clause}
            ORDER BY (em.data->>:field)::numeric DESC
            LIMIT :limit OFFSET :offset
        """

        result = await self.session.execute(text(search_query), params)
        rows = result.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM extracted_metadata em
            WHERE em.data ? :field AND {where_clause}
        """
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        count_result = await self.session.execute(text(count_query), count_params)
        total = count_result.scalar_one()

        results = []
        for row in rows:
            results.append({
                "document_id": row.id,
                "filename": row.filename,
                "document_type": row.document_type,
                "status": row.status,
                "upload_timestamp": row.upload_timestamp,
                "extracted_data": row.data,
            })

        return results, total

    async def get_search_suggestions(
        self,
        partial_query: str,
        limit: int = 10,
    ) -> list[str]:
        """
        Get search suggestions based on partial input.
        
        Args:
            partial_query: Partial search query
            limit: Maximum suggestions to return
            
        Returns:
            List of suggested search terms
        """
        # Extract unique words from documents matching the partial query
        query = """
            SELECT DISTINCT unnest(string_to_array(raw_text, ' ')) as word
            FROM documents
            WHERE raw_text ILIKE :pattern
            LIMIT :limit
        """

        result = await self.session.execute(
            text(query),
            {"pattern": f"%{partial_query}%", "limit": limit * 5},
        )
        words = [row.word for row in result.fetchall()]

        # Filter and clean suggestions
        suggestions = []
        seen = set()
        for word in words:
            cleaned = word.strip(".,!?;:\"'()[]{}").lower()
            if (
                len(cleaned) >= 3
                and cleaned.startswith(partial_query.lower())
                and cleaned not in seen
            ):
                suggestions.append(cleaned)
                seen.add(cleaned)
            if len(suggestions) >= limit:
                break

        return suggestions
