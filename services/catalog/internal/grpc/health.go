package grpc

import (
	"context"

	"github.com/bookstore/services/catalog/internal/db"
	"github.com/bookstore/services/catalog/internal/events"
	"go.uber.org/zap"
	"google.golang.org/grpc/health/grpc_health_v1"
)

// HealthServer implements the gRPC health checking protocol
type HealthServer struct {
	grpc_health_v1.UnimplementedHealthServer
	db        *db.DB
	publisher *events.Publisher
	log       *zap.Logger
}

// NewHealthServer creates a new health check server
func NewHealthServer(database *db.DB, publisher *events.Publisher, log *zap.Logger) *HealthServer {
	return &HealthServer{
		db:        database,
		publisher: publisher,
		log:       log,
	}
}

// Check implements the health check
func (h *HealthServer) Check(ctx context.Context, req *grpc_health_v1.HealthCheckRequest) (*grpc_health_v1.HealthCheckResponse, error) {
	// Check database
	if err := h.db.Ping(); err != nil {
		h.log.Error("Database health check failed", zap.Error(err))
		return &grpc_health_v1.HealthCheckResponse{
			Status: grpc_health_v1.HealthCheckResponse_NOT_SERVING,
		}, nil
	}

	// Check RabbitMQ
	if !h.publisher.IsHealthy() {
		h.log.Error("RabbitMQ health check failed")
		return &grpc_health_v1.HealthCheckResponse{
			Status: grpc_health_v1.HealthCheckResponse_NOT_SERVING,
		}, nil
	}

	return &grpc_health_v1.HealthCheckResponse{
		Status: grpc_health_v1.HealthCheckResponse_SERVING,
	}, nil
}

// Watch implements health check watching (streaming)
func (h *HealthServer) Watch(req *grpc_health_v1.HealthCheckRequest, server grpc_health_v1.Health_WatchServer) error {
	// For simplicity, we'll send the current status and close
	// In production, this could stream status changes
	resp := &grpc_health_v1.HealthCheckResponse{
		Status: grpc_health_v1.HealthCheckResponse_SERVING,
	}

	// Check health
	if err := h.db.Ping(); err != nil || !h.publisher.IsHealthy() {
		resp.Status = grpc_health_v1.HealthCheckResponse_NOT_SERVING
	}

	return server.Send(resp)
}




