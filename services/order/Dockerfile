# Multi-stage build for Order Service (Python)

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies for building
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY services/order/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Install grpcio-tools for protobuf compilation
RUN pip install --user grpcio-tools

# Copy proto files and compile them (Order needs: order, cart, catalog, inventory, payment, common)
COPY contracts/proto /build/contracts/proto
RUN mkdir -p /build/contracts/gen/python && \
    python -m grpc_tools.protoc \
    --proto_path=/build/contracts/proto \
    --python_out=/build/contracts/gen/python \
    --grpc_python_out=/build/contracts/gen/python \
    /build/contracts/proto/common.proto \
    /build/contracts/proto/order.proto \
    /build/contracts/proto/cart.proto \
    /build/contracts/proto/catalog.proto \
    /build/contracts/proto/inventory.proto \
    /build/contracts/proto/payment.proto && \
    touch /build/contracts/gen/python/__init__.py && \
    sed -i 's/^import common_pb2/from . import common_pb2/g' /build/contracts/gen/python/*.py && \
    sed -i 's/^import \(order\|cart\|catalog\|inventory\|payment\)_pb2/from . import \1_pb2/g' /build/contracts/gen/python/*.py

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY services/order/order ./order
COPY services/order/cmd ./cmd

# Copy compiled proto files from builder stage
COPY --from=builder /build/contracts/gen/python /app/contracts/gen/python

# Set Python path and ownership
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

RUN chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${HTTP_HEALTH_PORT:-8082}/healthz || exit 1

# Expose ports
EXPOSE 50053 8082

# Start the service
CMD ["python", "cmd/start.py"]
