import { useState } from 'react'
import { useCartStore } from '../store/cartStore'
import { useAuthStore } from '../store/authStore'

function BookCard({ book }) {
  const addItem = useCartStore((state) => state.addItem)
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  
  // Stock viene directamente del catálogo (que consulta a inventory en tiempo real)
  const stock = book.stock !== undefined ? book.stock : 0
  const hasStock = stock > 0

  const handleAddToCart = async () => {
    try {
      setLoading(true)
      setMessage('')

      // Verificar que hay stock disponible
      if (!hasStock) {
        setMessage('Producto sin stock disponible')
        return
      }
      
      if (quantity > stock) {
        setMessage(`Solo hay ${stock} unidades disponibles`)
        return
      }

      // Agregar al carrito
      addItem({
        bookId: book.sku,
        title: book.title,
        price: book.price?.amount || 0,
        quantity: quantity
      })

      setMessage('Agregado al carrito exitosamente')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage(error.message || 'Error al agregar al carrito')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card book-card">
      <div className="card-header">{book.title}</div>
      
      <div className="book-details">
        <p><strong>Autor:</strong> {book.author}</p>
        {isAdmin && <p><strong>SKU:</strong> {book.sku}</p>}
        <p className="book-price">
          <strong>Precio:</strong> 
          <span className="price-value">
            ${book.price?.amount?.toFixed(2) || 'N/A'}
            {book.price?.currency && <span className="currency"> {book.price.currency}</span>}
          </span>
        </p>
        {book.description && <p className="book-description">{book.description}</p>}
        
        {/* Stock indicator */}
        <p className="book-stock">
          <strong>Stock disponible:</strong> 
          <span className={`stock-value ${stock === 0 ? 'out-of-stock' : stock < 10 ? 'low-stock' : 'in-stock'}`}>
            {hasStock ? `${stock} en stock` : 'Agotado'}
          </span>
        </p>
      </div>
      
      <div className="book-actions">
        <div className="quantity-selector">
          <label htmlFor={`quantity-${book.sku}`}>Cantidad:</label>
          <input
            id={`quantity-${book.sku}`}
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            className="quantity-input"
          />
        </div>
        <button 
          onClick={handleAddToCart} 
          disabled={loading || !hasStock}
          className="btn-primary add-to-cart-btn"
        >
          {loading ? 'Agregando...' : !hasStock ? 'Sin Stock' : 'Agregar al Carrito'}
        </button>
      </div>
      
      {message && (
        <p className={message.includes('exitosamente') ? 'success-message' : 'error-message'}>
          {message}
        </p>
      )}
    </div>
  )
}

export default BookCard
