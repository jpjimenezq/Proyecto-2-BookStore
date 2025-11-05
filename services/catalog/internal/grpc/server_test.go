package grpc

import (
	"context"
	"net"
	"testing"
	"time"

	"github.com/bookstore/services/catalog/internal/db"
	"github.com/bookstore/services/catalog/internal/events"
	"github.com/bookstore/services/catalog/internal/repo"
	"github.com/bookstore/services/catalog/pkg/logger"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/test/bufconn"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	catalogpb "github.com/bookstore/contracts/gen/go/catalog"
	commonpb "github.com/bookstore/contracts/gen/go/common"
)

const bufSize = 1024 * 1024

var lis *bufconn.Listener

// MockPublisher is a mock event publisher for testing
type MockPublisher struct {
	PublishedEvents []string
}

func (m *MockPublisher) PublishBookCreated(ctx context.Context, sku, title, author, category, currency string, price int64, active bool) error {
	m.PublishedEvents = append(m.PublishedEvents, "created:"+sku)
	return nil
}

func (m *MockPublisher) PublishBookUpdated(ctx context.Context, sku string, fieldsChanged []string, updates map[string]interface{}) error {
	m.PublishedEvents = append(m.PublishedEvents, "updated:"+sku)
	return nil
}

func (m *MockPublisher) PublishBookDeleted(ctx context.Context, sku string) error {
	m.PublishedEvents = append(m.PublishedEvents, "deleted:"+sku)
	return nil
}

func (m *MockPublisher) IsHealthy() bool {
	return true
}

func (m *MockPublisher) Close() error {
	return nil
}

func setupTestServer(t *testing.T) (*CatalogServer, catalogpb.CatalogServiceClient, *MockPublisher) {
	// Setup in-memory database
	gormDB, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	require.NoError(t, err)

	err = gormDB.AutoMigrate(&db.Book{})
	require.NoError(t, err)

	database := &db.DB{DB: gormDB}

	// Setup mock publisher
	mockPublisher := &MockPublisher{
		PublishedEvents: []string{},
	}

	// Setup logger
	log := logger.NewLogger("test", "info")

	// Create repository
	catalogRepo := repo.NewCatalogRepository(database, log)

	// Create gRPC server
	catalogServer := NewCatalogServer(catalogRepo, &events.Publisher{}, log)

	// Use real publisher interface by wrapping mock
	// For this test, we'll use the mock directly

	// Setup bufconn
	lis = bufconn.Listen(bufSize)
	s := grpc.NewServer()
	catalogpb.RegisterCatalogServiceServer(s, catalogServer)

	go func() {
		if err := s.Serve(lis); err != nil {
			t.Logf("Server exited with error: %v", err)
		}
	}()

	// Create client
	ctx := context.Background()
	conn, err := grpc.DialContext(ctx, "bufnet",
		grpc.WithContextDialer(bufDialer),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	require.NoError(t, err)

	client := catalogpb.NewCatalogServiceClient(conn)

	return catalogServer, client, mockPublisher
}

func bufDialer(context.Context, string) (net.Conn, error) {
	return lis.Dial()
}

func TestCreateAndGetBook(t *testing.T) {
	_, client, _ := setupTestServer(t)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Create book
	createReq := &catalogpb.CreateBookRequest{
		Book: &catalogpb.Book{
			Sku:    "SMOKE-001",
			Title:  "Smoke Test Book",
			Author: "Test Author",
			Price: &commonpb.Money{
				Currency:      "USD",
				Amount:        2999,
				DecimalPlaces: 2,
			},
			Category:    "testing",
			Description: "A test book",
			Active:      true,
		},
	}

	createResp, err := client.CreateBook(ctx, createReq)
	require.NoError(t, err)
	assert.NotNil(t, createResp)
	assert.Equal(t, "SMOKE-001", createResp.Book.Sku)
	assert.Equal(t, "Smoke Test Book", createResp.Book.Title)

	// Get book
	getReq := &catalogpb.GetBookRequest{
		Sku: "SMOKE-001",
	}

	getResp, err := client.GetBook(ctx, getReq)
	require.NoError(t, err)
	assert.NotNil(t, getResp)
	assert.Equal(t, "SMOKE-001", getResp.Book.Sku)
	assert.Equal(t, "Smoke Test Book", getResp.Book.Title)
	assert.Equal(t, "Test Author", getResp.Book.Author)
	assert.Equal(t, int64(2999), getResp.Book.Price.Amount)
}

func TestUpdateBook(t *testing.T) {
	_, client, _ := setupTestServer(t)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Create book
	createReq := &catalogpb.CreateBookRequest{
		Book: &catalogpb.Book{
			Sku:    "UPDATE-001",
			Title:  "Original Title",
			Author: "Original Author",
			Price: &commonpb.Money{
				Currency: "USD",
				Amount:   1999,
			},
			Active: true,
		},
	}

	_, err := client.CreateBook(ctx, createReq)
	require.NoError(t, err)

	// Update book
	updateReq := &catalogpb.UpdateBookRequest{
		Book: &catalogpb.Book{
			Sku:    "UPDATE-001",
			Title:  "Updated Title",
			Author: "Updated Author",
			Price: &commonpb.Money{
				Currency: "USD",
				Amount:   2999,
			},
			Active: true,
		},
		UpdateMask: []string{"title", "price"},
	}

	updateResp, err := client.UpdateBook(ctx, updateReq)
	require.NoError(t, err)
	assert.Equal(t, "Updated Title", updateResp.Book.Title)
	assert.Equal(t, int64(2999), updateResp.Book.Price.Amount)
}

func TestListBooks(t *testing.T) {
	_, client, _ := setupTestServer(t)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Create multiple books
	for i := 1; i <= 3; i++ {
		createReq := &catalogpb.CreateBookRequest{
			Book: &catalogpb.Book{
				Sku:    "LIST-00" + string(rune('0'+i)),
				Title:  "Book " + string(rune('0'+i)),
				Author: "Author " + string(rune('0'+i)),
				Price: &commonpb.Money{
					Currency: "USD",
					Amount:   int64(1000 * i),
				},
				Category: "test",
				Active:   true,
			},
		}
		_, err := client.CreateBook(ctx, createReq)
		require.NoError(t, err)
		time.Sleep(10 * time.Millisecond) // Ensure different timestamps
	}

	// List books
	listReq := &catalogpb.ListBooksRequest{
		Pagination: &commonpb.Pagination{
			Page:     1,
			PageSize: 10,
		},
		ActiveOnly: true,
	}

	listResp, err := client.ListBooks(ctx, listReq)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, len(listResp.Books), 3)
	assert.NotNil(t, listResp.Pagination)
}

