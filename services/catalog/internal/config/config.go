package config

import (
	"os"
)

// Config holds all configuration for the catalog service
type Config struct {
	ServiceName    string
	PGDSN          string
	GRPCPort       string
	HTTPHealthPort string
	RabbitMQURL    string
	LogLevel       string
}

// Load loads configuration from environment variables
func Load() *Config {
	return &Config{
		ServiceName:    getEnv("SERVICE_NAME", "catalog"),
		PGDSN:          getEnv("PG_DSN", "postgres://bookstore:changeme@localhost:5432/catalog?sslmode=disable"),
		GRPCPort:       getEnv("GRPC_PORT", "50051"),
		HTTPHealthPort: getEnv("HTTP_HEALTH_PORT", "8080"),
		RabbitMQURL:    getEnv("RABBITMQ_URL", "amqp://admin:changeme@localhost:5672/"),
		LogLevel:       getEnv("LOG_LEVEL", "info"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}




