# Build stage
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY services/payment/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Install grpcio-tools for protobuf compilation
RUN pip install --user grpcio-tools

# Copy proto files and compile them (Payment needs: payment, order, common)
COPY contracts/proto /build/contracts/proto
RUN mkdir -p /build/contracts/gen/python && \
    python -m grpc_tools.protoc \
    --proto_path=/build/contracts/proto \
    --python_out=/build/contracts/gen/python \
    --grpc_python_out=/build/contracts/gen/python \
    /build/contracts/proto/common.proto \
    /build/contracts/proto/payment.proto \
    /build/contracts/proto/order.proto && \
    touch /build/contracts/gen/python/__init__.py && \
    sed -i 's/^import common_pb2/from . import common_pb2/g' /build/contracts/gen/python/*.py && \
    sed -i 's/^import \(payment\|order\)_pb2/from . import \1_pb2/g' /build/contracts/gen/python/*.py

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY services/payment/payment ./payment
COPY services/payment/cmd ./cmd

# Copy compiled proto files from builder stage
COPY --from=builder /build/contracts/gen/python /app/contracts/gen/python

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add local packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 50056 8084

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8084/health || exit 1

# Run the application
CMD ["python", "cmd/start.py"]
