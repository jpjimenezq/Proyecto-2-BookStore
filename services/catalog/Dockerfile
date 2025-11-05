# Build stage
FROM golang:1.24-alpine AS builder

# Install build dependencies including protoc
RUN apk add --no-cache git make protobuf-dev protoc

# Install Go protoc plugins (using specific versions for reproducibility)
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.2 && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.5.1

# Set working directory
WORKDIR /build

# Copy go mod files first
COPY services/catalog/go.mod services/catalog/go.sum ./

# Copy source code
COPY services/catalog/ ./

# Copy proto files and compile them
COPY contracts/proto ../contracts/proto
RUN mkdir -p ../contracts/gen/go && \
    protoc \
    --proto_path=../contracts/proto \
    --go_out=../contracts/gen/go \
    --go_opt=module=github.com/bookstore/contracts/gen/go \
    --go-grpc_out=../contracts/gen/go \
    --go-grpc_opt=module=github.com/bookstore/contracts/gen/go \
    ../contracts/proto/common.proto \
    ../contracts/proto/catalog.proto \
    ../contracts/proto/inventory.proto && \
    printf 'module github.com/bookstore/contracts/gen/go/catalog\n\ngo 1.24.0\n\nrequire (\n\tgoogle.golang.org/grpc v1.76.0\n\tgoogle.golang.org/protobuf v1.34.2\n)\n' > ../contracts/gen/go/catalog/go.mod && \
    printf 'module github.com/bookstore/contracts/gen/go/common\n\ngo 1.24.0\n\nrequire (\n\tgoogle.golang.org/grpc v1.76.0\n\tgoogle.golang.org/protobuf v1.34.2\n)\n' > ../contracts/gen/go/common/go.mod && \
    printf 'module github.com/bookstore/contracts/gen/go/inventory\n\ngo 1.24.0\n\nrequire (\n\tgoogle.golang.org/grpc v1.76.0\n\tgoogle.golang.org/protobuf v1.34.2\n)\n' > ../contracts/gen/go/inventory/go.mod

# Download dependencies and update go.mod/go.sum
RUN go mod download && go mod tidy

# Build the application
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s" \
    -o /build/catalogd \
    ./cmd/catalogd

# Runtime stage
FROM alpine:3.19

# Install ca-certificates for HTTPS
RUN apk add --no-cache ca-certificates tzdata

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/catalogd /app/catalogd

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 50051 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/healthz || exit 1

# Run the application
ENTRYPOINT ["/app/catalogd"]


