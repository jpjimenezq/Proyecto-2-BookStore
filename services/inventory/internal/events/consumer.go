package events

import (
	"encoding/json"
	"fmt"
	"log"

	"github.com/bookstore/inventory/internal/db"
	"github.com/bookstore/inventory/internal/repo"
	amqp "github.com/rabbitmq/amqp091-go"
)

type Consumer struct {
	conn        *amqp.Connection
	channel     *amqp.Channel
	serviceName string
	repo        *repo.InventoryRepo
	publisher   *Publisher
}

func NewConsumer(url, serviceName string, repository *repo.InventoryRepo, publisher *Publisher) (*Consumer, error) {
	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to open channel: %w", err)
	}

	// Declare exchange
	if err := ch.ExchangeDeclare(
		ExchangeName,
		ExchangeType,
		true,
		false,
		false,
		false,
		nil,
	); err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("failed to declare exchange: %w", err)
	}

	log.Printf(" Consumer connected to RabbitMQ exchange: %s", ExchangeName)

	return &Consumer{
		conn:        conn,
		channel:     ch,
		serviceName: serviceName,
		repo:        repository,
		publisher:   publisher,
	}, nil
}

func (c *Consumer) Start() error {
	// Declare queue for this service
	queueName := fmt.Sprintf("%s.inventory.queue", c.serviceName)

	queue, err := c.channel.QueueDeclare(
		queueName,
		true,  // durable
		false, // delete when unused
		false, // exclusive
		false, // no-wait
		nil,   // arguments
	)
	if err != nil {
		return fmt.Errorf("failed to declare queue: %w", err)
	}

	// Bind queue to exchange with routing keys for order and catalog events
	routingKeys := []string{
		"order.created",
		"order.cancelled",
		"catalog.created",
		"catalog.deleted",
	}

	for _, key := range routingKeys {
		if err := c.channel.QueueBind(
			queue.Name,
			key,
			ExchangeName,
			false,
			nil,
		); err != nil {
			return fmt.Errorf("failed to bind queue to %s: %w", key, err)
		}
		log.Printf("Listening for events: %s", key)
	}

	// Start consuming
	msgs, err := c.channel.Consume(
		queue.Name,
		c.serviceName, // consumer tag
		false,         // auto-ack
		false,         // exclusive
		false,         // no-local
		false,         // no-wait
		nil,           // args
	)
	if err != nil {
		return fmt.Errorf("failed to register consumer: %w", err)
	}

	// Process messages
	for msg := range msgs {
		c.handleMessage(msg)
	}

	return nil
}

func (c *Consumer) handleMessage(msg amqp.Delivery) {
	log.Printf("Received event: %s", msg.RoutingKey)

	switch msg.RoutingKey {
	case "order.created":
		c.handleOrderCreated(msg)
	case "order.cancelled":
		c.handleOrderCancelled(msg)
	case "catalog.created":
		c.handleCatalogCreated(msg)
	case "catalog.deleted":
		c.handleCatalogDeleted(msg)
	default:
		log.Printf("  Unknown event type: %s", msg.RoutingKey)
		msg.Nack(false, false) // Don't requeue unknown events
	}
}

type OrderCreatedEvent struct {
	EventID      string `json:"event_id"`
	EventType    string `json:"event_type"`
	EventVersion string `json:"event_version"`
	Timestamp    string `json:"timestamp"`
	Payload      struct {
		OrderID string `json:"order_id"`
		UserID  string `json:"user_id"`
		Items   []struct {
			SKU      string  `json:"sku"`
			Quantity int32   `json:"quantity"`
			Price    float64 `json:"price"`
		} `json:"items"`
	} `json:"payload"`
}

type OrderCancelledEvent struct {
	EventID      string `json:"event_id"`
	EventType    string `json:"event_type"`
	EventVersion string `json:"event_version"`
	Timestamp    string `json:"timestamp"`
	Payload      struct {
		OrderID string `json:"order_id"`
		Reason  string `json:"reason"`
		Items   []struct {
			SKU      string  `json:"sku"`
			Quantity int32   `json:"quantity"`
			Price    float64 `json:"price"`
		} `json:"items"`
	} `json:"payload"`
}

func (c *Consumer) handleOrderCreated(msg amqp.Delivery) {
	var event OrderCreatedEvent
	if err := json.Unmarshal(msg.Body, &event); err != nil {
		log.Printf(" Failed to unmarshal order.created event: %v", err)
		msg.Nack(false, false)
		return
	}

	// Reserve stock for the order
	reserved := make([]db.ReservedItem, 0, len(event.Payload.Items))
	for _, item := range event.Payload.Items {
		reserved = append(reserved, db.ReservedItem{
			ItemID:   item.SKU,
			Quantity: item.Quantity,
		})
	}

	if err := c.repo.ReserveStock(event.Payload.OrderID, reserved); err != nil {
		log.Printf(" Failed to reserve stock for order %s: %v", event.Payload.OrderID, err)
		msg.Nack(false, true) // Requeue for retry
		return
	}

	log.Printf(" Stock reserved for order %s", event.Payload.OrderID)
	msg.Ack(false)
}

