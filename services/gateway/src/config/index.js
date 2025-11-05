require('dotenv').config();
const path = require('path');

const config = {
  // Server
  port: process.env.PORT || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',

  // Service URLs (gRPC)
  services: {
    user: process.env.USER_SERVICE_URL || 'localhost:50054',
    order: process.env.ORDER_SERVICE_URL || 'localhost:50053',
    cart: process.env.CART_SERVICE_URL || 'localhost:50052',
    catalog: process.env.CATALOG_SERVICE_URL || 'localhost:50051',
    inventory: process.env.INVENTORY_SERVICE_URL || 'localhost:50055',
    payment: process.env.PAYMENT_SERVICE_URL || 'localhost:50056',
  },

  // Proto files
  protoPath: process.env.PROTO_PATH || path.join(__dirname, '..', '..', 'contracts', 'proto'),

  // Authentication
  jwt: {
    secret: process.env.JWT_SECRET || 'dev-secret-change-me',
    expiration: process.env.JWT_EXPIRATION || '24h',
  },

  // CORS
  cors: {
    origin: process.env.CORS_ORIGIN 
      ? process.env.CORS_ORIGIN.split(',')
      : true, // Permitir todos los orígenes en desarrollo
    credentials: true,
  },

  // Rate Limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
    max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,
  },

  // Logging
  logLevel: process.env.LOG_LEVEL || 'info',
};

module.exports = config;

