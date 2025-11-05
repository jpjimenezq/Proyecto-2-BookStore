import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

/**
 * Componente para proteger rutas que requieren autenticación
 */
export function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

/**
 * Componente para proteger rutas que requieren rol de administrador
 */
export function AdminRoute({ children }) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.role !== 'ADMIN') {
    return (
      <div className="container" style={{ marginTop: '2rem' }}>
        <div className="card">
          <h2 style={{ color: '#ef4444' }}>Acceso Denegado</h2>
          <p>No tienes permisos para acceder a esta página.</p>
          <p>Solo los administradores pueden acceder al inventario.</p>
          <button 
            onClick={() => window.history.back()} 
            className="btn-primary"
            style={{ marginTop: '1rem' }}
          >
            Volver
          </button>
        </div>
      </div>
    )
  }

  return children
}

