package grpc

import (
	"context"
	"time"

	"github.com/bookstore/services/catalog/internal/clients"
	"github.com/bookstore/services/catalog/internal/db"
	"github.com/bookstore/services/catalog/internal/events"
	"github.com/bookstore/services/catalog/internal/repo"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	// Import generated proto files
	catalogpb "github.com/bookstore/contracts/gen/go/catalog"
	commonpb "github.com/bookstore/contracts/gen/go/common"
)

// CatalogServer implements the CatalogService gRPC service
type CatalogServer struct {
	catalogpb.UnimplementedCatalogServiceServer
	repo            *repo.CatalogRepository
	publisher       *events.Publisher
	inventoryClient *clients.InventoryClient
	log             *zap.Logger
}

// NewCatalogServer creates a new catalog gRPC server
func NewCatalogServer(repo *repo.CatalogRepository, publisher *events.Publisher, inventoryClient *clients.InventoryClient, log *zap.Logger) *CatalogServer {
	return &CatalogServer{
		repo:            repo,
		publisher:       publisher,
		inventoryClient: inventoryClient,
		log:             log,
	}
}

// RegisterCatalogService registers the catalog service with the gRPC server
func RegisterCatalogService(s *grpc.Server, srv *CatalogServer) {
	catalogpb.RegisterCatalogServiceServer(s, srv)
}

// ListBooks returns a paginated list of books
func (s *CatalogServer) ListBooks(ctx context.Context, req *catalogpb.ListBooksRequest) (*catalogpb.ListBooksResponse, error) {
	// Validate pagination
	page := req.GetPagination().GetPage()
	pageSize := req.GetPagination().GetPageSize()
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 10
	}

	// Call repository
	books, total, err := s.repo.ListBooks(
		ctx,
		page,
		pageSize,
		req.GetCategory(),
		req.GetAuthor(),
		req.GetActiveOnly(),
		req.GetMinPrice(),
		req.GetMaxPrice(),
	)
	if err != nil {
		s.log.Error("Failed to list books", zap.Error(err))
		return nil, status.Error(codes.Internal, "failed to list books")
	}

	// Convert to proto
	pbBooks := make([]*catalogpb.Book, len(books))
	for i, book := range books {
		pbBooks[i] = s.bookToProto(ctx, book)
	}

	// Calculate total pages
	totalPages := int32(total) / pageSize
	if int32(total)%pageSize > 0 {
		totalPages++
	}

	return &catalogpb.ListBooksResponse{
		Books: pbBooks,
		Pagination: &commonpb.Pagination{
			Page:       page,
			PageSize:   pageSize,
			Total:      int32(total),
			TotalPages: totalPages,
		},
	}, nil
}

// GetBook retrieves a single book by SKU
func (s *CatalogServer) GetBook(ctx context.Context, req *catalogpb.GetBookRequest) (*catalogpb.GetBookResponse, error) {
	if req.GetSku() == "" {
		return nil, status.Error(codes.InvalidArgument, "sku is required")
	}

	book, err := s.repo.GetBook(ctx, req.GetSku())
	if err != nil {
		if err == repo.ErrBookNotFound {
			return nil, status.Error(codes.NotFound, "book not found")
		}
		s.log.Error("Failed to get book", zap.String("sku", req.GetSku()), zap.Error(err))
		return nil, status.Error(codes.Internal, "failed to get book")
	}

	return &catalogpb.GetBookResponse{
		Book: s.bookToProto(ctx, book),
	}, nil
}

