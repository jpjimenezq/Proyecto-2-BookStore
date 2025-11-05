import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { getItem, updateStock } from '../api/inventory.api'
import { createBook } from '../api/catalog.api'

function InventoryPage() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()
  const [itemId, setItemId] = useState('')
  const [item, setItem] = useState(null)
  const [newStock, setNewStock] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showCreateBook, setShowCreateBook] = useState(false)
  const [newBook, setNewBook] = useState({
    title: '',
    author: '',
    price: '',
    category: '',
    description: ''
  })

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
    } else if (user?.role !== 'ADMIN') {
      navigate('/')
    }
  }, [isAuthenticated, user, navigate])

  const handleSearchItem = async (e) => {
    e.preventDefault()
    
    if (!itemId.trim()) {
      setError('Ingresa un ID de item')
      return
    }

    try {
      setLoading(true)
      setError('')
      setSuccess('')
      
      const data = await getItem(itemId)
      setItem(data.item || data)
      setNewStock(data.item?.quantity || data.quantity || 0)
    } catch (err) {
      setError(err.message || 'Error al buscar el item')
      setItem(null)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateStock = async () => {
    if (!item) return

    try {
      setLoading(true)
      setError('')
      setSuccess('')
      
      // Calcular delta (diferencia entre nuevo stock y actual)
      const currentStock = item.quantity || 0
      const delta = newStock - currentStock
      
      await updateStock(item.itemId || item.item_id || item.id, delta)
      
      setSuccess(`Stock actualizado exitosamente! (${currentStock} → ${newStock})`)
      
      // Recargar item
      const data = await getItem(item.itemId || item.item_id || item.id)
      setItem(data.item || data)
      setNewStock(data.item?.quantity || data.quantity || 0)
    } catch (err) {
      setError(err.message || 'Error al actualizar el stock')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateBook = async (e) => {
    e.preventDefault()

    try {
      setLoading(true)
      setError('')
      setSuccess('')

      // No enviar SKU, se generará automáticamente en el backend
      const bookData = {
        title: newBook.title,
        author: newBook.author,
        price: parseFloat(newBook.price),
        category: newBook.category,
        description: newBook.description
      }

      const result = await createBook(bookData)
      
      setSuccess(`Libro creado exitosamente con SKU: ${result.book?.sku || 'generado'}`)
      setShowCreateBook(false)
      setNewBook({
        title: '',
        author: '',
        price: '',
        category: '',
        description: ''
      })
    } catch (err) {
      setError(err.message || 'Error al crear el libro')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1>Gestión de Inventario</h1>
        <button 
          onClick={() => setShowCreateBook(!showCreateBook)} 
          className="btn-success"
        >
          {showCreateBook ? 'Cancelar' : 'Crear Nuevo Libro'}
        </button>
      </div>

      {showCreateBook && (
        <div className="card" style={{ marginBottom: '2rem', backgroundColor: '#1e293b' }}>
          <h2>Crear Nuevo Libro</h2>
          <p style={{ color: '#9ca3af', marginBottom: '1rem' }}>
            El SKU se generará automáticamente (BOOK-001, BOOK-002, etc.)
          </p>
          <form onSubmit={handleCreateBook}>
            <div className="form-group">
              <label htmlFor="title">Título *</label>
              <input
                type="text"
                id="title"
                value={newBook.title}
                onChange={(e) => setNewBook({...newBook, title: e.target.value})}
                placeholder="El nombre del libro"
                required
                style={{ width: '100%' }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="author">Autor *</label>
              <input
                type="text"
                id="author"
                value={newBook.author}
                onChange={(e) => setNewBook({...newBook, author: e.target.value})}
                placeholder="Nombre del autor"
                required
                style={{ width: '100%' }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="price">Precio (USD) *</label>
              <input
                type="number"
                id="price"
                min="0"
                step="0.01"
                value={newBook.price}
                onChange={(e) => setNewBook({...newBook, price: e.target.value})}
                placeholder="19.99"
                required
                style={{ width: '200px' }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="category">Categoría *</label>
              <select
                id="category"
                value={newBook.category}
                onChange={(e) => setNewBook({...newBook, category: e.target.value})}
                required
                style={{ width: '100%' }}
              >
                <option value="">Selecciona una categoría</option>
                <option value="fiction">Ficción</option>
                <option value="non-fiction">No Ficción</option>
                <option value="science">Ciencia</option>
                <option value="history">Historia</option>
                <option value="biography">Biografía</option>
                <option value="technology">Tecnología</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="description">Descripción</label>
              <textarea
                id="description"
                value={newBook.description}
                onChange={(e) => setNewBook({...newBook, description: e.target.value})}
                placeholder="Descripción del libro..."
                rows="3"
                style={{ width: '100%' }}
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Creando...' : 'Crear Libro'}
            </button>
          </form>
        </div>
      )}
      
      <div className="card">
        <h2>Buscar Item en Inventario</h2>
        <form onSubmit={handleSearchItem}>
          <div className="form-group">
            <label htmlFor="itemId">ID del Item (ej: BOOK-001)</label>
            <input
              type="text"
              id="itemId"
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
              placeholder="BOOK-001"
              style={{ width: '100%' }}
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </form>
      </div>

      {error && <div className="error" style={{ marginTop: '1rem' }}>{error}</div>}
      {success && <div className="success" style={{ marginTop: '1rem' }}>{success}</div>}

      {item && (
        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Información del Item</h2>
          <div style={{ marginTop: '1rem' }}>
            <p><strong>ID:</strong> {item.itemId || item.id}</p>
            <p><strong>Nombre:</strong> {item.name || 'N/A'}</p>
            <p><strong>Stock Actual:</strong> {item.quantity}</p>
            <p><strong>Stock Reservado:</strong> {item.reservedQuantity || 0}</p>
            <p><strong>Stock Disponible:</strong> {item.quantity - (item.reservedQuantity || 0)}</p>
            <p><strong>Última actualización:</strong> {new Date(item.updatedAt).toLocaleString()}</p>
          </div>

          <div style={{ marginTop: '2rem' }}>
            <h3>Actualizar Stock</h3>
            <div className="form-group">
              <label htmlFor="newStock">Nueva cantidad</label>
              <input
                type="number"
                id="newStock"
                min="0"
                value={newStock}
                onChange={(e) => setNewStock(parseInt(e.target.value) || 0)}
                style={{ width: '200px' }}
              />
            </div>
            <button 
              onClick={handleUpdateStock} 
              disabled={loading}
              className="btn-success"
            >
              {loading ? 'Actualizando...' : 'Actualizar Stock'}
            </button>
          </div>
        </div>
      )}

      <div className="card" style={{ marginTop: '2rem', backgroundColor: '#1a2332' }}>
        <h3>Información</h3>
        <p>Esta página permite consultar y actualizar el inventario de items.</p>
        <p><strong>IDs de ejemplo:</strong> BOOK-001, BOOK-002, BOOK-003, ... BOOK-010</p>
      </div>
    </div>
  )
}

export default InventoryPage
