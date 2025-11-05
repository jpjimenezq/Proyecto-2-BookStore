const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');
const config = require('../config');

class GrpcClient {
  constructor() {
    this.clients = {};
    this.protoPath = config.protoPath;
  }

  /**
   * Load proto file and create gRPC client
   */
  loadProto(serviceName, protoFile, packageName, serviceDefinition) {
    try {
      const PROTO_PATH = path.join(this.protoPath, protoFile);
      
      const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
        keepCase: true,
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true,
        includeDirs: [this.protoPath]
      });

      const protoDescriptor = grpc.loadPackageDefinition(packageDefinition);
      
      // Navigate to the service (e.g., bookstore.user.UserService)
      const packagePath = packageName.split('.');
      let service = protoDescriptor;
      for (const part of packagePath) {
        service = service[part];
      }

      const serviceUrl = config.services[serviceName];
      const client = new service[serviceDefinition](
        serviceUrl,
        grpc.credentials.createInsecure()
      );

      this.clients[serviceName] = client;
      
      return client;
    } catch (error) {
      console.error(` [gRPC Client] Error loading ${serviceName}:`, error.message);
      throw error;
    }
  }

  /**
   * Initialize all service clients
   */
  initializeAll() {
    try {
      // User Service
      this.loadProto('user', 'user.proto', 'bookstore.user', 'UserService');
      
      // Order Service
      this.loadProto('order', 'order.proto', 'bookstore.order', 'OrderService');
      
      // Cart Service
      this.loadProto('cart', 'cart.proto', 'bookstore.cart', 'CartService');
      
      // Catalog Service
      this.loadProto('catalog', 'catalog.proto', 'bookstore.catalog', 'CatalogService');

      // Inventory Service
      this.loadProto('inventory', 'inventory.proto', 'inventory', 'InventoryService');

      // Payment Service
      this.loadProto('payment', 'payment.proto', 'bookstore.payment', 'PaymentService');

    } catch (error) {
      console.error(' [gRPC Client] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Get client for a specific service
   */
  getClient(serviceName) {
    const client = this.clients[serviceName];
    if (!client) {
      throw new Error(`Service client '${serviceName}' not found. Available: ${Object.keys(this.clients).join(', ')}`);
    }
    return client;
  }

  /**
   * Make a gRPC call with promise wrapper and error handling
   */
  async call(serviceName, method, request) {
    const client = this.getClient(serviceName);
    
    return new Promise((resolve, reject) => {
      client[method](request, (error, response) => {
        if (error) {
          console.error(` [gRPC Call] ${serviceName}.${method} error:`, error.message);
          reject(this.handleGrpcError(error));
        } else {
          resolve(response);
        }
      });
    });
  }

  /**
   * Handle gRPC errors and convert to HTTP-friendly format
   */
  handleGrpcError(error) {
    const errorMap = {
      3: { status: 400, message: 'Invalid argument' },           // INVALID_ARGUMENT
      5: { status: 404, message: 'Not found' },                  // NOT_FOUND
      6: { status: 409, message: 'Already exists' },             // ALREADY_EXISTS
      7: { status: 403, message: 'Permission denied' },          // PERMISSION_DENIED
      16: { status: 401, message: 'Unauthenticated' },           // UNAUTHENTICATED
      14: { status: 503, message: 'Service unavailable' },       // UNAVAILABLE
      13: { status: 500, message: 'Internal server error' },     // INTERNAL
    };

    const grpcCode = error.code || 13;
    const httpError = errorMap[grpcCode] || { status: 500, message: 'Unknown error' };

    return {
      status: httpError.status,
      message: error.details || httpError.message,
      code: grpcCode,
    };
  }
}

// Singleton instance
const grpcClient = new GrpcClient();

module.exports = grpcClient;

