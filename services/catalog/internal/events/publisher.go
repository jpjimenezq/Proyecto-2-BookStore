package events

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	amqp "github.com/rabbitmq/amqp091-go"
	"go.uber.org/zap"
)

const (
	exchangeName = "bookstore.events"
	exchangeType = "topic"

	// Event types
	EventTypeCatalogCreated = "catalog.created"
	EventTypeCatalogUpdated = "catalog.updated"
	EventTypeCatalogDeleted = "catalog.deleted"

	// Retry configuration
	maxRetries     = 3
	initialBackoff = 100 * time.Millisecond
	maxBackoff     = 5 * time.Second
)

// Publisher handles event publishing to RabbitMQ
type Publisher struct {
	conn    *amqp.Connection
	channel *amqp.Channel
	log     *zap.Logger
}

// Event represents a domain event
type Event struct {
	EventID       string                 `json:"event_id"`
	EventType     string                 `json:"event_type"`
	EventVersion  string                 `json:"event_version"`
	Timestamp     string                 `json:"timestamp"`
	CorrelationID string                 `json:"correlation_id,omitempty"`
	Payload       map[string]interface{} `json:"payload"`
}

// NewPublisher creates a new event publisher
func NewPublisher(url string, log *zap.Logger) (*Publisher, error) {
	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	channel, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to open channel: %w", err)
	}

	// Declare exchange
	if err := channel.ExchangeDeclare(
		exchangeName,
		exchangeType,
		true,  // durable
		false, // auto-deleted
		false, // internal
		false, // no-wait
		nil,   // arguments
	); err != nil {
		channel.Close()
		conn.Close()
		return nil, fmt.Errorf("failed to declare exchange: %w", err)
	}

	// Enable publisher confirms for reliability
	if err := channel.Confirm(false); err != nil {
		channel.Close()
		conn.Close()
		return nil, fmt.Errorf("failed to enable publisher confirms: %w", err)
	}

	log.Info("Connected to RabbitMQ", zap.String("exchange", exchangeName))

	return &Publisher{
		conn:    conn,
		channel: channel,
		log:     log,
	}, nil
}

// PublishBookCreated publishes a book created event
func (p *Publisher) PublishBookCreated(ctx context.Context, sku, title, author, category, currency string, price int64, active bool) error {
	event := Event{
		EventID:      uuid.New().String(),
		EventType:    EventTypeCatalogCreated,
		EventVersion: "1.0.0",
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
		Payload: map[string]interface{}{
			"sku":      sku,
			"title":    title,
			"author":   author,
			"price":    price,
			"currency": currency,
			"category": category,
			"active":   active,
		},
	}

	// Extract correlation ID from context if available
	if corrID := ctx.Value("correlation_id"); corrID != nil {
		event.CorrelationID = corrID.(string)
	}

	return p.publishWithRetry(ctx, EventTypeCatalogCreated, event)
}

// PublishBookUpdated publishes a book updated event
func (p *Publisher) PublishBookUpdated(ctx context.Context, sku string, fieldsChanged []string, updates map[string]interface{}) error {
	event := Event{
		EventID:      uuid.New().String(),
		EventType:    EventTypeCatalogUpdated,
		EventVersion: "1.0.0",
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
		Payload: map[string]interface{}{
			"sku":            sku,
			"fields_changed": fieldsChanged,
		},
	}

	// Add updated field values to payload
	for k, v := range updates {
		event.Payload[k] = v
	}

	// Extract correlation ID from context if available
	if corrID := ctx.Value("correlation_id"); corrID != nil {
		event.CorrelationID = corrID.(string)
	}

	return p.publishWithRetry(ctx, EventTypeCatalogUpdated, event)
}

// PublishBookDeleted publishes a book deleted event
func (p *Publisher) PublishBookDeleted(ctx context.Context, sku string) error {
	event := Event{
		EventID:      uuid.New().String(),
		EventType:    EventTypeCatalogDeleted,
		EventVersion: "1.0.0",
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
		Payload: map[string]interface{}{
			"sku": sku,
		},
	}

	// Extract correlation ID from context if available
	if corrID := ctx.Value("correlation_id"); corrID != nil {
		event.CorrelationID = corrID.(string)
	}

	return p.publishWithRetry(ctx, EventTypeCatalogDeleted, event)
}

// publishWithRetry publishes an event with exponential backoff retry
func (p *Publisher) publishWithRetry(ctx context.Context, routingKey string, event Event) error {
	body, err := json.Marshal(event)
	if err != nil {
		p.log.Error("Failed to marshal event", zap.Error(err))
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	backoff := initialBackoff
	var lastErr error

	for attempt := 0; attempt < maxRetries; attempt++ {
		if attempt > 0 {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
				backoff *= 2
				if backoff > maxBackoff {
					backoff = maxBackoff
				}
			}
		}

		// Publish with confirmation
		confirms := p.channel.NotifyPublish(make(chan amqp.Confirmation, 1))

		err := p.channel.PublishWithContext(
			ctx,
			exchangeName,
			routingKey,
			false, // mandatory
			false, // immediate
			amqp.Publishing{
				ContentType:  "application/json",
				DeliveryMode: amqp.Persistent,
				Timestamp:    time.Now(),
				MessageId:    event.EventID,
				Body:         body,
				Headers: amqp.Table{
					"event_type":    event.EventType,
					"event_version": event.EventVersion,
				},
			},
		)

		if err != nil {
			lastErr = err
			p.log.Warn("Failed to publish event, retrying",
				zap.Int("attempt", attempt+1),
				zap.Error(err),
			)
			continue
		}

		// Wait for confirmation
		select {
		case confirm := <-confirms:
			if confirm.Ack {
				p.log.Info("Event published successfully",
					zap.String("event_id", event.EventID),
					zap.String("event_type", event.EventType),
					zap.String("routing_key", routingKey),
				)
				return nil
			}
			lastErr = fmt.Errorf("event not acknowledged")
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(5 * time.Second):
			lastErr = fmt.Errorf("confirmation timeout")
		}

		p.log.Warn("Event publish not confirmed, retrying",
			zap.Int("attempt", attempt+1),
			zap.Error(lastErr),
		)
	}

	p.log.Error("Failed to publish event after retries",
		zap.String("event_id", event.EventID),
		zap.String("event_type", event.EventType),
		zap.Int("attempts", maxRetries),
		zap.Error(lastErr),
	)
	return fmt.Errorf("failed to publish event after %d attempts: %w", maxRetries, lastErr)
}

// IsHealthy checks if the publisher connection is healthy
func (p *Publisher) IsHealthy() bool {
	return p.conn != nil && !p.conn.IsClosed()
}

// Close closes the publisher connection
func (p *Publisher) Close() error {
	if p.channel != nil {
		if err := p.channel.Close(); err != nil {
			p.log.Error("Failed to close channel", zap.Error(err))
		}
	}
	if p.conn != nil {
		if err := p.conn.Close(); err != nil {
			p.log.Error("Failed to close connection", zap.Error(err))
			return err
		}
	}
	p.log.Info("Publisher closed")
	return nil
}
