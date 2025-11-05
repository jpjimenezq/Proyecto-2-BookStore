package db

import (
	"time"

	"gorm.io/gorm"
)

// Book represents a book in the catalog database
type Book struct {
	SKU         string    `gorm:"primaryKey;type:varchar(50)" json:"sku"`
	Title       string    `gorm:"type:varchar(255);not null;index:idx_books_title" json:"title"`
	Author      string    `gorm:"type:varchar(255);not null;index:idx_books_author" json:"author"`
	Price       int64     `gorm:"not null" json:"price"`                                  // Price in smallest currency unit (cents)
	Currency    string    `gorm:"type:varchar(3);not null;default:'USD'" json:"currency"` // ISO 4217
	Category    string    `gorm:"type:varchar(100);index:idx_books_category" json:"category,omitempty"`
	Description string    `gorm:"type:text" json:"description,omitempty"`
	CreatedAt   time.Time `gorm:"not null;default:CURRENT_TIMESTAMP;index:idx_books_created_at" json:"created_at"`
	UpdatedAt   time.Time `gorm:"not null;default:CURRENT_TIMESTAMP" json:"updated_at"`
	Active      bool      `gorm:"not null;default:true;index:idx_books_active" json:"active"`
	Stock       *int32    `gorm:"default:0" json:"stock,omitempty"` // Optional, synced from Inventory service
}

// TableName specifies the table name for Book model
func (Book) TableName() string {
	return "books"
}

// BeforeCreate hook to set timestamps
func (b *Book) BeforeCreate(tx *gorm.DB) error {
	now := time.Now()
	if b.CreatedAt.IsZero() {
		b.CreatedAt = now
	}
	if b.UpdatedAt.IsZero() {
		b.UpdatedAt = now
	}
	return nil
}

// BeforeUpdate hook to update timestamp
func (b *Book) BeforeUpdate(tx *gorm.DB) error {
	b.UpdatedAt = time.Now()
	return nil
}




