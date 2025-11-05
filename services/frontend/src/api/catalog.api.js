import apiClient from './client'

/**
 * API para el catálogo de libros
 */

// Listar todos los libros
export const listBooks = async (params = {}) => {
  const response = await apiClient.get('/api/catalog/books', { params })
  return response.data
}

// Obtener un libro por ID
export const getBook = async (bookId) => {
  const response = await apiClient.get(`/api/catalog/books/${bookId}`)
  return response.data
}

// Crear un nuevo libro (admin)
export const createBook = async (bookData) => {
  const response = await apiClient.post('/api/catalog/books', bookData)
  return response.data
}

// Actualizar un libro (admin)
export const updateBook = async (bookId, bookData) => {
  const response = await apiClient.put(`/api/catalog/books/${bookId}`, bookData)
  return response.data
}

// Eliminar un libro (admin)
export const deleteBook = async (bookId) => {
  const response = await apiClient.delete(`/api/catalog/books/${bookId}`)
  return response.data
}

// Buscar libros
export const searchBooks = async (query) => {
  const response = await apiClient.get('/api/catalog/books/search', { 
    params: { q: query } 
  })
  return response.data
}
