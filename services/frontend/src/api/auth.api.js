import apiClient from './client'

/**
 * API para autenticación de usuarios
 */

// Registrar nuevo usuario
export const register = async (userData) => {
  const response = await apiClient.post('/api/auth/register', {
    username: userData.email || userData.username,
    password: userData.password
  })
  return response.data
}

// Iniciar sesión
export const login = async (credentials) => {
  const response = await apiClient.post('/api/auth/login', {
    username: credentials.email || credentials.username,
    password: credentials.password
  })
  return response.data
}

// Obtener perfil del usuario actual
export const getProfile = async () => {
  const response = await apiClient.get('/api/users/me')
  return response.data
}

// Actualizar perfil
export const updateProfile = async (userId, userData) => {
  const response = await apiClient.put(`/api/users/${userId}`, userData)
  return response.data
}

// Cerrar sesión (limpia tokens localmente)
export const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.location.href = '/login'
}
