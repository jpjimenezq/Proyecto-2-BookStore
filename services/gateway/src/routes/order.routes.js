const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { authenticateToken } = require('../middleware/auth');

/**
 * POST /api/orders
 * Create a new order
 */
router.post('/', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;
    const { items, payment_method, address } = req.body;

    if (!items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Items array is required and must not be empty'
      });
    }

    if (!payment_method) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Payment method is required'
      });
    }

    if (!address) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Shipping address is required'
      });
    }

    // Convert items to gRPC format (with Money type)
    const grpcItems = items.map(item => ({
      product_id: item.product_id || item.sku,
      quantity: parseInt(item.quantity || item.qty),
      unit_price: {
        currency: item.currency || 'USD',
        amount: Math.round((item.price || item.unit_price) * 100), // Convert to cents
        decimal_places: 2
      }
    }));

    const response = await grpcClient.call('order', 'CreateOrder', {
      user_id,
      items: grpcItems,
      payment_method,
      address
    });

    res.status(201).json({
      message: 'Order created successfully',
      order: {
        order_id: response.order_id,
        status: response.status,
        total_amount: {
          amount: response.total_amount.amount / 100,
          currency: response.total_amount.currency
        }
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/orders/:id
 * Get order by ID
 */
router.get('/:id', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;

    const response = await grpcClient.call('order', 'GetOrder', {
      order_id: id
    });

    // Check if user owns this order
    if (response.user_id !== req.user.user_id) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You can only view your own orders'
      });
    }

    const order = {
      order_id: response.order_id,
      user_id: response.user_id,
      items: response.items.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: {
          amount: item.unit_price.amount / 100,
          currency: item.unit_price.currency
        }
      })),
      payment_method: response.payment_method,
      address: response.address,
      status: response.status,
      total_amount: {
        amount: response.total_amount.amount / 100,
        currency: response.total_amount.currency
      },
      created_at: response.created_at
    };

    res.json(order);
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/orders
 * Get user's orders with pagination
 */
router.get('/', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;
    const { page = 1, page_size = 10 } = req.query;

    const response = await grpcClient.call('order', 'GetOrdersByUser', {
      user_id,
      page: parseInt(page),
      page_size: parseInt(page_size)
    });

    const orders = response.orders.map(order => ({
      order_id: order.order_id,
      user_id: order.user_id,
      total_amount: {
        amount: order.total_amount.amount / 100,
        currency: order.total_amount.currency
      },
      status: order.status,
      created_at: order.created_at,
      items: order.items ? order.items.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: {
          amount: item.unit_price.amount / 100,
          currency: item.unit_price.currency
        }
      })) : []
    }));

    res.json({
      orders,
      total_count: response.total_count,
      user_id: response.user_id
    });
  } catch (error) {
    next(error);
  }
});

/**
 * PATCH /api/orders/:id/cancel
 * Cancel an order
 */
router.patch('/:id/cancel', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;

    // First get the order to verify ownership
    const orderResponse = await grpcClient.call('order', 'GetOrder', {
      order_id: id
    });

    // Check if user owns this order
    if (orderResponse.user_id !== req.user.user_id) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You can only cancel your own orders'
      });
    }

    // Check if order can be cancelled
    if (orderResponse.status === 'CANCELLED') {
      return res.status(400).json({
        error: 'Invalid operation',
        message: 'Order is already cancelled'
      });
    }

    if (orderResponse.status === 'DELIVERED') {
      return res.status(400).json({
        error: 'Invalid operation',
        message: 'Cannot cancel a delivered order'
      });
    }

    // Cancel the order
    const response = await grpcClient.call('order', 'UpdateOrderStatus', {
      order_id: id,
      status: 'CANCELLED'
    });

    res.json({
      message: 'Order cancelled successfully',
      order_id: response.order_id,
      status: response.status,
      success: response.success
    });
  } catch (error) {
    next(error);
  }
});

/**
 * PATCH /api/orders/:id/status
 * Update order status (admin only)
 */
router.patch('/:id/status', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    if (!status) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Status is required'
      });
    }

    // Validate status
    const validStatuses = ['CREATED', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED'];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({
        error: 'Validation error',
        message: `Status must be one of: ${validStatuses.join(', ')}`
      });
    }

    const response = await grpcClient.call('order', 'UpdateOrderStatus', {
      order_id: id,
      status
    });

    res.json({
      message: 'Order status updated',
      order_id: response.order_id,
      status: response.status,
      success: response.success
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;

