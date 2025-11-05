import { useState, useEffect } from 'react'
import { listBooks } from '../api/catalog.api'
import BookCard from '../components/BookCard'

function CatalogPage() {
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadBooks()
  }, [])

  const loadBooks = async () => {
    try {
      setLoading(true)
      const data = await listBooks()
      setBooks(data.books || data)
    } catch (err) {
      setError(err.message || 'Error al cargar los libros')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Cargando libros...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div>
      <h1>Catálogo de Libros</h1>
      <p>Explora nuestra colección de {books.length} libros</p>
      
      {books.length === 0 ? (
        <div className="card">
          <p>No hay libros disponibles en este momento.</p>
        </div>
      ) : (
        <div className="grid">
          {books.map((book) => (
            <BookCard key={book.sku} book={book} />
          ))}
        </div>
      )}
    </div>
  )
}

export default CatalogPage
