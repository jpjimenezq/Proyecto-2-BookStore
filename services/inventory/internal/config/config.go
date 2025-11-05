package config

import (
	"os"
)

type Config struct {
	ServiceName    string
	PGDSN          string
	RabbitMQURL    string
	GRPCPort       string
	HTTPHealthPort string
	LogLevel       string
}

func Load() *Config {
	return &Config{
		ServiceName:    getEnv("SERVICE_NAME", "inventory"),
		PGDSN:          getEnv("PG_DSN", "postgres://bookstore:changeme@postgres-inventory:5432/inventorydb?sslmode=disable"),
		RabbitMQURL:    getEnv("RABBITMQ_URL", "amqp://admin:changeme@rabbitmq:5672/"),
		GRPCPort:       getEnv("GRPC_PORT", "50055"),
		HTTPHealthPort: getEnv("HTTP_HEALTH_PORT", "8083"),
		LogLevel:       getEnv("LOG_LEVEL", "info"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
