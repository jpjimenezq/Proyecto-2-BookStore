import axios from 'axios'

// PRODUCTION: Direct connection to Gateway NodePort
const API_URL = 'http://44.197.205.70:31355'

// Crear instancia de axios con configuración base
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 segundos
})

// Interceptor para agregar el token JWT a todas las peticiones
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para manejar errores de respuesta
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // El servidor respondió con un código de error
      const { status, data } = error.response
      
      if (status === 401) {
        // Token inválido o expirado
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
      
      // Mensaje de error personalizado
      const errorMessage = data?.error || data?.message || 'Error en la petición'
      return Promise.reject(new Error(errorMessage))
    } else if (error.request) {
      // La petición fue hecha pero no hubo respuesta
      return Promise.reject(new Error('No se pudo conectar con el servidor'))
    } else {
      // Algo pasó al configurar la petición
      return Promise.reject(new Error(error.message))
    }
  }
)

export default apiClient
