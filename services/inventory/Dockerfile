# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install protoc and Go plugins (using versions compatible with Go 1.22)
RUN apk add --no-cache git protobuf-dev protoc && \
    go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.2 && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0

# Copy go mod files
COPY services/inventory/go.mod ./

# Copy source code
COPY services/inventory/ .

# Copy proto files and compile them
COPY contracts/proto /contracts/proto
RUN mkdir -p /contracts/gen/go && \
    protoc \
    --proto_path=/contracts/proto \
    --go_out=/contracts/gen/go \
    --go_opt=module=github.com/bookstore/contracts/gen/go \
    --go-grpc_out=/contracts/gen/go \
    --go-grpc_opt=module=github.com/bookstore/contracts/gen/go \
    /contracts/proto/common.proto \
    /contracts/proto/inventory.proto && \
    printf 'module github.com/bookstore/contracts/gen/go/inventory\n\ngo 1.22\n\nrequire (\n\tgoogle.golang.org/grpc v1.67.0\n\tgoogle.golang.org/protobuf v1.34.2\n)\n' > /contracts/gen/go/inventory/go.mod

# Download dependencies and generate go.sum (now that protobufs exist)
RUN go mod download && go mod tidy

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o inventoryd ./cmd/inventoryd

# Runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates wget

WORKDIR /root/

# Copy binary from builder
COPY --from=builder /app/inventoryd .

EXPOSE 50055 8083

CMD ["./inventoryd"]
