package repo

import (
	"database/sql"
	"fmt"

	"github.com/bookstore/inventory/internal/db"
)

type InventoryRepo struct {
	db *sql.DB
}

func NewInventoryRepo(database *sql.DB) *InventoryRepo {
	return &InventoryRepo{db: database}
}

func (r *InventoryRepo) CreateItem(item *db.Item) error {
	query := `
		INSERT INTO items (item_id, name, category, quantity, price)
		VALUES ($1, $2, $3, $4, $5)
		ON CONFLICT (item_id) DO NOTHING`
	
	_, err := r.db.Exec(query, item.ItemID, item.Name, item.Category, item.Quantity, item.Price)
	if err != nil {
		return fmt.Errorf("failed to create item: %w", err)
	}
	return nil
}

func (r *InventoryRepo) DeleteItem(itemID string) error {
	query := `DELETE FROM items WHERE item_id = $1`
	result, err := r.db.Exec(query, itemID)
	if err != nil {
		return fmt.Errorf("failed to delete item: %w", err)
	}
	
	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	
	if rowsAffected == 0 {
		return fmt.Errorf("item not found: %s", itemID)
	}
	
	return nil
}

func (r *InventoryRepo) GetItemByID(itemID string) (*db.Item, error) {
	query := `SELECT item_id, name, category, quantity, price FROM items WHERE item_id = $1`
	row := r.db.QueryRow(query, itemID)

	var item db.Item
	if err := row.Scan(&item.ItemID, &item.Name, &item.Category, &item.Quantity, &item.Price); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return &item, nil
}

func (r *InventoryRepo) GetAllItems() ([]db.Item, error) {
	rows, err := r.db.Query(`SELECT item_id, name, category, quantity, price FROM items`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var items []db.Item
	for rows.Next() {
		var item db.Item
		if err := rows.Scan(&item.ItemID, &item.Name, &item.Category, &item.Quantity, &item.Price); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (r *InventoryRepo) UpdateStock(itemID string, delta int32) (int32, error) {
	var newQuantity int32
	query := `UPDATE items SET quantity = quantity + $1 WHERE item_id = $2 RETURNING quantity`
	err := r.db.QueryRow(query, delta, itemID).Scan(&newQuantity)
	if err != nil {
		return 0, err
	}
	return newQuantity, nil
}

func (r *InventoryRepo) ReserveStock(orderID string, reserved []db.ReservedItem) error {
	tx, err := r.db.Begin()
	if err != nil {
		return err
	}

	for _, ri := range reserved {
		var current int32
		if err := tx.QueryRow(`SELECT quantity FROM items WHERE item_id = $1 FOR UPDATE`, ri.ItemID).Scan(&current); err != nil {
			tx.Rollback()
			return err
		}
		if current < ri.Quantity {
			tx.Rollback()
			return fmt.Errorf("insufficient stock for item %s: available=%d, requested=%d", ri.ItemID, current, ri.Quantity)
		}
		if _, err := tx.Exec(`UPDATE items SET quantity = quantity - $1 WHERE item_id = $2`, ri.Quantity, ri.ItemID); err != nil {
			tx.Rollback()
			return err
		}
	}

	if err := tx.Commit(); err != nil {
		return err
	}
	return nil
}

func (r *InventoryRepo) ReleaseStock(orderID string, reserved []db.ReservedItem) error {
	tx, err := r.db.Begin()
	if err != nil {
		return err
	}

	for _, ri := range reserved {
		if _, err := tx.Exec(`UPDATE items SET quantity = quantity + $1 WHERE item_id = $2`, ri.Quantity, ri.ItemID); err != nil {
			tx.Rollback()
			return err
		}
	}

	if err := tx.Commit(); err != nil {
		return err
	}
	return nil
}
