const jwt = require('jsonwebtoken');
const config = require('../config');

/**
 * Middleware to verify JWT token
 */
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({
      error: 'Access token required',
      message: 'Please provide a valid Bearer token in Authorization header'
    });
  }

  jwt.verify(token, config.jwt.secret, (err, user) => {
    if (err) {
      return res.status(403).json({
        error: 'Invalid token',
        message: 'The provided token is invalid or expired'
      });
    }

    req.user = user; // Attach user info to request
    next();
  });
};

/**
 * Optional authentication - doesn't fail if no token
 */
const optionalAuth = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (token) {
    jwt.verify(token, config.jwt.secret, (err, user) => {
      if (!err) {
        req.user = user;
      }
    });
  }

  next();
};

/**
 * Middleware to check if user is admin
 */
const requireAdmin = (req, res, next) => {
  if (!req.user) {
    return res.status(401).json({
      error: 'Authentication required',
      message: 'Please authenticate to access this resource'
    });
  }

  if (req.user.role !== 'ADMIN') {
    return res.status(403).json({
      error: 'Forbidden',
      message: 'This action requires administrator privileges'
    });
  }

  next();
};

/**
 * Middleware to check if user is admin or the owner of the resource
 */
const requireAdminOrOwner = (userIdParam = 'id') => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        error: 'Authentication required',
        message: 'Please authenticate to access this resource'
      });
    }

    const requestedUserId = req.params[userIdParam];
    
    // Allow if user is admin or accessing their own resource
    if (req.user.role === 'ADMIN' || req.user.user_id === requestedUserId) {
      next();
    } else {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You do not have permission to access this resource'
      });
    }
  };
};

/**
 * Generate JWT token
 */
const generateToken = (payload) => {
  return jwt.sign(payload, config.jwt.secret, {
    expiresIn: config.jwt.expiration
  });
};

module.exports = {
  authenticateToken,
  optionalAuth,
  requireAdmin,
  requireAdminOrOwner,
  generateToken,
};

