const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { authenticateToken } = require('../middleware/auth');

/**
 * GET /api/cart
 * Get user's cart
 */
router.get('/', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;

    const response = await grpcClient.call('cart', 'GetCart', { user_id });

    const cart = response.cart ? {
      user_id: response.cart.user_id,
      items: response.cart.items.map(item => ({
        sku: item.sku,
        qty: item.qty,
        price: {
          amount: item.price.amount / 100,
          currency: item.price.currency
        },
        title: item.title
      })),
      total: {
        amount: response.cart.total.amount / 100,
        currency: response.cart.total.currency
      },
      updated_at: response.cart.updated_at
    } : { user_id, items: [], total: { amount: 0, currency: 'USD' } };

    res.json(cart);
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/cart/items
 * Add item to cart
 */
router.post('/items', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;
    const { sku, qty } = req.body;

    if (!sku || !qty) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'SKU and quantity are required'
      });
    }

    if (qty <= 0) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Quantity must be positive'
      });
    }

    const response = await grpcClient.call('cart', 'AddItem', {
      user_id,
      sku,
      qty: parseInt(qty)
    });

    const cart = {
      user_id: response.cart.user_id,
      items: response.cart.items.map(item => ({
        sku: item.sku,
        qty: item.qty,
        price: {
          amount: item.price.amount / 100,
          currency: item.price.currency
        },
        title: item.title
      })),
      total: {
        amount: response.cart.total.amount / 100,
        currency: response.cart.total.currency
      },
      updated_at: response.cart.updated_at
    };

    res.json({
      message: 'Item added to cart',
      cart
    });
  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/cart/items/:sku
 * Remove item from cart
 */
router.delete('/items/:sku', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;
    const { sku } = req.params;

    const response = await grpcClient.call('cart', 'RemoveItem', {
      user_id,
      sku
    });

    const cart = {
      user_id: response.cart.user_id,
      items: response.cart.items.map(item => ({
        sku: item.sku,
        qty: item.qty,
        price: {
          amount: item.price.amount / 100,
          currency: item.price.currency
        },
        title: item.title
      })),
      total: {
        amount: response.cart.total.amount / 100,
        currency: response.cart.total.currency
      },
      updated_at: response.cart.updated_at
    };

    res.json({
      message: 'Item removed from cart',
      cart
    });
  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/cart
 * Clear cart
 */
router.delete('/', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;

    const response = await grpcClient.call('cart', 'ClearCart', { user_id });

    res.json({
      message: 'Cart cleared successfully',
      success: response.success
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;