// CreateBook creates a new book in the catalog
func (s *CatalogServer) CreateBook(ctx context.Context, req *catalogpb.CreateBookRequest) (*catalogpb.CreateBookResponse, error) {
	// Validate request (SKU is optional for create)
	if err := validateBookForCreate(req.GetBook()); err != nil {
		return nil, status.Error(codes.InvalidArgument, err.Error())
	}

	// Convert from proto
	book := protoToBook(req.GetBook())

	// Create book
	if err := s.repo.CreateBook(ctx, book); err != nil {
		if err == repo.ErrBookAlreadyExists {
			return nil, status.Error(codes.AlreadyExists, "book already exists")
		}
		s.log.Error("Failed to create book", zap.Error(err))
		return nil, status.Error(codes.Internal, "failed to create book")
	}

	// Publish event (async, don't fail request if event publishing fails)
	go func() {
		eventCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		if err := s.publisher.PublishBookCreated(
			eventCtx,
			book.SKU,
			book.Title,
			book.Author,
			book.Category,
			book.Currency,
			book.Price,
			book.Active,
		); err != nil {
			s.log.Error("Failed to publish book created event",
				zap.String("sku", book.SKU),
				zap.Error(err),
			)
		}
	}()

	return &catalogpb.CreateBookResponse{
		Book: s.bookToProto(ctx, book),
	}, nil
}

// UpdateBook updates an existing book
func (s *CatalogServer) UpdateBook(ctx context.Context, req *catalogpb.UpdateBookRequest) (*catalogpb.UpdateBookResponse, error) {
	// Validate request
	if err := validateBook(req.GetBook()); err != nil {
		return nil, status.Error(codes.InvalidArgument, err.Error())
	}

	// Convert from proto
	book := protoToBook(req.GetBook())

	// Update book
	fieldsChanged, err := s.repo.UpdateBook(ctx, book, req.GetUpdateMask())
	if err != nil {
		if err == repo.ErrBookNotFound {
			return nil, status.Error(codes.NotFound, "book not found")
		}
		s.log.Error("Failed to update book", zap.Error(err))
		return nil, status.Error(codes.Internal, "failed to update book")
	}

	// Publish event only if fields changed (async)
	if len(fieldsChanged) > 0 {
		go func() {
			eventCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()

			updates := buildUpdatePayload(book, fieldsChanged)
			if err := s.publisher.PublishBookUpdated(eventCtx, book.SKU, fieldsChanged, updates); err != nil {
				s.log.Error("Failed to publish book updated event",
					zap.String("sku", book.SKU),
					zap.Error(err),
				)
			}
		}()
	}

	// Get updated book
	updatedBook, err := s.repo.GetBook(ctx, book.SKU)
	if err != nil {
		s.log.Error("Failed to get updated book", zap.Error(err))
		return nil, status.Error(codes.Internal, "failed to get updated book")
	}

	return &catalogpb.UpdateBookResponse{
		Book: s.bookToProto(ctx, updatedBook),
	}, nil
}

// SearchBooks performs full-text search on books
func (s *CatalogServer) SearchBooks(ctx context.Context, req *catalogpb.SearchBooksRequest) (*catalogpb.SearchBooksResponse, error) {
	if req.GetQuery() == "" {
		return nil, status.Error(codes.InvalidArgument, "query is required")
	}

	// Validate pagination
	page := req.GetPagination().GetPage()
	pageSize := req.GetPagination().GetPageSize()
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 10
	}

	// Search books
	books, total, err := s.repo.SearchBooks(ctx, req.GetQuery(), page, pageSize, req.GetCategory())
	if err != nil {
		s.log.Error("Failed to search books", zap.Error(err))
		return nil, status.Error(codes.Internal, "failed to search books")
	}

	// Convert to proto
	pbBooks := make([]*catalogpb.Book, len(books))
	for i, book := range books {
		pbBooks[i] = s.bookToProto(ctx, book)
	}

	// Calculate total pages
	totalPages := int32(total) / pageSize
	if int32(total)%pageSize > 0 {
		totalPages++
	}

	return &catalogpb.SearchBooksResponse{
		Books: pbBooks,
		Pagination: &commonpb.Pagination{
			Page:       page,
			PageSize:   pageSize,
			Total:      int32(total),
			TotalPages: totalPages,
		},
	}, nil
}

// Health performs a health check
func (s *CatalogServer) Health(ctx context.Context, req *commonpb.Empty) (*commonpb.HealthStatus, error) {
	// This is handled by the dedicated health server
	return &commonpb.HealthStatus{
		Status:  commonpb.HealthStatus_SERVING,
		Service: "catalog",
		Version: "1.0.0",
	}, nil
}

// Helper functions

