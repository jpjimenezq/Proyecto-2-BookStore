package clients

import (
	"context"
	"fmt"
	"os"
	"time"

	inventorypb "github.com/bookstore/contracts/gen/go/inventory"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// InventoryClient wraps the gRPC connection to the inventory service
type InventoryClient struct {
	conn   *grpc.ClientConn
	client inventorypb.InventoryServiceClient
	log    *zap.Logger
}

// NewInventoryClient creates a new inventory service client
func NewInventoryClient(log *zap.Logger) (*InventoryClient, error) {
	inventoryURL := os.Getenv("INVENTORY_SERVICE_URL")
	if inventoryURL == "" {
		inventoryURL = "localhost:50055"
	}

	// Connect to inventory service
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(
		ctx,
		inventoryURL,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to inventory service: %w", err)
	}

	client := inventorypb.NewInventoryServiceClient(conn)
	log.Info("Inventory client connected", zap.String("url", inventoryURL))

	return &InventoryClient{
		conn:   conn,
		client: client,
		log:    log,
	}, nil
}

// GetStock retrieves the stock for an item
func (c *InventoryClient) GetStock(ctx context.Context, itemID string) (int32, error) {
	req := &inventorypb.GetItemRequest{
		ItemId: itemID,
	}

	resp, err := c.client.GetItem(ctx, req)
	if err != nil {
		// Return 0 if item not found in inventory (graceful degradation)
		c.log.Warn("Failed to get stock from inventory",
			zap.String("item_id", itemID),
			zap.Error(err),
		)
		return 0, nil
	}

	if resp.Item == nil {
		return 0, nil
	}

	return resp.Item.Quantity, nil
}

// Close closes the connection to inventory service
func (c *InventoryClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}
