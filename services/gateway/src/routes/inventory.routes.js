const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { authenticateToken, optionalAuth, requireAdmin } = require('../middleware/auth');

/**
 * GET /api/inventory/items/:itemId
 * Get item details
 */
router.get('/items/:itemId', optionalAuth, async (req, res, next) => {
  try {
    const { itemId } = req.params;

    const response = await grpcClient.call('inventory', 'GetItem', {
      item_id: itemId
    });

    if (!response.item) {
      return res.status(404).json({
        error: 'Item not found',
        item_id: itemId
      });
    }

    res.json({
      item_id: response.item.item_id,
      name: response.item.name,
      category: response.item.category,
      quantity: response.item.quantity,
      price: response.item.price,
      available: response.item.quantity > 0
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/inventory/check-availability
 * Check stock availability for an item
 * Body: { item_id: string, quantity: number }
 */
router.post('/check-availability', optionalAuth, async (req, res, next) => {
  try {
    const { item_id, quantity } = req.body;

    if (!item_id || !quantity) {
      return res.status(400).json({
        error: 'Missing required fields',
        required: ['item_id', 'quantity']
      });
    }

    const response = await grpcClient.call('inventory', 'CheckAvailability', {
      item_id,
      requested_quantity: parseInt(quantity)
    });

    res.json({
      item_id,
      requested_quantity: quantity,
      available: response.available,
      available_quantity: response.available_quantity,
      message: response.message
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/inventory/reserve
 * Reserve stock for an order (requires authentication)
 * Body: { order_id: string, items: [{ item_id: string, quantity: number }] }
 */
router.post('/reserve', authenticateToken, async (req, res, next) => {
  try {
    const { order_id, items } = req.body;

    if (!order_id || !items || !Array.isArray(items)) {
      return res.status(400).json({
        error: 'Missing required fields',
        required: {
          order_id: 'string',
          items: '[{ item_id: string, quantity: number }]'
        }
      });
    }

    const response = await grpcClient.call('inventory', 'ReserveStock', {
      order_id,
      items: items.map(item => ({
        item_id: item.item_id,
        quantity: parseInt(item.quantity)
      }))
    });

    res.json({
      success: response.success,
      message: response.message,
      order_id,
      failed_items: response.failed_items || []
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/inventory/release
 * Release reserved stock (requires authentication)
 * Body: { order_id: string, items: [{ item_id: string, quantity: number }] }
 */
router.post('/release', authenticateToken, async (req, res, next) => {
  try {
    const { order_id, items } = req.body;

    if (!order_id || !items || !Array.isArray(items)) {
      return res.status(400).json({
        error: 'Missing required fields',
        required: {
          order_id: 'string',
          items: '[{ item_id: string, quantity: number }]'
        }
      });
    }

    const response = await grpcClient.call('inventory', 'ReleaseStock', {
      order_id,
      items: items.map(item => ({
        item_id: item.item_id,
        quantity: parseInt(item.quantity)
      }))
    });

    res.json({
      success: response.success,
      message: response.message,
      order_id
    });
  } catch (error) {
    next(error);
  }
});

/**
 * PATCH /api/inventory/items/:itemId/stock
 * Update stock manually (Admin only)
 * Body: { delta: number } - positive to add, negative to subtract
 */
router.patch('/items/:itemId/stock', authenticateToken, requireAdmin, async (req, res, next) => {
  try {
    const { itemId } = req.params;
    const { delta } = req.body;

    if (delta === undefined || delta === null) {
      return res.status(400).json({
        error: 'Missing required field: delta',
        description: 'delta should be a positive or negative integer'
      });
    }

    const response = await grpcClient.call('inventory', 'UpdateStock', {
      item_id: itemId,
      delta: parseInt(delta)
    });

    res.json({
      success: response.success,
      message: response.message,
      item_id: itemId,
      new_quantity: response.new_quantity,
      delta: delta
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
