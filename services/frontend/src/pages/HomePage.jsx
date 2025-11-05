import { Link } from 'react-router-dom'

function HomePage() {
  return (
    <div className="home-page">
      <div className="hero-section">
        <h1>Bienvenido a Bookstore</h1>
        <p className="hero-subtitle">
          Tu librería online favorita con miles de libros disponibles
        </p>
      </div>
      
      <div className="grid" style={{ marginTop: '3rem' }}>
        <div className="card feature-card">
          <div className="card-header">Catálogo</div>
          <p>Explora nuestra amplia colección de libros</p>
          <Link to="/catalog">
            <button className="btn-primary" style={{ marginTop: '1rem', width: '100%' }}>
              Ver Catálogo
            </button>
          </Link>
        </div>

        <div className="card feature-card">
          <div className="card-header">Tu Carrito</div>
          <p>Revisa los libros que has seleccionado</p>
          <Link to="/cart">
            <button className="btn-primary" style={{ marginTop: '1rem', width: '100%' }}>
              Ir al Carrito
            </button>
          </Link>
        </div>

        <div className="card feature-card">
          <div className="card-header">Tus Órdenes</div>
          <p>Consulta el estado de tus pedidos</p>
          <Link to="/orders">
            <button className="btn-primary" style={{ marginTop: '1rem', width: '100%' }}>
              Ver Órdenes
            </button>
          </Link>
        </div>
      </div>

      <div className="features-section">
        <h2>Características</h2>
        <div className="grid" style={{ marginTop: '2rem' }}>
          <div className="card info-card">
            <h3>Entrega Rápida</h3>
            <p>Recibe tus libros en tiempo récord</p>
          </div>
          <div className="card info-card">
            <h3>Pago Seguro</h3>
            <p>Transacciones protegidas y confiables</p>
          </div>
          <div className="card info-card">
            <h3>Ofertas Especiales</h3>
            <p>Descuentos y promociones exclusivas</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage
