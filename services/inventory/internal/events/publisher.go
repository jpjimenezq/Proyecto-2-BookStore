package events

import (
	"encoding/json"
	"fmt"
	"log"

	amqp "github.com/rabbitmq/amqp091-go"
)

const (
	ExchangeName = "bookstore.events"
	ExchangeType = "topic"
)

type Publisher struct {
	conn        *amqp.Connection
	channel     *amqp.Channel
	serviceName string
}

func NewPublisher(url, serviceName string) (*Publisher, error) {
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
		true,  // durable
		false, // auto-deleted
		false, // internal
		false, // no-wait
		nil,   // arguments
	); err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("failed to declare exchange: %w", err)
	}

	log.Printf(" Publisher connected to RabbitMQ exchange: %s", ExchangeName)

	return &Publisher{
		conn:        conn,
		channel:     ch,
		serviceName: serviceName,
	}, nil
}

func (p *Publisher) PublishEvent(routingKey string, body []byte) error {
	if p.channel == nil {
		return fmt.Errorf("publisher channel is nil")
	}

	err := p.channel.Publish(
		ExchangeName,
		routingKey,
		false, // mandatory
		false, // immediate
		amqp.Publishing{
			ContentType:  "application/json",
			Body:         body,
			DeliveryMode: amqp.Persistent,
			AppId:        p.serviceName,
		},
	)

	if err != nil {
		return fmt.Errorf("failed to publish event: %w", err)
	}

	return nil
}

func (p *Publisher) PublishItemCreated(itemID, name, category string, quantity int32) error {
	event := map[string]interface{}{
		"event_type": "inventory.created",
		"payload": map[string]interface{}{
			"item_id":  itemID,
			"name":     name,
			"category": category,
			"quantity": quantity,
		},
	}

	body, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	return p.PublishEvent("inventory.created", body)
}

func (p *Publisher) PublishItemDeleted(itemID string) error {
	event := map[string]interface{}{
		"event_type": "inventory.deleted",
		"payload": map[string]interface{}{
			"item_id": itemID,
		},
	}

	body, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	return p.PublishEvent("inventory.deleted", body)
}

func (p *Publisher) Close() {
	if p.channel != nil {
		p.channel.Close()
	}
	if p.conn != nil {
		p.conn.Close()
	}
}
