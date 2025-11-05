import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../api/auth.api'

function RegisterPage() {
  const navigate = useNavigate()
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await register(formData)
      
      // Redirigir al login después de registrarse
      navigate('/login', { 
        state: { message: 'Registro exitoso. Por favor inicia sesión.' }
      })
    } catch (err) {
      setError(err.message || 'Error al registrarse')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ textAlign: 'center' }}>Crear Cuenta</h1>
      
      <form className="form" onSubmit={handleSubmit}>
        {error && <div className="error">{error}</div>}
        
        <div className="form-group">
          <label htmlFor="name">Nombre</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Contraseña</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            minLength="6"
          />
        </div>

        <button 
          type="submit" 
          className="btn-primary" 
          disabled={loading}
          style={{ width: '100%' }}
        >
          {loading ? 'Registrando...' : 'Registrarse'}
        </button>

        <p style={{ textAlign: 'center', marginTop: '1rem' }}>
          ¿Ya tienes cuenta? <Link to="/login">Inicia sesión aquí</Link>
        </p>
      </form>
    </div>
  )
}

export default RegisterPage
