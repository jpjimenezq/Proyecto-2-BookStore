import apiClient from './client'

/**
 * API para el carrito de compras
 * El API Gateway usa el user_id del token JWT automáticamente
 */

// Obtener el carrito del usuario (usa el token JWT)
export const getCart = async () => {
  const response = await apiClient.get('/api/cart')
  return response.data
}

// Agregar item al carrito
export const addToCart = async (itemData) => {
  // itemData debe contener: { sku, qty }
  const response = await apiClient.post('/api/cart/items', itemData)
  return response.data
}

// Actualizar cantidad de un item (no está implementado en el Gateway, usar addToCart)
export const updateCartItem = async (userId, itemId, quantity) => {
  // Por ahora, agregar más cantidad al item existente
  const response = await apiClient.post('/api/cart/items', { 
    sku: itemId, 
    qty: quantity 
  })
  return response.data
}

// Eliminar item del carrito
export const removeFromCart = async (userId, itemId) => {
  const response = await apiClient.delete(`/api/cart/items/${itemId}`)
  return response.data
}

// Limpiar el carrito
export const clearCart = async () => {
  const response = await apiClient.delete('/api/cart')
  return response.data
}
