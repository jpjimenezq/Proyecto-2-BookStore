import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { listOrders, cancelOrder } from '../api/order.api'
import { processPayment } from '../api/payment.api'

function OrdersPage() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuthStore()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    loadOrders()
  }, [isAuthenticated, navigate])

  const loadOrders = async () => {
    try {
      setLoading(true)
      const data = await listOrders()
      console.log('Orders data received:', data)
      
      // Mapear los datos del backend al formato esperado por el frontend
      const mappedOrders = (data.orders || data || []).map(order => ({
        id: order.order_id || order.id,
        userId: order.user_id || order.userId,
        status: order.status?.toLowerCase() || 'created',
        totalAmount: order.total_amount?.amount || order.totalAmount || 0,
        createdAt: order.created_at 
          ? new Date(order.created_at * 1000).toISOString() // Timestamp en segundos
          : order.createdAt || new Date().toISOString(),
        items: order.items || [] // Items pueden venir vacíos desde GetOrdersByUser
      }))
      
      console.log('Mapped orders:', mappedOrders)
      setOrders(mappedOrders)
    } catch (err) {
      console.error('Error loading orders:', err)
      setError(err.message || 'Error al cargar las órdenes')
    } finally {
      setLoading(false)
    }
  }

  const handleCancelOrder = async (orderId) => {
    if (!window.confirm('¿Estás seguro de cancelar esta orden?')) {
      return
    }

    try {
      await cancelOrder(orderId)
      // Recargar órdenes
      loadOrders()
    } catch (err) {
      alert(err.message || 'Error al cancelar la orden')
    }
  }

  const handlePayOrder = async (order) => {
    if (!window.confirm(`¿Procesar pago de $${order.totalAmount?.toFixed(2)}?`)) {
      return
    }

    try {
      setLoading(true)
      setError('')

      // Calcular monto total en centavos
      const totalCents = Math.round((order.totalAmount || 0) * 100)
      
      const paymentData = {
        order_id: order.id,
        amount: {
          amount: totalCents,
          currency: 'USD',
          decimal_places: 2
        },
        method: {
          type: 'CREDIT_CARD',
          last4: '4242',  // Simulación de tarjeta
          token: 'tok_visa'  // Token simulado
        }
      }

      await processPayment(paymentData)
      
      alert(`¡Pago completado! Orden ${order.id} actualizada a COMPLETED`)
      
      // Recargar órdenes para ver el cambio de estado
      loadOrders()
    } catch (err) {
      setError(err.message || 'Error al procesar el pago')
      alert(err.message || 'Error al procesar el pago')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status) => {
    const statusClasses = {
      created: 'status-badge status-pending',
      pending: 'status-badge status-pending',
      completed: 'status-badge status-confirmed',
      confirmed: 'status-badge status-confirmed',
      shipped: 'status-badge status-shipped',
      delivered: 'status-badge status-delivered',
      cancelled: 'status-badge status-cancelled'
    }
    
    const statusLabels = {
      created: 'PENDIENTE PAGO',
      completed: 'PAGADO',
      pending: 'PENDIENTE',
      confirmed: 'PAGADO',
      shipped: 'ENVIADO',
      delivered: 'ENTREGADO',
      cancelled: 'CANCELADO'
    }
    
    return (
      <span className={statusClasses[status] || 'status-badge'}>
        {statusLabels[status] || status.toUpperCase()}
      </span>
    )
  }

  if (loading) {
    return <div className="loading">Cargando órdenes...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div>
      <h1>Mis Órdenes</h1>
      
      {orders.length === 0 ? (
        <div className="card">
          <p>No tienes órdenes aún.</p>
          <button onClick={() => navigate('/catalog')} className="btn-primary">
            Ir al Catálogo
          </button>
        </div>
      ) : (
        <div style={{ marginTop: '2rem' }}>
          {orders.map((order) => (
            <div key={order.id} className="order-item">
              <div className="order-header">
                <div className="order-info">
                  <h3>Orden #{order.id}</h3>
                  <p><strong>Fecha:</strong> {new Date(order.createdAt).toLocaleDateString()}</p>
                  <p><strong>Estado:</strong> {getStatusBadge(order.status)}</p>
                  <p style={{ fontSize: '1.2rem', color: '#69f0ae', marginTop: '0.5rem' }}>
                    <strong>Total:</strong> ${order.totalAmount?.toFixed(2)}
                  </p>
                </div>
                
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {order.status === 'created' && (
                    <button 
                      onClick={() => handlePayOrder(order)}
                      className="btn-success"
                      disabled={loading}
                    >
                      Pagar Ahora
                    </button>
                  )}
                  {order.status === 'created' && (
                    <button 
                      onClick={() => handleCancelOrder(order.id)}
                      className="btn-danger"
                      disabled={loading}
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </div>
              
              <div className="order-items-list">
                <strong>Items:</strong>
                {order.items && order.items.length > 0 ? (
                  <ul>
                    {order.items.map((item, index) => (
                      <li key={index}>
                        {item.product_id || item.bookId || 'N/A'} - 
                        Cantidad: {item.quantity} - 
                        ${((item.unit_price?.amount || item.price || 0) * item.quantity).toFixed(2)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ color: 'rgba(255, 255, 255, 0.5)', fontStyle: 'italic' }}>
                    Información de items no disponible en el resumen
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default OrdersPage