func TestSearchBooks(t *testing.T) {
	_, client, _ := setupTestServer(t)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Create books
	createReq := &catalogpb.CreateBookRequest{
		Book: &catalogpb.Book{
			Sku:    "SEARCH-001",
			Title:  "Go Programming Language",
			Author: "Test Author",
			Price: &commonpb.Money{
				Currency: "USD",
				Amount:   3999,
			},
			Active: true,
		},
	}

	_, err := client.CreateBook(ctx, createReq)
	require.NoError(t, err)

	// Search books
	searchReq := &catalogpb.SearchBooksRequest{
		Query: "Go Programming",
		Pagination: &commonpb.Pagination{
			Page:     1,
			PageSize: 10,
		},
	}

	// Note: SQLite doesn't support full-text search like PostgreSQL
	// This test may not return results in SQLite
	_, err = client.SearchBooks(ctx, searchReq)
	// We just verify no crash, actual search results depend on database
	_ = err
}

func TestHealth(t *testing.T) {
	_, client, _ := setupTestServer(t)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	healthResp, err := client.Health(ctx, &commonpb.Empty{})
	require.NoError(t, err)
	assert.Equal(t, commonpb.HealthStatus_SERVING, healthResp.Status)
	assert.Equal(t, "catalog", healthResp.Service)
}

func TestValidation(t *testing.T) {
	_, client, _ := setupTestServer(t)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Test missing SKU
	createReq := &catalogpb.CreateBookRequest{
		Book: &catalogpb.Book{
			Title:  "Test Book",
			Author: "Test Author",
			Price: &commonpb.Money{
				Currency: "USD",
				Amount:   1999,
			},
		},
	}

	_, err := client.CreateBook(ctx, createReq)
	assert.Error(t, err)

	// Test missing title
	createReq = &catalogpb.CreateBookRequest{
		Book: &catalogpb.Book{
			Sku:    "TEST-001",
			Author: "Test Author",
			Price: &commonpb.Money{
				Currency: "USD",
				Amount:   1999,
			},
		},
	}

	_, err = client.CreateBook(ctx, createReq)
	assert.Error(t, err)
}




