import apiClient from './client'

/**
 * Authorize a payment (reserve funds)
 * @param {Object} paymentData
 * @param {string} paymentData.order_id - Order ID
 * @param {Object} paymentData.amount - Amount object
 * @param {number} paymentData.amount.amount - Amount in cents
 * @param {string} paymentData.amount.currency - Currency code (e.g., 'USD')
 * @param {number} paymentData.amount.decimal_places - Decimal places (usually 2)
 * @param {Object} paymentData.method - Payment method
 * @param {string} paymentData.method.type - Type: CREDIT_CARD, DEBIT_CARD, PAYPAL, etc.
 * @param {string} paymentData.method.last4 - Last 4 digits
 * @param {string} paymentData.method.token - Payment token
 * @returns {Promise<Object>} Payment authorization response
 */
export const authorizePayment = async (paymentData) => {
  try {
    const response = await apiClient.post('/api/payments/authorize', paymentData)
    return response.data
  } catch (error) {
    console.error('Error authorizing payment:', error)
    throw new Error(error.response?.data?.message || 'Error al autorizar el pago')
  }
}

/**
 * Capture an authorized payment (charge funds)
 * @param {string} paymentId - Payment ID
 * @returns {Promise<Object>} Payment capture response
 */
export const capturePayment = async (paymentId) => {
  try {
    const response = await apiClient.post(`/api/payments/${paymentId}/capture`)
    return response.data
  } catch (error) {
    console.error('Error capturing payment:', error)
    throw new Error(error.response?.data?.message || 'Error al capturar el pago')
  }
}

/**
 * Get payment details
 * @param {string} paymentId - Payment ID
 * @returns {Promise<Object>} Payment details
 */
export const getPayment = async (paymentId) => {
  try {
    const response = await apiClient.get(`/api/payments/${paymentId}`)
    return response.data
  } catch (error) {
    console.error('Error getting payment:', error)
    throw new Error(error.response?.data?.message || 'Error al obtener información del pago')
  }
}

/**
 * Process complete payment (authorize + capture)
 * This is a convenience function that combines authorize and capture
 * @param {Object} paymentData - Payment data for authorization
 * @returns {Promise<Object>} Final payment status
 */
export const processPayment = async (paymentData) => {
  try {
    // Step 1: Authorize payment
    const authResponse = await authorizePayment(paymentData)
    const paymentId = authResponse.payment?.payment_id
    
    if (!paymentId) {
      throw new Error('No se recibió ID de pago')
    }

    // Step 2: Capture payment
    const captureResponse = await capturePayment(paymentId)
    
    return {
      ...captureResponse,
      payment_id: paymentId
    }
  } catch (error) {
    console.error('Error processing payment:', error)
    throw error
  }
}
