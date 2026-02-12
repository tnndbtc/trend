-- ============================================================================
-- Trend Intelligence Platform - PostgreSQL Database Schema
-- ============================================================================
-- This schema defines the relational database structure for storing trends,
-- topics, and processed items from various sources.
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for additional crypto functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE trend_state AS ENUM (
    'emerging',
    'viral',
    'sustained',
    'declining',
    'dead'
);

CREATE TYPE source_type AS ENUM (
    'reddit',
    'hackernews',
    'twitter',
    'youtube',
    'google_news',
    'bbc',
    'reuters',
    'ap_news',
    'al_jazeera',
    'guardian',
    'rss',
    'custom'
);

CREATE TYPE category_type AS ENUM (
    'Technology',
    'Politics',
    'Entertainment',
    'Sports',
    'Science',
    'Business',
    'Health',
    'World News',
    'Environment',
    'Education',
    'Other'
);

CREATE TYPE processing_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'skipped'
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Topics Table
-- A topic is a cluster of related items
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    category category_type NOT NULL,
    sources source_type[] NOT NULL DEFAULT '{}',
    item_count INTEGER NOT NULL DEFAULT 0,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    keywords TEXT[] DEFAULT '{}',

    -- Engagement metrics (stored as JSONB for flexibility)
    total_engagement JSONB NOT NULL DEFAULT '{"upvotes": 0, "downvotes": 0, "comments": 0, "shares": 0, "views": 0, "score": 0.0}',

    -- Timestamps
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    -- Indexes
    CONSTRAINT topics_item_count_check CHECK (item_count >= 0)
);

CREATE INDEX idx_topics_category ON topics(category);
CREATE INDEX idx_topics_language ON topics(language);
CREATE INDEX idx_topics_first_seen ON topics(first_seen DESC);
CREATE INDEX idx_topics_last_updated ON topics(last_updated DESC);
CREATE INDEX idx_topics_keywords ON topics USING GIN(keywords);
CREATE INDEX idx_topics_metadata ON topics USING GIN(metadata);

-- Trends Table
-- A trend is a ranked, analyzed topic with state tracking
CREATE TABLE trends (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    key_points TEXT[] DEFAULT '{}',
    category category_type NOT NULL,
    state trend_state NOT NULL DEFAULT 'emerging',
    score FLOAT NOT NULL,
    sources source_type[] NOT NULL DEFAULT '{}',
    item_count INTEGER NOT NULL DEFAULT 0,
    velocity FLOAT NOT NULL DEFAULT 0.0,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    keywords TEXT[] DEFAULT '{}',
    related_trend_ids UUID[] DEFAULT '{}',

    -- Engagement metrics
    total_engagement JSONB NOT NULL DEFAULT '{"upvotes": 0, "downvotes": 0, "comments": 0, "shares": 0, "views": 0, "score": 0.0}',

    -- Timestamps
    first_seen TIMESTAMPTZ NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    peak_engagement_at TIMESTAMPTZ,

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    -- Indexes and constraints
    CONSTRAINT trends_rank_check CHECK (rank > 0),
    CONSTRAINT trends_score_check CHECK (score >= 0),
    CONSTRAINT trends_velocity_check CHECK (velocity >= 0)
);

CREATE INDEX idx_trends_topic_id ON trends(topic_id);
CREATE INDEX idx_trends_rank ON trends(rank);
CREATE INDEX idx_trends_category ON trends(category);
CREATE INDEX idx_trends_state ON trends(state);
CREATE INDEX idx_trends_score ON trends(score DESC);
CREATE INDEX idx_trends_language ON trends(language);
CREATE INDEX idx_trends_first_seen ON trends(first_seen DESC);
CREATE INDEX idx_trends_last_updated ON trends(last_updated DESC);
CREATE INDEX idx_trends_keywords ON trends USING GIN(keywords);
CREATE INDEX idx_trends_metadata ON trends USING GIN(metadata);
CREATE INDEX idx_trends_composite_rank_score ON trends(rank, score DESC);

-- Processed Items Table
-- Items after normalization and initial processing
CREATE TABLE processed_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source source_type NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    title_normalized TEXT NOT NULL,
    description TEXT,
    content TEXT,
    content_normalized TEXT,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    author VARCHAR(255),
    category category_type,

    -- Engagement metrics
    metrics JSONB NOT NULL DEFAULT '{"upvotes": 0, "downvotes": 0, "comments": 0, "shares": 0, "views": 0, "score": 0.0}',

    -- Timestamps
    published_at TIMESTAMPTZ NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    -- Unique constraint on source + source_id
    CONSTRAINT processed_items_source_unique UNIQUE (source, source_id)
);

