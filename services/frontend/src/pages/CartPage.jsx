import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'
import { createOrder } from '../api/order.api'
import { removeFromCart } from '../api/cart.api'
import { useState } from 'react'

function CartPage() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuthStore()
  const { items, total, updateQuantity, removeItem, clearCart } = useCartStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleQuantityChange = (bookId, newQuantity) => {
    if (newQuantity < 1) return
    updateQuantity(bookId, newQuantity)
  }

  const handleRemove = async (bookId) => {
    try {
      if (isAuthenticated) {
        await removeFromCart(null, bookId) // El API Gateway usa el token JWT
      }
      removeItem(bookId)
    } catch (err) {
      console.error('Error al remover item:', err)
      // Remover del store local incluso si falla en el backend
      removeItem(bookId)
    }
  }

  const handleCheckout = async () => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }

    try {
      setLoading(true)
      setError('')
      setSuccess('')

      // Crear orden sin pago automático
      const orderData = {
        items: items.map(item => ({
          product_id: item.bookId,  // SKU del libro
          quantity: item.quantity,
          price: item.price,  // Precio en dólares (el Gateway lo convertirá a centavos)
          currency: 'USD'
        })),
        payment_method: 'credit_card',  // Método de pago por defecto
        address: 'Default shipping address'  // Dirección por defecto (TODO: hacer formulario)
      }

      const order = await createOrder(orderData)
      const orderId = order.order?.order_id
      
      if (!orderId) {
        throw new Error('No se recibió ID de orden')
      }

      // Limpiar carrito después de crear la orden exitosamente
      clearCart()
      
      setSuccess(`¡Orden creada exitosamente! ID: ${orderId}`)
      
      // Redirigir a órdenes para que el usuario pueda pagar
      setTimeout(() => {
        navigate('/orders')
      }, 1500)
    } catch (err) {
      setError(err.message || 'Error al procesar la compra')
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div>
        <h1>Carrito de Compras</h1>
        <div className="card">
          <p>Debes iniciar sesión para ver tu carrito.</p>
          <button onClick={() => navigate('/login')} className="btn-primary">
            Iniciar Sesión
          </button>
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div>
        <h1>Carrito de Compras</h1>
        <div className="card">
          <p>Tu carrito está vacío.</p>
          <button onClick={() => navigate('/catalog')} className="btn-primary">
            Ir al Catálogo
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1>Carrito de Compras</h1>
      
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}
      
      <div style={{ marginTop: '2rem' }}>
        {items.map((item) => (
          <div key={item.bookId} className="cart-item">
            <div className="cart-item-info">
              <h3>{item.title}</h3>
              <p className="cart-item-price">Precio unitario: ${item.price?.toFixed(2)}</p>
              <div className="quantity-selector" style={{ marginTop: '0.75rem' }}>
                <label>Cantidad: </label>
                <input
                  type="number"
                  min="1"
                  value={item.quantity}
                  onChange={(e) => handleQuantityChange(item.bookId, parseInt(e.target.value))}
                  className="quantity-input"
                  style={{ width: '70px', marginLeft: '0.5rem' }}
                />
              </div>
            </div>
            <div className="cart-item-actions">
              <p className="cart-item-total">
                ${(item.price * item.quantity).toFixed(2)}
              </p>
              <button 
                onClick={() => handleRemove(item.bookId)} 
                className="btn-danger"
              >
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="cart-summary">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0 }}>Total:</h2>
          <span className="cart-total">${total.toFixed(2)}</span>
        </div>
        <button 
          onClick={handleCheckout} 
          disabled={loading}
          className="btn-success"
          style={{ width: '100%', padding: '1rem', fontSize: '1.1rem' }}
        >
          {loading ? 'Procesando...' : 'Finalizar Compra'}
        </button>
      </div>
    </div>
  )
}

export default CartPage
