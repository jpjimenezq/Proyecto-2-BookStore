import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'
import { logout } from '../api/auth.api'

function Navbar() {
  const { isAuthenticated, user, clearAuth } = useAuthStore()
  const { items } = useCartStore()

  const handleLogout = () => {
    logout()
    clearAuth()
  }

  const isAdmin = user?.role === 'ADMIN'

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          Bookstore {isAdmin && <span style={{ fontSize: '0.7em', color: '#fbbf24' }}> [ADMIN]</span>}
        </Link>

        <ul className="navbar-links">
          <li><Link to="/">Inicio</Link></li>
          <li><Link to="/catalog">Catálogo</Link></li>
          {isAuthenticated && (
            <>
              <li><Link to="/cart">Carrito {items.length > 0 && <span className="badge">({items.length})</span>}</Link></li>
              <li><Link to="/orders">Mis Órdenes</Link></li>
              {isAdmin && <li><Link to="/inventory">Inventario</Link></li>}
            </>
          )}
        </ul>

        <div className="navbar-actions">
          {isAuthenticated ? (
            <>
              <span className="user-greeting">
                Hola, {user?.username || user?.email}
                {isAdmin && <span style={{ color: '#fbbf24', marginLeft: '0.5rem' }}>ADMIN</span>}
              </span>
              <button onClick={handleLogout} className="btn-secondary">
                Cerrar Sesión
              </button>
            </>
          ) : (
            <>
              <Link to="/login">
                <button className="btn-primary">Iniciar Sesión</button>
              </Link>
              <Link to="/register">
                <button className="btn-secondary">Registrarse</button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
