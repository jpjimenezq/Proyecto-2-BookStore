const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { authenticateToken } = require('../middleware/auth');

/**
 * POST /api/payments/authorize
 * Authorize a payment (reserve funds)
 * 
 * Body:
 * {
 *   "order_id": "string",
 *   "amount": {
 *     "amount": 9999,  // Amount in cents
 *     "currency": "USD",
 *     "decimal_places": 2
 *   },
 *   "method": {
 *     "type": "CREDIT_CARD",  // CREDIT_CARD, DEBIT_CARD, PAYPAL, BANK_TRANSFER
 *     "last4": "4242",
 *     "token": "tok_visa"
 *   }
 * }
 */
router.post('/authorize', authenticateToken, async (req, res, next) => {
  try {
    const user_id = req.user.user_id;
    const { order_id, amount, method } = req.body;

    // Validate required fields
    if (!order_id || !amount || !method) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'order_id, amount, and method are required'
      });
    }

    // Call payment service via gRPC
    const response = await grpcClient.call('payment', 'Authorize', {
      order_id,
      amount: {
        amount: amount.amount,
        currency: amount.currency || 'USD',
        decimal_places: amount.decimal_places || 2
      },
      method: {
        type: method.type || 'CREDIT_CARD',
        last4: method.last4 || '',
        token: method.token || ''
      },
      user_id
    });

    res.status(201).json({
      message: 'Payment authorized successfully',
      payment: {
        payment_id: response.payment_id,
        status: response.status,
        message: response.message
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/payments/:paymentId/capture
 * Capture an authorized payment (charge funds)
 */
router.post('/:paymentId/capture', authenticateToken, async (req, res, next) => {
  try {
    const { paymentId } = req.params;

    const response = await grpcClient.call('payment', 'Capture', {
      payment_id: paymentId
    });

    res.json({
      message: 'Payment captured successfully',
      payment: {
        payment_id: response.payment_id,
        status: response.status,
        message: response.message,
        captured_at: response.captured_at
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/payments/:paymentId
 * Get payment details
 */
router.get('/:paymentId', authenticateToken, async (req, res, next) => {
  try {
    const { paymentId } = req.params;

    const response = await grpcClient.call('payment', 'GetPayment', {
      payment_id: paymentId
    });

    // Check if user owns this payment
    if (response.user_id !== req.user.user_id) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'You can only view your own payments'
      });
    }

    res.json({
      payment_id: response.payment_id,
      order_id: response.order_id,
      user_id: response.user_id,
      amount: {
        amount: response.amount.amount,
        currency: response.amount.currency,
        decimal_places: response.amount.decimal_places
      },
      method: {
        type: response.method.type,
        last4: response.method.last4
      },
      status: response.status,
      created_at: response.created_at,
      captured_at: response.captured_at
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
