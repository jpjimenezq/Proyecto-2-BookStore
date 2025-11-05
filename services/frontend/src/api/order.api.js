import apiClient from './client'

/**
 * API para gestión de órdenes
 */

// Crear una nueva orden
export const createOrder = async (orderData) => {
  const response = await apiClient.post('/api/orders', orderData)
  return response.data
}

// Obtener orden por ID
export const getOrder = async (orderId) => {
  const response = await apiClient.get(`/api/orders/${orderId}`)
  return response.data
}

// Listar órdenes del usuario (usa el user_id del token JWT)
export const listOrders = async () => {
  const response = await apiClient.get('/api/orders')
  return response.data
}

// Cancelar orden
export const cancelOrder = async (orderId) => {
  const response = await apiClient.patch(`/api/orders/${orderId}/cancel`)
  return response.data
}

// Actualizar estado de orden (admin)
export const updateOrderStatus = async (orderId, status) => {
  const response = await apiClient.patch(`/api/orders/${orderId}/status`, { status })
  return response.data
}
