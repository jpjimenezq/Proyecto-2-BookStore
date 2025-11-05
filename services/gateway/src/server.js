const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const config = require('./config');
const grpcClient = require('./clients/grpc-client');
const { errorHandler, notFoundHandler } = require('./middleware/error-handler');

// Import routes
const authRoutes = require('./routes/auth.routes');
const userRoutes = require('./routes/user.routes');
const catalogRoutes = require('./routes/catalog.routes');
const cartRoutes = require('./routes/cart.routes');
const orderRoutes = require('./routes/order.routes');
const inventoryRoutes = require('./routes/inventory.routes');
const paymentRoutes = require('./routes/payment.routes');

// Initialize Express app
const app = express();

// Security middleware
app.use(helmet());

// CORS - Permitir todos los orígenes en desarrollo
app.use(cors({
  origin: function (origin, callback) {
    // Permitir peticiones sin origin (como Postman) y todas las peticiones en desarrollo
    callback(null, true);
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.max,
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

// Body parser
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Logging
if (config.nodeEnv === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'api-gateway',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    services: {
      user: config.services.user,
      order: config.services.order,
      cart: config.services.cart,
      catalog: config.services.catalog,
      inventory: config.services.inventory,
      payment: config.services.payment,
    }
  });
});

// API Documentation endpoint
app.get('/', (req, res) => {
  res.json({
    name: 'Bookstore API Gateway',
    version: '1.0.0',
    description: 'REST API Gateway for Bookstore Microservices',
    documentation: {
      endpoints: {
        health: 'GET /health',
        auth: {
          register: 'POST /api/auth/register',
          login: 'POST /api/auth/login',
          verify: 'POST /api/auth/verify'
        },
        users: {
          getUser: 'GET /api/users/:id',
          updateUser: 'PUT /api/users/:id',
          deleteUser: 'DELETE /api/users/:id'
        },
        catalog: {
          listBooks: 'GET /api/catalog/books',
          getBook: 'GET /api/catalog/books/:sku',
          searchBooks: 'GET /api/catalog/books/search?query=...'
        },
        cart: {
          getCart: 'GET /api/cart',
          addItem: 'POST /api/cart/items',
          removeItem: 'DELETE /api/cart/items/:sku',
          clearCart: 'DELETE /api/cart'
        },
        orders: {
          createOrder: 'POST /api/orders',
          getOrder: 'GET /api/orders/:id',
          listOrders: 'GET /api/orders',
          updateStatus: 'PATCH /api/orders/:id/status'
        },
        inventory: {
          getItem: 'GET /api/inventory/items/:itemId',
          checkAvailability: 'POST /api/inventory/check-availability',
          reserveStock: 'POST /api/inventory/reserve',
          releaseStock: 'POST /api/inventory/release',
          updateStock: 'PATCH /api/inventory/items/:itemId/stock'
        },
        payments: {
          authorize: 'POST /api/payments/authorize',
          capture: 'POST /api/payments/:paymentId/capture',
          getPayment: 'GET /api/payments/:paymentId'
        }
      }
    },
    links: {
      github: 'https://github.com/yourusername/bookstore-ms',
      docs: '/api-docs'
    }
  });
});

// Mount API routes
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
app.use('/api/catalog', catalogRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/orders', orderRoutes);
app.use('/api/inventory', inventoryRoutes);
app.use('/api/payments', paymentRoutes);

// Error handlers (must be last)
app.use(notFoundHandler);
app.use(errorHandler);

// Initialize gRPC clients
try {
  grpcClient.initializeAll();
} catch (error) {
  console.error('Failed to initialize gRPC clients:', error);
  process.exit(1);
}

// Start server
const PORT = config.port;
const server = app.listen(PORT, () => {
  console.log(`API Gateway running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  server.close(() => {
    process.exit(0);
  });
});

module.exports = app;

