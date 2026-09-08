-- SkillForge AI Database Initialization Script
-- Enables the pgvector extension

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify pgvector is active
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
