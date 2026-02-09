-- PostgreSQL initialization script
-- Run automatically when PostgreSQL container starts

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Set ownership and search path
ALTER EXTENSION vector OWNER TO postgres;
SET search_path TO public;
