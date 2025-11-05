package main

import (
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/bookstore/inventory/internal/config"
	"github.com/bookstore/inventory/internal/db"
	"github.com/bookstore/inventory/internal/events"
	"github.com/bookstore/inventory/internal/grpc"
	"github.com/bookstore/inventory/internal/repo"
	"github.com/bookstore/inventory/pkg/logger"
)

func main() {
	// Initialize logger
	log := logger.New("inventory")

	// Load configuration
	cfg := config.Load()
	log.Info("Starting Inventory Service", "port", cfg.GRPCPort)

	// Connect to database
	database, err := db.Connect(cfg.PGDSN)
	if err != nil {
		log.Fatal("Failed to connect to database", "error", err)
	}
	defer database.Close()

	// Run migrations
	if err := db.RunMigrations(database); err != nil {
		log.Fatal("Failed to run migrations", "error", err)
	}

	// Initialize repository
	repository := repo.NewInventoryRepo(database)

	// Initialize event publisher
	publisher, err := events.NewPublisher(cfg.RabbitMQURL, cfg.ServiceName)
	if err != nil {
		log.Warn("Failed to initialize event publisher", "error", err)
	} else {
		defer publisher.Close()
		log.Info("Event publisher initialized")
	}

	// Initialize event consumer
	consumer, err := events.NewConsumer(cfg.RabbitMQURL, cfg.ServiceName, repository, publisher)
	if err != nil {
		log.Warn("Failed to initialize event consumer", "error", err)
	} else {
		defer consumer.Close()

		// Start consuming events
		go func() {
			if err := consumer.Start(); err != nil {
				log.Error("Consumer error", "error", err)
			}
		}()
		log.Info("Event consumer started")
	}

	// Initialize gRPC server
	grpcServer := grpc.NewServer(repository, publisher)

	// Start health check HTTP server
	go startHealthServer(cfg.HTTPHealthPort, log)

	// Start gRPC server
	lis, err := net.Listen("tcp", fmt.Sprintf(":%s", cfg.GRPCPort))
	if err != nil {
		log.Fatal("Failed to listen", "error", err)
	}

	go func() {
		log.Info("gRPC server listening", "addr", lis.Addr())
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatal("Failed to serve gRPC", "error", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info("Shutting down server...")

	// Graceful shutdown
	grpcServer.GracefulStop()

	log.Info("Server stopped")
}

func startHealthServer(port string, log *logger.Logger) {
	http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	http.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	addr := fmt.Sprintf(":%s", port)
	log.Info("Health check server listening", "addr", addr)

	server := &http.Server{
		Addr:         addr,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Error("Health server error", "error", err)
	}
}
