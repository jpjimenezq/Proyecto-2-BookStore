package repo

import (
	"context"
	"errors"
	"fmt"

	"github.com/bookstore/services/catalog/internal/db"
	"go.uber.org/zap"
	"gorm.io/gorm"
)

var (
	// ErrBookNotFound is returned when a book is not found
	ErrBookNotFound = errors.New("book not found")

	// ErrBookAlreadyExists is returned when trying to create a book that already exists
	ErrBookAlreadyExists = errors.New("book already exists")
)

// CatalogRepository handles book catalog operations
type CatalogRepository struct {
	db  *db.DB
	log *zap.Logger
}

// NewCatalogRepository creates a new catalog repository
func NewCatalogRepository(database *db.DB, logger *zap.Logger) *CatalogRepository {
	return &CatalogRepository{
		db:  database,
		log: logger,
	}
}

// ListBooks returns a paginated list of books with optional filters
func (r *CatalogRepository) ListBooks(ctx context.Context, page, pageSize int32, category, author string, activeOnly bool, minPrice, maxPrice float64) ([]*db.Book, int64, error) {
	query := r.db.WithContext(ctx).Model(&db.Book{})

	// Apply filters
	if category != "" {
		query = query.Where("category = ?", category)
	}
	if author != "" {
		query = query.Where("author ILIKE ?", "%"+author+"%")
	}
	if activeOnly {
		query = query.Where("active = ?", true)
	}
	if minPrice > 0 {
		query = query.Where("price >= ?", int64(minPrice*100))
	}
	if maxPrice > 0 {
		query = query.Where("price <= ?", int64(maxPrice*100))
	}

	// Count total
	var total int64
	if err := query.Count(&total).Error; err != nil {
		r.log.Error("Failed to count books", zap.Error(err))
		return nil, 0, err
	}

	// Apply pagination
	offset := (page - 1) * pageSize
	var books []*db.Book
	if err := query.Offset(int(offset)).Limit(int(pageSize)).Order("created_at DESC").Find(&books).Error; err != nil {
		r.log.Error("Failed to list books", zap.Error(err))
		return nil, 0, err
	}

	return books, total, nil
}

// GetBook retrieves a book by SKU
func (r *CatalogRepository) GetBook(ctx context.Context, sku string) (*db.Book, error) {
	var book db.Book
	err := r.db.WithContext(ctx).Where("sku = ?", sku).First(&book).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrBookNotFound
		}
		r.log.Error("Failed to get book", zap.String("sku", sku), zap.Error(err))
		return nil, err
	}

	return &book, nil
}

// CreateBook creates a new book in the catalog
func (r *CatalogRepository) CreateBook(ctx context.Context, book *db.Book) error {
	// Generate SKU if not provided
	if book.SKU == "" {
		sku, err := r.generateNextSKU(ctx)
		if err != nil {
			r.log.Error("Failed to generate SKU", zap.Error(err))
			return err
		}
		book.SKU = sku
	}

	// Check if book already exists
	var existing db.Book
	err := r.db.WithContext(ctx).Where("sku = ?", book.SKU).First(&existing).Error
	if err == nil {
		return ErrBookAlreadyExists
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		r.log.Error("Failed to check book existence", zap.String("sku", book.SKU), zap.Error(err))
		return err
	}

	// Create book
	if err := r.db.WithContext(ctx).Create(book).Error; err != nil {
		r.log.Error("Failed to create book", zap.String("sku", book.SKU), zap.Error(err))
		return err
	}

	r.log.Info("Book created", zap.String("sku", book.SKU), zap.String("title", book.Title))
	return nil
}

// generateNextSKU generates the next sequential SKU (BOOK-001, BOOK-002, etc.)
func (r *CatalogRepository) generateNextSKU(ctx context.Context) (string, error) {
	var lastBook db.Book
	
	// Get the last book ordered by SKU (descending) that matches BOOK-% pattern
	err := r.db.WithContext(ctx).
		Where("sku LIKE ?", "BOOK-%").
		Order("sku DESC").
		First(&lastBook).Error
	
	if errors.Is(err, gorm.ErrRecordNotFound) {
		// No books exist yet, start with BOOK-001
		return "BOOK-001", nil
	}
	
	if err != nil {
		return "", fmt.Errorf("failed to get last book: %w", err)
	}
	
	// Extract number from last SKU (e.g., "BOOK-015" -> 15)
	var lastNum int
	_, err = fmt.Sscanf(lastBook.SKU, "BOOK-%d", &lastNum)
	if err != nil {
		// If parsing fails, count all books and add 1
		var count int64
		if err := r.db.WithContext(ctx).Model(&db.Book{}).Count(&count).Error; err != nil {
			return "", fmt.Errorf("failed to count books: %w", err)
		}
		return fmt.Sprintf("BOOK-%03d", count+1), nil
	}
	
	// Generate next SKU
	nextNum := lastNum + 1
	return fmt.Sprintf("BOOK-%03d", nextNum), nil
}

