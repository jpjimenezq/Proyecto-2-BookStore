-- Initial schema for catalog service
-- This migration is applied via GORM AutoMigrate, but keeping SQL for reference

-- Create books table
CREATE TABLE IF NOT EXISTS books (
    sku VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    price BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT true,
    stock INTEGER DEFAULT 0
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
CREATE INDEX IF NOT EXISTS idx_books_created_at ON books(created_at);
CREATE INDEX IF NOT EXISTS idx_books_active ON books(active);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_books_title_search ON books USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_books_author_search ON books USING gin(to_tsvector('english', author));

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_books_active_category ON books(active, category) WHERE active = true;

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE books IS 'Catalog of books available in the bookstore';
COMMENT ON COLUMN books.sku IS 'Stock Keeping Unit - unique identifier';
COMMENT ON COLUMN books.price IS 'Price in smallest currency unit (e.g., cents)';
COMMENT ON COLUMN books.currency IS 'ISO 4217 currency code';
COMMENT ON COLUMN books.stock IS 'Stock level - synced from Inventory service (read-only)';





