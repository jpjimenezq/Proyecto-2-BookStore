package db

import (
	"gorm.io/gorm"
)

// RunMigrations runs all database migrations
func RunMigrations(db *DB) error {
	// Auto-migrate Book model
	if err := db.AutoMigrate(&Book{}); err != nil {
		return err
	}

	// Create additional indexes if not exists
	if err := createIndexes(db.DB); err != nil {
		return err
	}

	return nil
}

func createIndexes(db *gorm.DB) error {
	// Full-text search indexes for PostgreSQL
	indexes := []string{
		// GIN index for full-text search on title
		`CREATE INDEX IF NOT EXISTS idx_books_title_search ON books USING gin(to_tsvector('english', title))`,

		// GIN index for full-text search on author
		`CREATE INDEX IF NOT EXISTS idx_books_author_search ON books USING gin(to_tsvector('english', author))`,

		// Composite index for common queries
		`CREATE INDEX IF NOT EXISTS idx_books_active_category ON books(active, category) WHERE active = true`,
	}

	for _, indexSQL := range indexes {
		if err := db.Exec(indexSQL).Error; err != nil {
			return err
		}
	}

	return nil
}




