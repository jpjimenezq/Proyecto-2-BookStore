const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { generateToken } = require('../middleware/auth');

/**
 * POST /api/auth/register
 * Register a new user
 */
router.post('/register', async (req, res, next) => {
  try {
    const { username, password, email, role } = req.body;

    if (!username || !password) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Username and password are required'
      });
    }

    const registerRequest = {
      username,
      password
    };

    if (email) registerRequest.email = email;
    if (role) registerRequest.role = role;

    const response = await grpcClient.call('user', 'RegisterUser', registerRequest);

    if (response.status === 'ERROR') {
      return res.status(400).json({
        error: 'Registration failed',
        message: response.message
      });
    }

    // Generate JWT token
    const token = generateToken({
      user_id: response.user_id,
      username: response.username,
      email: response.email || '',
      role: response.role || 'CLIENT'
    });

    res.status(201).json({
      message: 'User registered successfully',
      user: {
        user_id: response.user_id,
        username: response.username,
        email: response.email || '',
        role: response.role || 'CLIENT'
      },
      token
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/login
 * Login user
 */
router.post('/login', async (req, res, next) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Username and password are required'
      });
    }

    const response = await grpcClient.call('user', 'LoginUser', {
      username,
      password
    });

    if (response.status === 'ERROR') {
      return res.status(401).json({
        error: 'Authentication failed',
        message: response.message
      });
    }

    res.json({
      message: 'Login successful',
      user: {
        user_id: response.user_id,
        username: response.username,
        email: response.email || '',
        role: response.role || 'CLIENT'
      },
      token: response.token
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/verify
 * Verify JWT token
 */
router.post('/verify', async (req, res, next) => {
  try {
    const { token } = req.body;

    if (!token) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Token is required'
      });
    }

    const response = await grpcClient.call('user', 'VerifyToken', { token });

    if (response.status === 'ERROR') {
      return res.status(401).json({
        error: 'Token invalid',
        message: response.message
      });
    }

    res.json({
      valid: true,
      user: {
        user_id: response.user_id,
        username: response.username,
        role: response.role || 'CLIENT'
      }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;

