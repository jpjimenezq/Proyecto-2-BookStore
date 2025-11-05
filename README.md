# Bookstore Microservices

A cloud-native microservices architecture for a bookstore application, built with gRPC, event-driven messaging, and Kubernetes.

## Architecture Overview

This monorepo contains a complete microservices ecosystem with:

- **Catalog Service**: Manages book inventory and catalog operations
- **Cart Service**: Handles shopping cart functionality
- **Shared Contracts**: Protocol Buffer definitions and event schemas
- **Infrastructure**: Kubernetes manifests for deployment

### Technology Stack

- **Communication**: gRPC (synchronous), RabbitMQ (asynchronous events)
- **Databases**: PostgreSQL (Catalog), MongoDB (Cart)
- **Container Orchestration**: Kubernetes
- **Languages**: Go, Python, Node.js (contracts support all three)

## Project Structure

```
bookstore-ms/
├── contracts/                 # Shared contracts
│   ├── proto/                # gRPC Protocol Buffers
│   │   ├── common.proto      # Shared types
│   │   ├── catalog.proto     # Catalog service
│   │   └── cart.proto        # Cart service
│   ├── events/               # Event schemas (JSON Schema)
│   │   ├── catalog.events.json
│   │   └── cart.events.json
│   ├── gen/                  # Generated code (gitignored)
│   └── README.md
├── services/
│   ├── catalog/              # Catalog microservice
│   └── cart/                 # Cart microservice
├── deploy/
│   └── k8s/                  # Kubernetes manifests
│       ├── namespace.yaml
│       ├── rabbitmq/         # RabbitMQ deployment
│       ├── postgres/         # PostgreSQL deployment
│       └── mongo/            # MongoDB deployment
├── Makefile                  # Build automation
├── .editorconfig            # Editor configuration
├── .gitattributes           # Git attributes
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Getting Started

### Prerequisites

Install the following tools:

- **Protocol Buffers Compiler**: [protoc](https://github.com/protocolbuffers/protobuf/releases)
- **Go** (1.21+): [golang.org](https://golang.org/dl/)
- **Python** (3.11+): [python.org](https://www.python.org/downloads/)
- **Node.js** (18+): [nodejs.org](https://nodejs.org/)
- **Docker** (20.10+): [docker.com](https://www.docker.com/)
- **Docker Compose** (2.0+): Included with Docker Desktop
- **Kubernetes** (optional): [kubectl](https://kubernetes.io/docs/tasks/tools/)
- **grpcurl** (optional, for testing): `brew install grpcurl` or [releases](https://github.com/fullstorydev/grpcurl/releases)

### Quick Start with Docker Compose (Recommended)

The fastest way to get started is using Docker Compose:

```bash
# 1. Generate proto stubs
cd bookstore-ms
make proto-gen-all

# 2. Start all services
make local-up

# 3. Wait for services to be healthy (about 30 seconds)
make local-health

# 4. Test the services
./scripts/test-local.sh
```

Services will be available at:
- **Catalog**: gRPC `localhost:50051`, HTTP `localhost:8080`
- **Cart**: gRPC `localhost:50052`, HTTP `localhost:8081`
- **RabbitMQ**: AMQP `localhost:5672`, UI `http://localhost:15672` (admin/changeme)
- **PostgreSQL**: `localhost:5432` (bookstore/changeme)
- **MongoDB**: `localhost:27017`

### Development Setup (Without Docker)

If you want to run services directly (for development):

1. **Clone the repository**:
```bash
git clone <repository-url>
cd bookstore-ms
```

2. **Set up development environment**:
```bash
make dev-setup
```

3. **Generate contract code**:
```bash
make proto-gen-all
```

4. **Start infrastructure** (PostgreSQL, MongoDB, RabbitMQ):
```bash
cd deploy/local
docker-compose up -d postgres mongo rabbitmq
```

5. **Run services**:
```bash
# Terminal 1 - Catalog service
cd services/catalog
make run-dev

# Terminal 2 - Cart service
cd services/cart
make run-dev
```

## Development Workflow

### Working with Contracts

The contracts are the source of truth for service communication:

1. **Modify proto files** in `contracts/proto/`
2. **Regenerate code**:
```bash
make proto-gen-go    # For Go services
make proto-gen-py    # For Python services
make proto-gen-node  # For Node.js services
```

3. **Update services** to use the new contracts

See [contracts/README.md](contracts/README.md) for detailed documentation.

### Building Services

```bash
# Build all services
make docker-build-all

# Build specific service
make docker-build-catalog
make docker-build-cart
```

### Running Tests

```bash
# Test contract generation
make test

# Test Go services
make test-go

# Test Python services
make test-py
```

### Linting

```bash
# Run all linters
make lint

# Lint specific components
make lint-proto
make lint-events
make lint-go
```

## Deployment

### Kubernetes Deployment

1. **Apply infrastructure**:
```bash
make k8s-apply
```

This will deploy:
- Bookstore namespace
- RabbitMQ cluster
- PostgreSQL database
- MongoDB database

2. **Verify deployment**:
```bash
kubectl get all -n bookstore
```

3. **Access services**:
```bash
# Port forward RabbitMQ management
kubectl port-forward -n bookstore svc/rabbitmq 15672:15672

# Port forward PostgreSQL
kubectl port-forward -n bookstore svc/postgres 5432:5432

# Port forward MongoDB
kubectl port-forward -n bookstore svc/mongo 27017:27017
```

### Cleanup

```bash
# Delete all Kubernetes resources
make k8s-delete

# Clean generated files
make clean
```

## Services

### Catalog Service

Manages the book catalog with CRUD operations.

- **Database**: PostgreSQL
- **Port**: 50051 (gRPC)
- **Events Published**:
  - `catalog.created`
  - `catalog.updated`
  - `catalog.deleted`

### Cart Service

Manages shopping carts for users.

- **Database**: MongoDB
- **Port**: 50052 (gRPC)
- **Events Published**:
  - `cart.item_added`
  - `cart.item_removed`
  - `cart.checkout_requested`
  - `cart.cleared`

## Event-Driven Architecture

Services communicate asynchronously via RabbitMQ:

- **Exchange**: `bookstore.events` (topic)
- **Routing**: `<service>.<event_type>`
- **Format**: JSON Schema validated

See [contracts/README.md](contracts/README.md) for event schema details.

## Configuration

### Default Credentials (Development Only)

**⚠️ Change these in production!**

- **RabbitMQ**: `admin / changeme`
- **PostgreSQL**: `bookstore / changeme`
- **MongoDB**: `admin / changeme`

### Environment Variables

Services can be configured via environment variables:

- `GRPC_PORT`: gRPC server port
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `DB_NAME`: Database name
- `RABBITMQ_URL`: RabbitMQ connection URL
- `LOG_LEVEL`: Logging level (debug, info, warn, error)