func (s *CatalogServer) bookToProto(ctx context.Context, book *db.Book) *catalogpb.Book {
	pb := &catalogpb.Book{
		Sku:    book.SKU,
		Title:  book.Title,
		Author: book.Author,
		Price: &commonpb.Money{
			Currency:      book.Currency,
			Amount:        book.Price,
			DecimalPlaces: 2,
		},
		Category:    book.Category,
		Description: book.Description,
		CreatedAt:   book.CreatedAt.Unix(),
		UpdatedAt:   book.UpdatedAt.Unix(),
		Active:      book.Active,
	}

	// Get real stock from inventory service
	if s.inventoryClient != nil {
		stockCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
		defer cancel()

		stock, err := s.inventoryClient.GetStock(stockCtx, book.SKU)
		if err == nil {
			pb.Stock = &stock
		} else {
			// If inventory service is unavailable, set stock to 0
			zero := int32(0)
			pb.Stock = &zero
		}
	}

	return pb
}

func protoToBook(pb *catalogpb.Book) *db.Book {
	book := &db.Book{
		SKU:         pb.GetSku(),
		Title:       pb.GetTitle(),
		Author:      pb.GetAuthor(),
		Currency:    pb.GetPrice().GetCurrency(),
		Price:       pb.GetPrice().GetAmount(),
		Category:    pb.GetCategory(),
		Description: pb.GetDescription(),
		Active:      pb.GetActive(),
	}

	// Handle optional stock
	if pb.Stock != nil {
		book.Stock = pb.Stock
	}

	return book
}

func validateBook(book *catalogpb.Book) error {
	if book == nil {
		return status.Error(codes.InvalidArgument, "book is required")
	}
	if book.GetSku() == "" {
		return status.Error(codes.InvalidArgument, "sku is required")
	}
	if book.GetTitle() == "" {
		return status.Error(codes.InvalidArgument, "title is required")
	}
	if book.GetAuthor() == "" {
		return status.Error(codes.InvalidArgument, "author is required")
	}
	if book.GetPrice() == nil {
		return status.Error(codes.InvalidArgument, "price is required")
	}
	if book.GetPrice().GetAmount() <= 0 {
		return status.Error(codes.InvalidArgument, "price must be positive")
	}
	if book.GetPrice().GetCurrency() == "" {
		return status.Error(codes.InvalidArgument, "currency is required")
	}
	return nil
}

// validateBookForCreate validates a book for creation (SKU is optional)
func validateBookForCreate(book *catalogpb.Book) error {
	if book == nil {
		return status.Error(codes.InvalidArgument, "book is required")
	}
	// SKU is optional - will be auto-generated if not provided
	if book.GetTitle() == "" {
		return status.Error(codes.InvalidArgument, "title is required")
	}
	if book.GetAuthor() == "" {
		return status.Error(codes.InvalidArgument, "author is required")
	}
	if book.GetPrice() == nil {
		return status.Error(codes.InvalidArgument, "price is required")
	}
	if book.GetPrice().GetAmount() <= 0 {
		return status.Error(codes.InvalidArgument, "price must be positive")
	}
	if book.GetPrice().GetCurrency() == "" {
		return status.Error(codes.InvalidArgument, "currency is required")
	}
	return nil
}

func buildUpdatePayload(book *db.Book, fieldsChanged []string) map[string]interface{} {
	payload := make(map[string]interface{})
	for _, field := range fieldsChanged {
		switch field {
		case "title":
			payload["title"] = book.Title
		case "author":
			payload["author"] = book.Author
		case "price":
			payload["price"] = book.Price
		case "currency":
			payload["currency"] = book.Currency
		case "category":
			payload["category"] = book.Category
		case "description":
			payload["description"] = book.Description
		case "active":
			payload["active"] = book.Active
		}
	}
	return payload
}

// LoggingInterceptor logs all gRPC requests
func LoggingInterceptor(log *zap.Logger) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		// Call handler
		resp, err := handler(ctx, req)

		// Log request
		if err != nil {
			log.Error("gRPC request failed",
				zap.String("method", info.FullMethod),
				zap.Error(err),
			)
		} else {
			log.Info("gRPC request completed",
				zap.String("method", info.FullMethod),
			)
		}

		return resp, err
	}
}
