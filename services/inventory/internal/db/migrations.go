package db

import (
	"database/sql"
)

func RunMigrations(db *sql.DB) error {
	schema := `
	CREATE TABLE IF NOT EXISTS items (
		item_id VARCHAR(255) PRIMARY KEY,
		name VARCHAR(500) NOT NULL,
		category VARCHAR(255),
		quantity INTEGER NOT NULL DEFAULT 0,
		price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

	CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
	CREATE INDEX IF NOT EXISTS idx_items_quantity ON items(quantity);
	`

	if _, err := db.Exec(schema); err != nil {
		return err
	}

	// Insert seed data if table is empty
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM items").Scan(&count); err != nil {
		return err
	}

	if count == 0 {
		seedData := `
		INSERT INTO items (item_id, name, category, quantity, price) VALUES
		('BOOK-001', 'The Great Gatsby', 'Fiction', 100, 15.99),
		('BOOK-002', 'To Kill a Mockingbird', 'Fiction', 75, 14.99),
		('BOOK-003', '1984', 'Science Fiction', 50, 13.99),
		('BOOK-004', 'Pride and Prejudice', 'Romance', 60, 12.99),
		('BOOK-005', 'The Catcher in the Rye', 'Fiction', 40, 11.99),
		('BOOK-006', 'Harry Potter and the Sorcerer''s Stone', 'Fantasy', 120, 19.99),
		('BOOK-007', 'The Hobbit', 'Fantasy', 80, 16.99),
		('BOOK-008', 'The Da Vinci Code', 'Mystery', 90, 14.99),
		('BOOK-009', 'The Alchemist', 'Fiction', 70, 13.99),
		('BOOK-010', 'The Chronicles of Narnia', 'Fantasy', 65, 22.99);
		`
		if _, err := db.Exec(seedData); err != nil {
			return err
		}
	}

	return nil
}
