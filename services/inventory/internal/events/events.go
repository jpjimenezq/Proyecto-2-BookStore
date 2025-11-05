package events

import "github.com/bookstore/inventory/internal/db"

type StockReservedEvent struct {
	EventID      string               `json:"event_id"`
	EventType    string               `json:"event_type"`
	EventVersion string               `json:"event_version"`
	Timestamp    string               `json:"timestamp"`
	Payload      StockReservedPayload `json:"payload"`
}

type StockReservedPayload struct {
	OrderID string            `json:"order_id"`
	Items   []db.ReservedItem `json:"items"`
}

type StockReleasedEvent struct {
	EventID      string               `json:"event_id"`
	EventType    string               `json:"event_type"`
	EventVersion string               `json:"event_version"`
	Timestamp    string               `json:"timestamp"`
	Payload      StockReleasedPayload `json:"payload"`
}

type StockReleasedPayload struct {
	OrderID string            `json:"order_id"`
	Items   []db.ReservedItem `json:"items"`
}

type StockUpdatedEvent struct {
	EventID      string              `json:"event_id"`
	EventType    string              `json:"event_type"`
	EventVersion string              `json:"event_version"`
	Timestamp    string              `json:"timestamp"`
	Payload      StockUpdatedPayload `json:"payload"`
}

type StockUpdatedPayload struct {
	ItemID           string `json:"item_id"`
	PreviousQuantity int32  `json:"previous_quantity"`
	NewQuantity      int32  `json:"new_quantity"`
	Delta            int32  `json:"delta"`
	Reason           string `json:"reason,omitempty"`
}
