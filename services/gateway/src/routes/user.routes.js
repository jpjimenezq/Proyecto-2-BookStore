const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { authenticateToken } = require('../middleware/auth');

/**
 * GET /api/users/:id
 * Get user by ID
 */
router.get('/:id', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;

    // Users can only view their own profile
    if (id !== req.user.user_id) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You can only view your own profile'
      });
    }

    const response = await grpcClient.call('user', 'GetUser', {
      user_id: id
    });

    res.json({
      user_id: response.user_id,
      username: response.username,
      created_at: response.created_at,
      updated_at: response.updated_at
    });
  } catch (error) {
    next(error);
  }
});

/**
 * PUT /api/users/:id
 * Update user
 */
router.put('/:id', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;
    const { username } = req.body;

    // Users can only update their own profile
    if (id !== req.user.user_id) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You can only update your own profile'
      });
    }

    if (!username) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Username is required'
      });
    }

    const response = await grpcClient.call('user', 'UpdateUser', {
      user_id: id,
      username
    });

    if (response.status === 'ERROR') {
      return res.status(400).json({
        error: 'Update failed',
        message: response.message
      });
    }

    res.json({
      message: 'User updated successfully',
      user_id: response.user_id
    });
  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/users/:id
 * Delete user
 */
router.delete('/:id', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;

    // Users can only delete their own account
    if (id !== req.user.user_id) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You can only delete your own account'
      });
    }

    const response = await grpcClient.call('user', 'DeleteUser', {
      user_id: id
    });

    if (response.status === 'ERROR') {
      return res.status(400).json({
        error: 'Delete failed',
        message: response.message
      });
    }

    res.json({
      message: 'User deleted successfully'
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;

