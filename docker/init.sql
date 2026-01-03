-- PostgreSQL initialization script
-- Creates necessary extensions for full-text search

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom text search configuration (optional)
-- This can be customized for specific languages or domains

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE document_ingestion TO postgres;

-- Create indexes for common queries (will be created by SQLAlchemy, but included for reference)
-- These are created after tables exist via Alembic migrations
