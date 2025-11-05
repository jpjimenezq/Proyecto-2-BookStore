package grpc

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	inventorypb "github.com/bookstore/contracts/gen/go/inventory"
	"github.com/bookstore/inventory/internal/db"
	"github.com/bookstore/inventory/internal/events"
	"github.com/bookstore/inventory/internal/repo"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type Server struct {
	inventorypb.UnimplementedInventoryServiceServer
	repo      *repo.InventoryRepo
	publisher *events.Publisher
}

func NewServer(repository *repo.InventoryRepo, publisher *events.Publisher) *grpc.Server {
	grpcServer := grpc.NewServer()

	svc := &Server{
		repo:      repository,
		publisher: publisher,
	}

	inventorypb.RegisterInventoryServiceServer(grpcServer, svc)

	return grpcServer
}

func (s *Server) GetItem(ctx context.Context, req *inventorypb.GetItemRequest) (*inventorypb.GetItemResponse, error) {
	item, err := s.repo.GetItemByID(req.ItemId)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "failed to get item: %v", err)
	}

	if item == nil {
		return nil, status.Errorf(codes.NotFound, "item not found: %s", req.ItemId)
	}

	return &inventorypb.GetItemResponse{
		Item: &inventorypb.Item{
			ItemId:   item.ItemID,
			Name:     item.Name,
			Category: item.Category,
			Quantity: item.Quantity,
			Price:    item.Price,
		},
	}, nil
}

func (s *Server) CheckAvailability(ctx context.Context, req *inventorypb.CheckAvailabilityRequest) (*inventorypb.CheckAvailabilityResponse, error) {
	item, err := s.repo.GetItemByID(req.ItemId)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "failed to check availability: %v", err)
	}

	if item == nil {
		return &inventorypb.CheckAvailabilityResponse{
			Available:         false,
			AvailableQuantity: 0,
			Message:           "Item not found",
		}, nil
	}

	available := item.Quantity >= req.RequestedQuantity
	message := "Available"
	if !available {
		message = fmt.Sprintf("Insufficient stock: requested=%d, available=%d", req.RequestedQuantity, item.Quantity)
	}

	return &inventorypb.CheckAvailabilityResponse{
		Available:         available,
		AvailableQuantity: item.Quantity,
		Message:           message,
	}, nil
}

func (s *Server) ReserveStock(ctx context.Context, req *inventorypb.ReserveStockRequest) (*inventorypb.ReserveStockResponse, error) {
	reserved := make([]db.ReservedItem, 0, len(req.Items))
	for _, ri := range req.Items {
		reserved = append(reserved, db.ReservedItem{
			ItemID:   ri.ItemId,
			Quantity: ri.Quantity,
		})
	}

	if err := s.repo.ReserveStock(req.OrderId, reserved); err != nil {
		log.Printf(" Failed to reserve stock for order %s: %v", req.OrderId, err)
		return &inventorypb.ReserveStockResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to reserve stock: %v", err),
		}, nil
	}

	// Publish stock reserved event
	if s.publisher != nil {
		event := events.StockReservedEvent{
			EventID:      fmt.Sprintf("inv-%d", time.Now().UnixNano()),
			EventType:    "inventory.stock_reserved",
			EventVersion: "1.0.0",
			Timestamp:    time.Now().Format(time.RFC3339),
			Payload: events.StockReservedPayload{
				OrderID: req.OrderId,
				Items:   reserved,
			},
		}

		data, _ := json.Marshal(event)
		if err := s.publisher.PublishEvent("inventory.stock_reserved", data); err != nil {
			log.Printf("  Failed to publish stock reserved event: %v", err)
		}
	}

	log.Printf(" Stock reserved for order %s", req.OrderId)
	return &inventorypb.ReserveStockResponse{
		Success: true,
		Message: "Stock reserved successfully",
	}, nil
}

func (s *Server) ReleaseStock(ctx context.Context, req *inventorypb.ReleaseStockRequest) (*inventorypb.ReleaseStockResponse, error) {
	reserved := make([]db.ReservedItem, 0, len(req.Items))
	for _, ri := range req.Items {
		reserved = append(reserved, db.ReservedItem{
			ItemID:   ri.ItemId,
			Quantity: ri.Quantity,
		})
	}

	if err := s.repo.ReleaseStock(req.OrderId, reserved); err != nil {
		log.Printf(" Failed to release stock for order %s: %v", req.OrderId, err)
		return &inventorypb.ReleaseStockResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to release stock: %v", err),
		}, nil
	}

	// Publish stock released event
	if s.publisher != nil {
		event := events.StockReleasedEvent{
			EventID:      fmt.Sprintf("inv-%d", time.Now().UnixNano()),
			EventType:    "inventory.stock_released",
			EventVersion: "1.0.0",
			Timestamp:    time.Now().Format(time.RFC3339),
			Payload: events.StockReleasedPayload{
				OrderID: req.OrderId,
				Items:   reserved,
			},
		}

		data, _ := json.Marshal(event)
		if err := s.publisher.PublishEvent("inventory.stock_released", data); err != nil {
			log.Printf("  Failed to publish stock released event: %v", err)
		}
	}

	log.Printf(" Stock released for order %s", req.OrderId)
	return &inventorypb.ReleaseStockResponse{
		Success: true,
		Message: "Stock released successfully",
	}, nil
}

func (s *Server) UpdateStock(ctx context.Context, req *inventorypb.UpdateStockRequest) (*inventorypb.UpdateStockResponse, error) {
	newQuantity, err := s.repo.UpdateStock(req.ItemId, req.Delta)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "failed to update stock: %v", err)
	}

	// Publish stock updated event
	if s.publisher != nil {
		event := events.StockUpdatedEvent{
			EventID:      fmt.Sprintf("inv-%d", time.Now().UnixNano()),
			EventType:    "inventory.stock_updated",
			EventVersion: "1.0.0",
			Timestamp:    time.Now().Format(time.RFC3339),
			Payload: events.StockUpdatedPayload{
				ItemID:           req.ItemId,
				PreviousQuantity: newQuantity - req.Delta,
				NewQuantity:      newQuantity,
				Delta:            req.Delta,
				Reason:           "Manual update",
			},
		}

		data, _ := json.Marshal(event)
		if err := s.publisher.PublishEvent("inventory.stock_updated", data); err != nil {
			log.Printf("  Failed to publish stock updated event: %v", err)
		}
	}

	return &inventorypb.UpdateStockResponse{
		Success:     true,
		Message:     "Stock updated successfully",
		NewQuantity: newQuantity,
	}, nil
}
