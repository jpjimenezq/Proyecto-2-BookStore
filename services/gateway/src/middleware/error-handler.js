/**
 * Global error handling middleware
 */
const errorHandler = (err, req, res, next) => {
  console.error(' [Error Handler]:', err);

  // gRPC error from our client
  if (err.status && err.message) {
    return res.status(err.status).json({
      error: err.message,
      code: err.code,
      path: req.path,
    });
  }

  // JWT error
  if (err.name === 'JsonWebTokenError') {
    return res.status(401).json({
      error: 'Invalid token',
      message: err.message,
    });
  }

  // JWT expired error
  if (err.name === 'TokenExpiredError') {
    return res.status(401).json({
      error: 'Token expired',
      message: 'Please login again',
    });
  }

  // Validation error
  if (err.name === 'ValidationError') {
    return res.status(400).json({
      error: 'Validation error',
      details: err.details || err.message,
    });
  }

  // Default error
  res.status(err.status || 500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'An unexpected error occurred',
  });
};

/**
 * Handle 404 errors
 */
const notFoundHandler = (req, res) => {
  res.status(404).json({
    error: 'Not found',
    message: `Route ${req.method} ${req.path} not found`,
    availableRoutes: {
      auth: 'POST /api/auth/register, POST /api/auth/login',
      users: 'GET /api/users/:id',
      catalog: 'GET /api/catalog/books, GET /api/catalog/books/:sku',
      cart: 'GET /api/cart, POST /api/cart/items, DELETE /api/cart/items/:sku',
      orders: 'GET /api/orders, POST /api/orders, GET /api/orders/:id',
    }
  });
};

module.exports = {
  errorHandler,
  notFoundHandler,
};

