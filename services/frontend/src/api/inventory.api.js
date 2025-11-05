import apiClient from './client'

/**
 * API para gestión de inventario
 */

// Obtener información de un item
export const getItem = async (itemId) => {
  const response = await apiClient.get(`/api/inventory/items/${itemId}`)
  return response.data
}

// Verificar disponibilidad de stock
export const checkAvailability = async (itemId, quantity) => {
  const response = await apiClient.post('/api/inventory/check-availability', {
    item_id: itemId,
    quantity
  })
  return response.data
}

// Reservar stock (requiere autenticación)
export const reserveStock = async (itemId, quantity, orderId) => {
  const response = await apiClient.post('/api/inventory/reserve', {
    item_id: itemId,
    quantity,
    order_id: orderId
  })
  return response.data
}

// Liberar stock (requiere autenticación)
export const releaseStock = async (itemId, quantity, orderId) => {
  const response = await apiClient.post('/api/inventory/release', {
    item_id: itemId,
    quantity,
    order_id: orderId
  })
  return response.data
}

// Actualizar stock (admin, requiere autenticación)
export const updateStock = async (itemId, delta) => {
  const response = await apiClient.patch(`/api/inventory/items/${itemId}/stock`, {
    delta: parseInt(delta)
  })
  return response.data
}
