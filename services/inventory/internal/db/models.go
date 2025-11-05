package db

type Item struct {
	ItemID   string  `db:"item_id"`
	Name     string  `db:"name"`
	Category string  `db:"category"`
	Quantity int32   `db:"quantity"`
	Price    float64 `db:"price"`
}

type ReservedItem struct {
	ItemID   string
	Quantity int32
}
