package main

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/bookstore/services/catalog/internal/clients"
	"github.com/bookstore/services/catalog/internal/config"
	"github.com/bookstore/services/catalog/internal/db"
	"github.com/bookstore/services/catalog/internal/events"
	grpcserver "github.com/bookstore/services/catalog/internal/grpc"
	"github.com/bookstore/services/catalog/internal/repo"
	"github.com/bookstore/services/catalog/pkg/logger"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
)

func main() {
	// Load configuration
	cfg := config.Load()

	// Initialize logger
	log := logger.NewLogger(cfg.ServiceName, cfg.LogLevel)
	defer log.Sync()

	log.Info("Catalog service starting")

	// Connect to database
	log.Info("Connecting to database...")
	database, err := db.Connect(cfg.PGDSN)
	if err != nil {
		log.Fatal("Failed to connect to database", zap.Error(err))
	}

	// Run migrations
	log.Info("Running database migrations...")
	if err := db.RunMigrations(database); err != nil {
		log.Fatal("Failed to run migrations", zap.Error(err))
	}

	// Initialize repository
	catalogRepo := repo.NewCatalogRepository(database, log)

	// Connect to RabbitMQ
	log.Info("Connecting to RabbitMQ")
	publisher, err := events.NewPublisher(cfg.RabbitMQURL, log)
	if err != nil {
		log.Fatal("Failed to connect to RabbitMQ", zap.Error(err))
	}
	defer publisher.Close()

	// Connect to Inventory service
	log.Info("Connecting to Inventory service")
	inventoryClient, err := clients.NewInventoryClient(log)
	if err != nil {
		log.Warn("Inventory service unavailable, stock info disabled", zap.Error(err))
		inventoryClient = nil
	}
	if inventoryClient != nil {
		defer inventoryClient.Close()
	}

	// Create gRPC server
	grpcServer := grpc.NewServer(
		grpc.UnaryInterceptor(grpcserver.LoggingInterceptor(log)),
	)

	// Register catalog service
	catalogService := grpcserver.NewCatalogServer(catalogRepo, publisher, inventoryClient, log)
	grpcserver.RegisterCatalogService(grpcServer, catalogService)

	// Register health service
	healthServer := grpcserver.NewHealthServer(database, publisher, log)
	grpc_health_v1.RegisterHealthServer(grpcServer, healthServer)

	// Enable reflection for grpcurl/grpcui
	reflection.Register(grpcServer)

	// Start gRPC server
	grpcListener, err := net.Listen("tcp", fmt.Sprintf(":%s", cfg.GRPCPort))
	if err != nil {
		log.Fatal("Failed to listen on gRPC port", zap.Error(err))
	}

	go func() {
		log.Info("Starting gRPC server", zap.String("address", grpcListener.Addr().String()))
		if err := grpcServer.Serve(grpcListener); err != nil {
			log.Fatal("Failed to serve gRPC", zap.Error(err))
		}
	}()

	// Start HTTP server for health check
	httpMux := http.NewServeMux()
	httpMux.HandleFunc("/healthz", healthHandler(database, publisher, log))

	httpServer := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.HTTPHealthPort),
		Handler:      httpMux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		log.Info("Starting HTTP server", zap.String("address", httpServer.Addr))
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal("Failed to serve HTTP", zap.Error(err))
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info("Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Shutdown HTTP server
	if err := httpServer.Shutdown(ctx); err != nil {
		log.Error("HTTP server shutdown error", zap.Error(err))
	}

	// Stop gRPC server
	grpcServer.GracefulStop()

	log.Info("Server stopped")
}

func healthHandler(database *db.DB, publisher *events.Publisher, log *zap.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Check database connection
		if err := database.Ping(); err != nil {
			log.Error("Database health check failed", zap.Error(err))
			w.WriteHeader(http.StatusServiceUnavailable)
			w.Write([]byte("unhealthy: database connection failed"))
			return
		}

		// Check RabbitMQ connection
		if !publisher.IsHealthy() {
			log.Error("RabbitMQ health check failed")
			w.WriteHeader(http.StatusServiceUnavailable)
			w.Write([]byte("unhealthy: rabbitmq connection failed"))
			return
		}

		w.WriteHeader(http.StatusOK)
		w.Write([]byte("healthy"))
	}
}
