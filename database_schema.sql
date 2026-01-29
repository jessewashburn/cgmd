-- ========================================
-- Classical Guitar Music Database Schema
-- Optimized for Search & Performance
-- ========================================

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS work_search_index;
DROP TABLE IF EXISTS work_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS works;
DROP TABLE IF EXISTS composer_aliases;
DROP TABLE IF EXISTS composers;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS instrumentation_categories;
DROP TABLE IF EXISTS data_sources;

-- ========================================
-- Reference Tables
-- ========================================

-- Countries lookup table (normalized)
CREATE TABLE countries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    iso_code CHAR(2) NULL,
    region VARCHAR(50) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_country_name (name),
    INDEX idx_country_code (iso_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Instrumentation categories for filtering
CREATE TABLE instrumentation_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_instrumentation_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Data source tracking (Sheerpluck, IMSLP, manual entry)
CREATE TABLE data_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    url VARCHAR(255) NULL,
    description TEXT NULL,
    last_sync TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Core Tables
-- ========================================

-- Composers table
CREATE TABLE composers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Basic Info
    full_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NULL,
    name_normalized VARCHAR(255) NOT NULL, -- Lowercase, accents removed for search
    
    -- Dates
    birth_year SMALLINT NULL,
    death_year SMALLINT NULL,
    is_living BOOLEAN DEFAULT FALSE,
    
    -- Location
    country_id INT NULL,
    country_description TEXT NULL, -- For complex origins like "American composer of Brazilian origin"
    
    -- Biography
    biography TEXT NULL,
    period VARCHAR(50) NULL, -- Renaissance, Baroque, Classical, Romantic, Modern, Contemporary
    
    -- Metadata
    data_source_id INT NULL,
    external_id VARCHAR(100) NULL, -- Original ID from source
    imslp_url VARCHAR(255) NULL,
    wikipedia_url VARCHAR(255) NULL,
    
    -- Admin
    is_verified BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    admin_notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE SET NULL,
    FOREIGN KEY (data_source_id) REFERENCES data_sources(id) ON DELETE SET NULL,
    
    -- Indexes for search performance
    INDEX idx_composer_last_name (last_name),
    INDEX idx_composer_full_name (full_name),
    INDEX idx_composer_normalized (name_normalized),
    INDEX idx_composer_country (country_id),
    INDEX idx_composer_birth_year (birth_year),
    INDEX idx_composer_death_year (death_year),
    INDEX idx_composer_period (period),
    INDEX idx_composer_living (is_living),
    INDEX idx_composer_verified (is_verified),
    
    -- Full-text search index for name and biography
    FULLTEXT INDEX ft_composer_name (full_name, first_name, last_name),
    FULLTEXT INDEX ft_composer_bio (biography)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Composer name variants/aliases (for handling different spellings)
CREATE TABLE composer_aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    composer_id INT NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    alias_type ENUM('birth_name', 'stage_name', 'alternate_spelling', 'pseudonym', 'translation') DEFAULT 'alternate_spelling',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (composer_id) REFERENCES composers(id) ON DELETE CASCADE,
    
    INDEX idx_alias_composer (composer_id),
    INDEX idx_alias_name (alias_name),
    FULLTEXT INDEX ft_alias_name (alias_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Works table
CREATE TABLE works (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Relationships
    composer_id INT NOT NULL,
    
    -- Work Info
    title VARCHAR(500) NOT NULL,
    title_normalized VARCHAR(500) NOT NULL, -- Lowercase, accents removed for search
    subtitle TEXT NULL,
    opus_number VARCHAR(50) NULL,
    catalog_number VARCHAR(100) NULL,
    
    -- Composition details
    composition_year SMALLINT NULL,
    composition_year_approx BOOLEAN DEFAULT FALSE,
    duration_minutes SMALLINT NULL,
    
    -- Instrumentation
    instrumentation_category_id INT NULL,
    instrumentation_detail TEXT NULL, -- Original instrumentation string from source
    difficulty_level TINYINT NULL, -- 1-10 scale
    
    -- Content
    description TEXT NULL,
    movements TEXT NULL, -- JSON array or delimited list
    key_signature VARCHAR(50) NULL,
    
    -- External Resources
    imslp_url VARCHAR(255) NULL,
    youtube_url VARCHAR(255) NULL,
    score_url VARCHAR(255) NULL,
    
    -- Metadata
    data_source_id INT NULL,
    external_id VARCHAR(100) NULL,
    
    -- Admin
    is_verified BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT TRUE,
    view_count INT DEFAULT 0,
    admin_notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (composer_id) REFERENCES composers(id) ON DELETE CASCADE,
    FOREIGN KEY (instrumentation_category_id) REFERENCES instrumentation_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (data_source_id) REFERENCES data_sources(id) ON DELETE SET NULL,
    
    -- Indexes for search and filtering
    INDEX idx_work_composer (composer_id),
    INDEX idx_work_title (title),
    INDEX idx_work_normalized (title_normalized),
    INDEX idx_work_instrumentation (instrumentation_category_id),
    INDEX idx_work_year (composition_year),
    INDEX idx_work_difficulty (difficulty_level),
    INDEX idx_work_public (is_public),
    INDEX idx_work_verified (is_verified),
    INDEX idx_work_views (view_count),
    
    -- Composite indexes for common queries
    INDEX idx_composer_public (composer_id, is_public),
    INDEX idx_composer_verified (composer_id, is_verified),
    INDEX idx_instrumentation_public (instrumentation_category_id, is_public),
    
    -- Full-text search index
    FULLTEXT INDEX ft_work_title (title, subtitle),
    FULLTEXT INDEX ft_work_content (title, subtitle, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Tagging System (for flexible categorization)
-- ========================================

CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NULL, -- 'genre', 'style', 'technique', 'form', etc.
    description TEXT NULL,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_tag_name (name),
    INDEX idx_tag_slug (slug),
    INDEX idx_tag_category (category),
    INDEX idx_tag_usage (usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Many-to-many relationship between works and tags
CREATE TABLE work_tags (
    work_id INT NOT NULL,
    tag_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (work_id, tag_id),
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    
    INDEX idx_work_tags_work (work_id),
    INDEX idx_work_tags_tag (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Search Optimization Table
-- ========================================

-- Denormalized table for ultra-fast search
-- This table combines composer and work data for quick lookups
CREATE TABLE work_search_index (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_id INT NOT NULL UNIQUE,
    
    -- Denormalized data for fast search
    composer_full_name VARCHAR(255) NOT NULL,
    composer_last_name VARCHAR(100) NOT NULL,
    composer_country VARCHAR(100) NULL,
    composer_birth_year SMALLINT NULL,
    composer_death_year SMALLINT NULL,
    
    work_title VARCHAR(500) NOT NULL,
    work_instrumentation VARCHAR(200) NULL,
    work_year SMALLINT NULL,
    
    -- Combined search field
    search_text TEXT NOT NULL, -- Combines all searchable fields
    
    -- Boost/ranking factors
    popularity_score FLOAT DEFAULT 0.0,
    last_viewed TIMESTAMP NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
    
    -- Indexes for fast lookups
    INDEX idx_search_composer_last (composer_last_name),
    INDEX idx_search_composer_full (composer_full_name),
    INDEX idx_search_work_title (work_title),
    INDEX idx_search_instrumentation (work_instrumentation),
    INDEX idx_search_year (work_year),
    INDEX idx_search_popularity (popularity_score),
    
    -- Full-text index for comprehensive search
    FULLTEXT INDEX ft_search_all (search_text),
    FULLTEXT INDEX ft_search_names (composer_full_name, work_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Trigger to maintain search index
-- ========================================

DELIMITER //

-- Update search index when a work is inserted
CREATE TRIGGER trg_work_insert_search 
AFTER INSERT ON works
FOR EACH ROW
BEGIN
    INSERT INTO work_search_index (
        work_id,
        composer_full_name,
        composer_last_name,
        composer_country,
        composer_birth_year,
        composer_death_year,
        work_title,
        work_instrumentation,
        work_year,
        search_text
    )
    SELECT 
        NEW.id,
        c.full_name,
        c.last_name,
        co.name,
        c.birth_year,
        c.death_year,
        NEW.title,
        ic.name,
        NEW.composition_year,
        CONCAT_WS(' ',
            c.full_name,
            c.first_name,
            c.last_name,
            co.name,
            NEW.title,
            NEW.subtitle,
            ic.name,
            NEW.description
        )
    FROM composers c
    LEFT JOIN countries co ON c.country_id = co.id
    LEFT JOIN instrumentation_categories ic ON NEW.instrumentation_category_id = ic.id
    WHERE c.id = NEW.composer_id;
END//

-- Update search index when a work is updated
CREATE TRIGGER trg_work_update_search 
AFTER UPDATE ON works
FOR EACH ROW
BEGIN
    UPDATE work_search_index wsi
    JOIN composers c ON c.id = NEW.composer_id
    LEFT JOIN countries co ON c.country_id = co.id
    LEFT JOIN instrumentation_categories ic ON NEW.instrumentation_category_id = ic.id
    SET 
        wsi.composer_full_name = c.full_name,
        wsi.composer_last_name = c.last_name,
        wsi.composer_country = co.name,
        wsi.composer_birth_year = c.birth_year,
        wsi.composer_death_year = c.death_year,
        wsi.work_title = NEW.title,
        wsi.work_instrumentation = ic.name,
        wsi.work_year = NEW.composition_year,
        wsi.search_text = CONCAT_WS(' ',
            c.full_name,
            c.first_name,
            c.last_name,
            co.name,
            NEW.title,
            NEW.subtitle,
            ic.name,
            NEW.description
        ),
        wsi.updated_at = CURRENT_TIMESTAMP
    WHERE wsi.work_id = NEW.id;
END//

-- Update search index when composer is updated
CREATE TRIGGER trg_composer_update_search 
AFTER UPDATE ON composers
FOR EACH ROW
BEGIN
    UPDATE work_search_index wsi
    LEFT JOIN countries co ON NEW.country_id = co.id
    SET 
        wsi.composer_full_name = NEW.full_name,
        wsi.composer_last_name = NEW.last_name,
        wsi.composer_country = co.name,
        wsi.composer_birth_year = NEW.birth_year,
        wsi.composer_death_year = NEW.death_year,
        wsi.updated_at = CURRENT_TIMESTAMP
    WHERE wsi.work_id IN (
        SELECT id FROM works WHERE composer_id = NEW.id
    );
END//

DELIMITER ;

-- ========================================
-- Initial Data Population
-- ========================================

-- Insert initial data sources
INSERT INTO data_sources (name, url, description) VALUES
('Sheerpluck', 'https://www.sheerpluck.de', 'Sheerpluck classical guitar database'),
('IMSLP', 'https://imslp.org', 'International Music Score Library Project'),
('Manual Entry', NULL, 'Manually entered by staff');

-- Insert common instrumentation categories
INSERT INTO instrumentation_categories (name, sort_order) VALUES
('Solo', 10),
('Duo', 20),
('Trio', 30),
('Quartet', 40),
('Chamber Music', 50),
('Ensemble', 60),
('Guitar Ensemble', 70),
('Concerto', 80),
('Orchestra', 90),
('Guitar with Electronics', 100),
('Guitar with Fixed Media', 110),
('Electric Guitar Solo', 120),
('Bass Guitar Solo', 130),
('Plucked Instruments', 140),
('Chorus and Guitar', 150),
('Stage Work', 160),
('Incidental and Film', 170),
('Dance/Ballet', 180),
('Installation/Sound Environment', 190),
('Other', 200);

-- ========================================
-- Useful Views for Common Queries
-- ========================================

-- View for public search results
CREATE VIEW v_public_works AS
SELECT 
    w.id AS work_id,
    w.title AS work_title,
    w.composition_year,
    c.id AS composer_id,
    c.full_name AS composer_name,
    c.birth_year,
    c.death_year,
    co.name AS country,
    ic.name AS instrumentation,
    w.view_count,
    w.updated_at
FROM works w
JOIN composers c ON w.composer_id = c.id
LEFT JOIN countries co ON c.country_id = co.id
LEFT JOIN instrumentation_categories ic ON w.instrumentation_category_id = ic.id
WHERE w.is_public = TRUE;

-- View for composer statistics
CREATE VIEW v_composer_stats AS
SELECT 
    c.id,
    c.full_name,
    c.birth_year,
    c.death_year,
    co.name AS country,
    COUNT(w.id) AS total_works,
    SUM(w.view_count) AS total_views,
    AVG(w.difficulty_level) AS avg_difficulty,
    MIN(w.composition_year) AS earliest_work,
    MAX(w.composition_year) AS latest_work
FROM composers c
LEFT JOIN works w ON c.id = w.composer_id AND w.is_public = TRUE
LEFT JOIN countries co ON c.country_id = co.id
GROUP BY c.id;

-- View for popular works
CREATE VIEW v_popular_works AS
SELECT 
    w.id,
    w.title,
    c.full_name AS composer,
    ic.name AS instrumentation,
    w.view_count,
    w.updated_at
FROM works w
JOIN composers c ON w.composer_id = c.id
LEFT JOIN instrumentation_categories ic ON w.instrumentation_category_id = ic.id
WHERE w.is_public = TRUE
ORDER BY w.view_count DESC;

-- ========================================
-- Stored Procedures for Common Operations
-- ========================================

DELIMITER //

-- Increment view count and update popularity score
CREATE PROCEDURE sp_increment_work_views(IN p_work_id INT)
BEGIN
    UPDATE works 
    SET view_count = view_count + 1 
    WHERE id = p_work_id;
    
    UPDATE work_search_index
    SET 
        popularity_score = popularity_score + 1,
        last_viewed = CURRENT_TIMESTAMP
    WHERE work_id = p_work_id;
END//

-- Search works with relevance scoring
CREATE PROCEDURE sp_search_works(
    IN p_query VARCHAR(500),
    IN p_limit INT,
    IN p_offset INT
)
BEGIN
    SELECT 
        wsi.work_id,
        wsi.composer_full_name,
        wsi.composer_country,
        wsi.composer_birth_year,
        wsi.composer_death_year,
        wsi.work_title,
        wsi.work_instrumentation,
        wsi.work_year,
        wsi.popularity_score,
        MATCH(wsi.search_text) AGAINST(p_query IN NATURAL LANGUAGE MODE) AS relevance_score
    FROM work_search_index wsi
    WHERE MATCH(wsi.search_text) AGAINST(p_query IN NATURAL LANGUAGE MODE)
    ORDER BY relevance_score DESC, wsi.popularity_score DESC
    LIMIT p_limit OFFSET p_offset;
END//

DELIMITER ;

-- ========================================
-- Performance Optimization Notes
-- ========================================

/*
1. INDEXES:
   - B-tree indexes on foreign keys and frequently filtered columns
   - FULLTEXT indexes on searchable text fields
   - Composite indexes for common query patterns

2. DENORMALIZATION:
   - work_search_index table duplicates data for faster search
   - Maintained automatically via triggers

3. SEARCH STRATEGY:
   - Use FULLTEXT search for natural language queries
   - Use B-tree indexes for exact matches and filtering
   - Combine both for optimal results

4. CACHING RECOMMENDATIONS:
   - Cache popular searches in Redis/Memcached
   - Cache composer lists and statistics
   - Use Django's query caching for repeated queries

5. QUERY OPTIMIZATION:
   - Use EXPLAIN to analyze slow queries
   - Monitor slow query log
   - Consider MySQL query cache for repeated queries

6. SCALING CONSIDERATIONS:
   - If dataset grows beyond 1M records, consider:
     * Elasticsearch for full-text search
     * Read replicas for heavy read workloads
     * Partitioning large tables by year or composer
*/