func (c *Consumer) handleOrderCancelled(msg amqp.Delivery) {
	var event OrderCancelledEvent
	if err := json.Unmarshal(msg.Body, &event); err != nil {
		log.Printf(" Failed to unmarshal order.cancelled event: %v", err)
		msg.Nack(false, false)
		return
	}

	// Release stock for the cancelled order
	reserved := make([]db.ReservedItem, 0, len(event.Payload.Items))
	for _, item := range event.Payload.Items {
		reserved = append(reserved, db.ReservedItem{
			ItemID:   item.SKU,
			Quantity: item.Quantity,
		})
	}

	if err := c.repo.ReleaseStock(event.Payload.OrderID, reserved); err != nil {
		log.Printf(" Failed to release stock for order %s: %v", event.Payload.OrderID, err)
		msg.Nack(false, true) // Requeue for retry
		return
	}

	log.Printf(" Stock released for cancelled order %s", event.Payload.OrderID)
	msg.Ack(false)
}

type CatalogCreatedEvent struct {
	EventID      string `json:"event_id"`
	EventType    string `json:"event_type"`
	EventVersion string `json:"event_version"`
	Timestamp    string `json:"timestamp"`
	Payload      struct {
		SKU      string `json:"sku"`
		Title    string `json:"title"`
		Author   string `json:"author"`
		Price    int64  `json:"price"`
		Currency string `json:"currency"`
		Category string `json:"category"`
		Active   bool   `json:"active"`
	} `json:"payload"`
}

type CatalogDeletedEvent struct {
	EventID      string `json:"event_id"`
	EventType    string `json:"event_type"`
	EventVersion string `json:"event_version"`
	Timestamp    string `json:"timestamp"`
	Payload      struct {
		SKU string `json:"sku"`
	} `json:"payload"`
}

func (c *Consumer) handleCatalogCreated(msg amqp.Delivery) {
	var event CatalogCreatedEvent
	if err := json.Unmarshal(msg.Body, &event); err != nil {
		log.Printf("Failed to unmarshal catalog.created event: %v", err)
		msg.Nack(false, false)
		return
	}

	log.Printf("Creating inventory item for book: %s (%s)", event.Payload.Title, event.Payload.SKU)

	// Convert price from cents to dollars
	priceInDollars := float64(event.Payload.Price) / 100.0

	// Create item in inventory with 0 stock initially
	item := &db.Item{
		ItemID:   event.Payload.SKU,
		Name:     event.Payload.Title,
		Category: event.Payload.Category,
		Quantity: 0, // Start with 0 stock
		Price:    priceInDollars,
	}

	if err := c.repo.CreateItem(item); err != nil {
		log.Printf("Failed to create inventory item for %s: %v", event.Payload.SKU, err)
		msg.Nack(false, true) // Requeue for retry
		return
	}

	log.Printf("Inventory item created: %s", event.Payload.SKU)

	// Publish inventory.created event
	if err := c.publisher.PublishItemCreated(event.Payload.SKU, event.Payload.Title, event.Payload.Category, 0); err != nil {
		log.Printf("Failed to publish inventory.created event: %v", err)
		// Don't fail the operation if event publishing fails
	}

	msg.Ack(false)
}

func (c *Consumer) handleCatalogDeleted(msg amqp.Delivery) {
	var event CatalogDeletedEvent
	if err := json.Unmarshal(msg.Body, &event); err != nil {
		log.Printf("Failed to unmarshal catalog.deleted event: %v", err)
		msg.Nack(false, false)
		return
	}

	log.Printf("Deleting inventory item: %s", event.Payload.SKU)

	if err := c.repo.DeleteItem(event.Payload.SKU); err != nil {
		log.Printf("Failed to delete inventory item %s: %v", event.Payload.SKU, err)
		msg.Nack(false, true) // Requeue for retry
		return
	}

	log.Printf("Inventory item deleted: %s", event.Payload.SKU)

	// Publish inventory.deleted event
	if err := c.publisher.PublishItemDeleted(event.Payload.SKU); err != nil {
		log.Printf("Failed to publish inventory.deleted event: %v", err)
	}

	msg.Ack(false)
}

func (c *Consumer) Close() {
	if c.channel != nil {
		c.channel.Close()
	}
	if c.conn != nil {
		c.conn.Close()
	}
}