// UpdateBook updates an existing book
func (r *CatalogRepository) UpdateBook(ctx context.Context, book *db.Book, updateMask []string) ([]string, error) {
	// Get existing book to compare changes
	existing, err := r.GetBook(ctx, book.SKU)
	if err != nil {
		return nil, err
	}

	// Determine which fields changed
	fieldsChanged := r.getChangedFields(existing, book, updateMask)
	if len(fieldsChanged) == 0 {
		r.log.Info("No fields changed", zap.String("sku", book.SKU))
		return fieldsChanged, nil
	}

	// Build update map
	updates := make(map[string]interface{})
	for _, field := range fieldsChanged {
		switch field {
		case "title":
			updates["title"] = book.Title
		case "author":
			updates["author"] = book.Author
		case "price":
			updates["price"] = book.Price
		case "currency":
			updates["currency"] = book.Currency
		case "category":
			updates["category"] = book.Category
		case "description":
			updates["description"] = book.Description
		case "active":
			updates["active"] = book.Active
		}
	}

	// Update book
	if err := r.db.WithContext(ctx).Model(&db.Book{}).Where("sku = ?", book.SKU).Updates(updates).Error; err != nil {
		r.log.Error("Failed to update book", zap.String("sku", book.SKU), zap.Error(err))
		return nil, err
	}

	r.log.Info("Book updated", zap.String("sku", book.SKU), zap.Strings("fields_changed", fieldsChanged))
	return fieldsChanged, nil
}

// SearchBooks performs full-text search on books
func (r *CatalogRepository) SearchBooks(ctx context.Context, query string, page, pageSize int32, category string) ([]*db.Book, int64, error) {
	// Build search query using PostgreSQL full-text search
	searchQuery := r.db.WithContext(ctx).Model(&db.Book{}).
		Where("to_tsvector('english', title || ' ' || author) @@ plainto_tsquery('english', ?)", query)

	if category != "" {
		searchQuery = searchQuery.Where("category = ?", category)
	}

	// Count total
	var total int64
	if err := searchQuery.Count(&total).Error; err != nil {
		r.log.Error("Failed to count search results", zap.Error(err))
		return nil, 0, err
	}

	// Apply pagination
	offset := (page - 1) * pageSize
	var books []*db.Book
	if err := searchQuery.Offset(int(offset)).Limit(int(pageSize)).Find(&books).Error; err != nil {
		r.log.Error("Failed to search books", zap.Error(err))
		return nil, 0, err
	}

	return books, total, nil
}

// DeleteBook soft deletes a book by setting active to false
func (r *CatalogRepository) DeleteBook(ctx context.Context, sku string) error {
	result := r.db.WithContext(ctx).Model(&db.Book{}).Where("sku = ?", sku).Update("active", false)
	if result.Error != nil {
		r.log.Error("Failed to delete book", zap.String("sku", sku), zap.Error(result.Error))
		return result.Error
	}

	if result.RowsAffected == 0 {
		return ErrBookNotFound
	}

	r.log.Info("Book deleted", zap.String("sku", sku))
	return nil
}

// getChangedFields compares old and new book and returns list of changed fields
func (r *CatalogRepository) getChangedFields(old, new *db.Book, updateMask []string) []string {
	var changed []string

	// If update mask is provided, only check those fields
	checkFields := updateMask
	if len(checkFields) == 0 {
		checkFields = []string{"title", "author", "price", "currency", "category", "description", "active"}
	}

	for _, field := range checkFields {
		switch field {
		case "title":
			if old.Title != new.Title {
				changed = append(changed, "title")
			}
		case "author":
			if old.Author != new.Author {
				changed = append(changed, "author")
			}
		case "price":
			if old.Price != new.Price {
				changed = append(changed, "price")
			}
		case "currency":
			if old.Currency != new.Currency {
				changed = append(changed, "currency")
			}
		case "category":
			if old.Category != new.Category {
				changed = append(changed, "category")
			}
		case "description":
			if old.Description != new.Description {
				changed = append(changed, "description")
			}
		case "active":
			if old.Active != new.Active {
				changed = append(changed, "active")
			}
		}
	}

	return changed
}

// GetStats returns catalog statistics for metrics
func (r *CatalogRepository) GetStats(ctx context.Context) (total, active int64, err error) {
	if err := r.db.WithContext(ctx).Model(&db.Book{}).Count(&total).Error; err != nil {
		return 0, 0, fmt.Errorf("failed to count total books: %w", err)
	}

	if err := r.db.WithContext(ctx).Model(&db.Book{}).Where("active = ?", true).Count(&active).Error; err != nil {
		return 0, 0, fmt.Errorf("failed to count active books: %w", err)
	}

	return total, active, nil
}