CREATE INDEX idx_processed_items_source ON processed_items(source);
CREATE INDEX idx_processed_items_source_id ON processed_items(source_id);
CREATE INDEX idx_processed_items_language ON processed_items(language);
CREATE INDEX idx_processed_items_category ON processed_items(category);
CREATE INDEX idx_processed_items_published_at ON processed_items(published_at DESC);
CREATE INDEX idx_processed_items_collected_at ON processed_items(collected_at DESC);
CREATE INDEX idx_processed_items_metadata ON processed_items USING GIN(metadata);

-- Many-to-Many: Topics to Items
CREATE TABLE topic_items (
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES processed_items(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (topic_id, item_id)
);

CREATE INDEX idx_topic_items_topic_id ON topic_items(topic_id);
CREATE INDEX idx_topic_items_item_id ON topic_items(item_id);

-- ============================================================================
-- HELPER TABLES
-- ============================================================================

-- Plugin Health Tracking
CREATE TABLE plugin_health (
    name VARCHAR(100) PRIMARY KEY,
    is_healthy BOOLEAN NOT NULL DEFAULT true,
    last_run_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_error TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    total_runs INTEGER NOT NULL DEFAULT 0,
    success_rate FLOAT NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT plugin_health_success_rate_check CHECK (success_rate >= 0.0 AND success_rate <= 1.0)
);

-- Pipeline Execution History
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status processing_status NOT NULL,
    items_collected INTEGER NOT NULL DEFAULT 0,
    items_processed INTEGER NOT NULL DEFAULT 0,
    items_deduplicated INTEGER NOT NULL DEFAULT 0,
    topics_created INTEGER NOT NULL DEFAULT 0,
    trends_created INTEGER NOT NULL DEFAULT 0,
    duration_seconds FLOAT,
    errors TEXT[] DEFAULT '{}',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update last_updated timestamp on topics
CREATE OR REPLACE FUNCTION update_topics_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_topics_updated
    BEFORE UPDATE ON topics
    FOR EACH ROW
    EXECUTE FUNCTION update_topics_timestamp();

-- Update last_updated timestamp on trends
CREATE OR REPLACE FUNCTION update_trends_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_trends_updated
    BEFORE UPDATE ON trends
    FOR EACH ROW
    EXECUTE FUNCTION update_trends_timestamp();

-- Automatically update topic item_count when items are added/removed
CREATE OR REPLACE FUNCTION update_topic_item_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE topics
        SET item_count = item_count + 1
        WHERE id = NEW.topic_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE topics
        SET item_count = item_count - 1
        WHERE id = OLD.topic_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_topic_items_count
    AFTER INSERT OR DELETE ON topic_items
    FOR EACH ROW
    EXECUTE FUNCTION update_topic_item_count();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Trending Topics View (for quick access to active trends)
CREATE OR REPLACE VIEW trending_topics AS
SELECT
    t.id,
    t.topic_id,
    t.title,
    t.summary,
    t.category,
    t.state,
    t.rank,
    t.score,
    t.velocity,
    t.item_count,
    t.sources,
    t.keywords,
    t.first_seen,
    t.last_updated,
    (t.total_engagement->>'score')::float AS engagement_score
FROM trends t
WHERE t.state IN ('emerging', 'viral', 'sustained')
ORDER BY t.rank, t.score DESC;

-- Popular Items by Source
CREATE OR REPLACE VIEW popular_items_by_source AS
SELECT
    source,
    category,
    COUNT(*) as item_count,
    AVG((metrics->>'score')::float) as avg_score,
    MAX(published_at) as latest_published
FROM processed_items
WHERE published_at > NOW() - INTERVAL '7 days'
GROUP BY source, category
ORDER BY item_count DESC;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to clean up old processed items
CREATE OR REPLACE FUNCTION cleanup_old_items(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processed_items
    WHERE collected_at < NOW() - (days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get top trends by category
CREATE OR REPLACE FUNCTION get_top_trends_by_category(
    p_category category_type DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_date_from TIMESTAMPTZ DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    rank INTEGER,
    title VARCHAR(500),
    summary TEXT,
    score FLOAT,
    state trend_state,
    category category_type
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.rank,
        t.title,
        t.summary,
        t.score,
        t.state,
        t.category
    FROM trends t
    WHERE
        (p_category IS NULL OR t.category = p_category)
        AND (p_date_from IS NULL OR t.first_seen >= p_date_from)
    ORDER BY t.rank, t.score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANTS (Adjust based on your user setup)
-- ============================================================================

-- Grant permissions to trend_user (if it exists)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trend_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trend_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trend_user;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE topics IS 'Clusters of related content items';
COMMENT ON TABLE trends IS 'Ranked and analyzed topics with state tracking';
COMMENT ON TABLE processed_items IS 'Normalized items from data sources';
COMMENT ON TABLE topic_items IS 'Many-to-many relationship between topics and items';
COMMENT ON TABLE plugin_health IS 'Health monitoring for data collection plugins';
COMMENT ON TABLE pipeline_runs IS 'Execution history of processing pipelines';
