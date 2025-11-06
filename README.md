# Bookstore Microservices

Sistema de tienda de libros construido con arquitectura de microservicios, utilizando múltiples lenguajes de programación y tecnologías modernas. Este proyecto demuestra patrones avanzados de **comunicación síncrona (gRPC)** y **asíncrona (eventos con RabbitMQ)**, desacoplamiento de servicios, y orquestación de microservicios polyglot.

## Arquitectura

Este proyecto implementa una arquitectura de microservicios completa con dos tipos de comunicación:

```
┌─────────────┐
│   Frontend  │ (React + Vite)
│   (Nginx)   │
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────┐
│   Gateway   │ (Node.js + Express)
│  (REST API) │
└──────┬──────┘
       │ gRPC
       ↓
┌──────────────────────────────────────────┐
│         Microservicios                   │
├──────────┬──────────┬──────────┬─────────┤
│ Catalog  │   Cart   │  Order   │   User  │
│  (Go)    │ (Python) │ (Python) │ (Node)  │
│          │          │          │         │
│ Inventory│ Payment  │          │         │
│  (Go)    │ (Python) │          │         │
└────┬─────┴────┬─────┴────┬─────┴────┬────┘
     │          │          │          │
     ↓          ↓          ↓          ↓
┌────────┐  ┌─────────┐  ┌──────────┐
│Postgres│  │ MongoDB │  │ RabbitMQ │
└────────┘  └─────────┘  └──────────┘
```

## Decisiones de Diseño y Justificación Técnica

### Elección de Lenguajes por Servicio

#### **Go (Catalog, Inventory)**
**Razones:**
- **Performance crítico**: Estos servicios manejan el catálogo y stock, operaciones de alta frecuencia
- **Concurrencia nativa**: Go routines ideales para manejar múltiples requests gRPC simultáneamente
- **Ecosystem gRPC**: Excelente soporte nativo para Protocol Buffers y gRPC

#### **Python (Cart, Order, Payment)**
**Razones:**
- **Lógica de negocio compleja**: Cálculos de precios, validaciones de órdenes, reglas de negocio
- **Prototipado rápido**: Ideal para lógica de negocio que cambia frecuentemente

#### **Node.js (User, Gateway)**
**Razones:**
- **I/O intensivo**: Gateway maneja muchas conexiones simultáneas sin bloqueo
- **Event-driven**: Arquitectura natural para proxy/gateway patterns
- **JSON nativo**: Manejo eficiente de JWT y payloads REST
- **Ecosystem HTTP**: Express.js, middleware de autenticación
- **Single language stack**: Facilita el desarrollo fullstack

### Elección de Persistencia por Servicio

#### **PostgreSQL (Catalog, Order, User, Inventory)**
**Razones:**
- **Transacciones**: Operaciones como crear orden + reservar inventario deben ser atómicas
- **Consultas SQL complejas**: Búsquedas con filtros, paginación, agregaciones

#### **MongoDB (Cart)**
**Razones:**
- **Documentos anidados**: Carrito como documento con array de items
- **Escrituras frecuentes**: Agregar/quitar items es muy frecuente, MongoDB optimizado para writes

#### **Sin BD (Payment, Gateway)**
**Razones:**
- **Delegacion**: Payment delega a gateways externos, no almacena datos sensibles
- **Gateway como proxy**: Solo traduce requests, no mantiene estado
- **Escalabilidad**: Servicios sin estado se escalan horizontalmente sin problemas

## Tipos de Comunicación

### Comunicación Síncrona (gRPC)
- **Protocolo**: gRPC sobre HTTP/2
- **Ubicación de contratos**: `contracts/proto/*.proto`
- **Código generado**: `contracts/gen/go/`, `contracts/gen/python/`, `contracts/gen/node/`
- **Uso**: Operaciones que requieren respuesta inmediata (CRUD, consultas)

### Comunicación Asíncrona (Eventos)
- **Message Broker**: RabbitMQ
- **Ubicación de esquemas**: `contracts/events/*.events.json`
- **Patrón**: Publish/Subscribe con exchanges tipo "topic"
- **Uso**: Notificaciones, sincronización eventual, desacoplamiento

## Servicios

| Servicio | Lenguaje | Base de Datos | Puerto gRPC | Puerto HTTP | Ubicación |
|----------|----------|---------------|-------------|-------------|-----------|
| **Catalog** | Go | PostgreSQL | 50051 | 8081 | `services/catalog/` |
| **Cart** | Python | MongoDB | 50052 | 8082 | `services/cart/` |
| **Order** | Python | PostgreSQL | 50053 | 8083 | `services/order/` |
| **User** | JS | PostgreSQL | 50054 | 8084 | `services/user/` |
| **Inventory** | Go | PostgreSQL | 50055 | 8085 | `services/inventory/` |
| **Payment** | Python | Ninguna | 50056 | 8086 | `services/payment/` |
| **Gateway** | Node.js | Ninguna | - | 3000 | `services/gateway/` |
| **Frontend** | React | Ninguna | - | 80 | `services/frontend/` |

### Estructura de Cada Servicio

**Servicios Go (Catalog, Inventory):**
```
services/catalog/
├── cmd/catalogd/main.go          # Entry point
├── internal/
│   ├── grpc/server.go            # Servidor gRPC
│   ├── grpc/handler.go           # Implementación de métodos gRPC
│   ├── repo/repository.go        # Acceso a datos
│   ├── events/publisher.go       # Publicador de eventos RabbitMQ
│   └── events/consumer.go        # Consumidor de eventos RabbitMQ
├── proto (link simbólico)        # → ../../contracts/proto/
└── Dockerfile
```

**Servicios Python (Cart, Order, Payment):**
```
services/cart/
├── cmd/start.py                  # Entry point
├── cart/
│   ├── grpc_server.py           # Servidor gRPC
│   ├── service.py               # Lógica de negocio
│   ├── db.py                    # Conexión a base de datos
│   ├── clients/                 # Clientes gRPC a otros servicios
│   │   └── catalog_client.py
│   └── events/
│       ├── publisher.py         # Publicador de eventos
│       └── consumer.py          # Consumidor de eventos
└── requirements.txt
```

**Servicios Node.js y JS (User, Gateway):**
```
services/user/
├── src/
│   ├── index.js                 # Entry point
│   ├── grpc/server.js          # Servidor gRPC
│   ├── grpc/clients/           # Clientes gRPC
│   ├── services/userService.js # Lógica de negocio
│   └── db.js                   # Conexión a PostgreSQL
└── package.json
```

## Comunicación entre Servicios

### Contratos gRPC (Comunicación Síncrona)

**Ubicación de Archivos Proto:**
```
contracts/proto/
├── common.proto          # Tipos compartidos (Money, Pagination, Address, Health)
├── catalog.proto         # CatalogService con 6 métodos RPC
├── cart.proto           # CartService con 5 métodos RPC
├── order.proto          # OrderService con 6 métodos RPC
├── user.proto           # UserService con 6 métodos RPC
├── inventory.proto      # InventoryService con 5 métodos RPC
└── payment.proto        # PaymentService con 2 métodos RPC
```

**Código Generado (Stubs):**
```
contracts/gen/
├── go/                  # Para servicios Catalog, Inventory
│   ├── catalog/
│   │   ├── catalog.pb.go        # Mensajes Protocol Buffer
│   │   └── catalog_grpc.pb.go   # Cliente y servidor gRPC
│   ├── cart/
│   ├── order/
│   ├── user/
│   ├── inventory/
│   ├── payment/
│   └── common/
├── python/              # Para servicios Cart, Order, Payment
│   ├── catalog_pb2.py           # Mensajes Protocol Buffer
│   ├── catalog_pb2_grpc.py      # Cliente y servidor gRPC
│   ├── cart_pb2.py
│   ├── cart_pb2_grpc.py
│   └── ...
```

### Eventos (Comunicación Asíncrona)

**Esquemas de Eventos:**
```
contracts/events/
├── catalog.events.json    # book.created, book.updated, book.deleted
├── cart.events.json       # cart.item.added, cart.item.removed, cart.cleared
└── inventory.events.json  # inventory.reserved, inventory.released, inventory.low_stock
```

**Configuración RabbitMQ:**
- **Exchange**: `bookstore.events` (tipo: topic)
- **Routing Keys**: `catalog.book.*`, `cart.item.*`, `order.*`, `inventory.*`
- **Queues**: Una por servicio consumidor
- **Pattern**: Cada servicio publica eventos cuando cambia su estado

## Funciones y Comunicaciones por Servicio

### 1. Catalog Service (Go - Puerto 50051)
**Ubicación**: `services/catalog/`

**Funciones Principales:**
- `GetBook(sku)` - Obtener detalles de un libro
- `ListBooks(page, pageSize, category)` - Listar libros con paginación
- `CreateBook(book)` - Crear nuevo libro (solo admin)
- `UpdateBook(sku, book)` - Actualizar libro existente
- `DeleteBook(sku)` - Eliminar libro
- `SearchBooks(query)` - Buscar libros por título/autor

**Comunicación Síncrona (gRPC Server):**
- **Recibe**: Llamadas gRPC desde Gateway
- **Implementa**: `contracts/proto/catalog.proto`
- **Archivo**: `internal/grpc/server.go`, `internal/grpc/handler.go`

**Comunicación Asíncrona (Eventos):**
- **Publica**: 
  - `book.created` cuando se crea un libro
  - `book.updated` cuando se actualiza
  - `book.deleted` cuando se elimina
- **Archivo**: `internal/events/publisher.go`
- **Exchange**: `bookstore.events`
- **Routing Key**: `catalog.book.*`

**No Consume Eventos** (servicio independiente)

### 2. Cart Service (Python - Puerto 50052)
**Ubicación**: `services/cart/`

**Funciones Principales:**
- `GetCart(user_id)` - Obtener carrito del usuario
- `AddItem(user_id, sku, quantity)` - Agregar libro al carrito
- `UpdateItem(user_id, sku, quantity)` - Actualizar cantidad
- `RemoveItem(user_id, sku)` - Remover item del carrito
- `ClearCart(user_id)` - Vaciar carrito completo

**Comunicación Síncrona (gRPC):**
- **Como Servidor**: 
  - Recibe llamadas desde Gateway y Order Service
  - Implementa: `contracts/proto/cart.proto`
  - Archivo: `cart/grpc_server.py`
- **Como Cliente**:
  - Llama a Catalog Service para obtener detalles del libro
  - Archivo: `cart/clients/catalog_client.py`
  - Usa: `contracts/gen/python/catalog_pb2_grpc.py`

**Comunicación Asíncrona:**
- **Publica**:
  - `cart.item.added` al agregar items
  - `cart.item.removed` al remover items
  - `cart.cleared` al vaciar carrito
  - Archivo: `cart/events/publisher.py`
- **Consume**:
  - `order.created` → Vacía carrito automáticamente
  - Archivo: `cart/events/consumer.py`

### 3. Order Service (Python - Puerto 50053)
**Ubicación**: `services/order/`

**Funciones Principales:**
- `CreateOrder(user_id, items, address, payment)` - Crear nueva orden
- `GetOrder(order_id)` - Obtener detalles de orden
- `ListOrders(user_id, status, page)` - Listar órdenes del usuario
- `UpdateOrderStatus(order_id, status)` - Actualizar estado
- `CancelOrder(order_id)` - Cancelar orden

**Comunicación Síncrona (gRPC):**
- **Como Servidor**:
  - Recibe llamadas desde Gateway
  - Implementa: `contracts/proto/order.proto`
  - Archivo: `order/grpc/server.py`
- **Como Cliente**, llama a:
  - **Cart Service**: `GetCart(user_id)` para obtener items
  - **Inventory Service**: `ReserveInventory(sku, quantity)` para cada item
  - **Payment Service**: `ProcessPayment(order_id, amount, method)`
  - Archivos: `order/clients/cart_client.py`, `inventory_client.py`, `payment_client.py`

**Comunicación Asíncrona:**
- **Publica**:
  - `order.created` cuando se crea orden exitosamente
  - `order.status.changed` cuando cambia estado (pending→paid→shipped→delivered)
  - `order.completed` cuando se completa
  - `order.cancelled` cuando se cancela
  - Archivo: `order/events/publisher.py`
- **No Consume Eventos** (orquestador)

### 4. User Service (Node.js - Puerto 50054)
**Ubicación**: `services/user/`

**Funciones Principales:**
- `Register(email, password, firstName, lastName)` - Registrar usuario
- `Login(email, password)` - Iniciar sesión, retorna JWT
- `VerifyToken(token)` - Verificar validez del token JWT
- `GetUser(user_id)` - Obtener perfil de usuario
- `UpdateUser(user_id, data)` - Actualizar perfil
- `DeleteUser(user_id)` - Eliminar cuenta

**Comunicación Síncrona (gRPC):**
- **Como Servidor**:
  - Recibe llamadas principalmente desde Gateway
  - Implementa: `contracts/proto/user.proto`
  - Archivo: `src/grpc/server.js`
- **No llama a otros servicios** (servicio base)

**Comunicación Asíncrona:**
- **No publica ni consume eventos** (servicio independiente)

### 5. Inventory Service (Go - Puerto 50055)
**Ubicación**: `services/inventory/`

**Funciones Principales:**
- `GetInventory(sku)` - Consultar stock disponible
- `UpdateInventory(sku, quantity)` - Actualizar cantidad (admin)
- `ReserveInventory(sku, quantity, order_id)` - Reservar stock para orden
- `ReleaseInventory(sku, quantity, order_id)` - Liberar reserva (si orden cancela)
- `ListLowStock()` - Listar items con stock bajo

**Comunicación Síncrona (gRPC):**
- **Como Servidor**:
  - Recibe llamadas desde Order Service y Gateway
  - Implementa: `contracts/proto/inventory.proto`
  - Archivo: `internal/grpc/server.go`
- **No llama a otros servicios**

**Comunicación Asíncrona:**
- **Publica**:
  - `inventory.reserved` cuando reserva stock
  - `inventory.released` cuando libera reserva
  - `inventory.low_stock` cuando stock < reorder_point
  - Archivo: `internal/events/publisher.go`
- **Consume**:
  - `order.cancelled` → Libera inventario reservado
  - Archivo: `internal/events/consumer.go`

### 6. Payment Service (Python - Puerto 50056)
**Ubicación**: `services/payment/`

**Funciones Principales:**
- `ProcessPayment(order_id, amount, payment_method)` - Procesar pago
- `ValidatePaymentMethod(card_number, cvv, expiry)` - Validar método de pago

**Comunicación Síncrona (gRPC):**
- **Como Servidor**:
  - Recibe llamadas SOLO desde Order Service
  - Implementa: `contracts/proto/payment.proto`
  - Archivo: `payment/grpc_server.py`
- **No llama a otros servicios** (stateless)

**Comunicación Asíncrona:**
- **No publica ni consume eventos** (servicio auxiliar)

### 7. Gateway Service (Node.js - Puerto 3000 HTTP)
**Ubicación**: `services/gateway/`

**Funciones Principales:**
- Traducir requests REST → gRPC
- Autenticación JWT en cada request
- Rate limiting
- Enrutamiento a servicios backend

**Comunicación Síncrona (gRPC):**
- **Como Cliente**, llama a TODOS los servicios:
  - User Service: `VerifyToken()` en cada request protegido
  - Catalog Service: todas las operaciones de catálogo
  - Cart Service: operaciones de carrito
  - Order Service: operaciones de órdenes
  - Inventory Service: consultas de inventario
  - Archivos: `src/grpc/clients/*.js`

**Comunicación Asíncrona:**
- **No publica ni consume eventos** (solo proxy)

### 8. Frontend (React - Puerto 80)
**Ubicación**: `services/frontend/`

**Funciones:**
- Interfaz de usuario web
- State management (Zustand)
- Llamadas HTTP al Gateway

**Comunicación:**
- **Solo HTTP REST** → Gateway (puerto 3000)
- Archivos: `src/api/*.api.js`

## Flujo de Comunicación Completo - Ejemplo: Crear Orden

```
1. [SÍNCRONA] Frontend → Gateway (HTTP POST /api/orders)
   Archivo: frontend/src/api/order.api.js

2. [SÍNCRONA] Gateway → User Service (gRPC VerifyToken)
   Archivo: gateway/src/grpc/clients/userClient.js
   Proto: contracts/proto/user.proto
   Stub: contracts/gen/node/user/

3. [SÍNCRONA] Gateway → Order Service (gRPC CreateOrder)
   Archivo: gateway/src/grpc/clients/orderClient.js
   Proto: contracts/proto/order.proto

4. [SÍNCRONA] Order Service → Cart Service (gRPC GetCart)
   Archivo: order/clients/cart_client.py
   Stub: contracts/gen/python/cart_pb2_grpc.py

5. [SÍNCRONA] Order Service → Inventory Service (gRPC ReserveInventory)
   Archivo: order/clients/inventory_client.py
   Stub: contracts/gen/python/inventory_pb2_grpc.py
   Por cada item en el carrito

6. [SÍNCRONA] Order Service → Payment Service (gRPC ProcessPayment)
   Archivo: order/clients/payment_client.py
   Stub: contracts/gen/python/payment_pb2_grpc.py

7. [ASÍNCRONA] Order Service → RabbitMQ (Publish order.created)
   Archivo: order/events/publisher.py
   Exchange: bookstore.events
   Routing Key: order.created
   Schema: contracts/events/order.events.json

8. [SÍNCRONA] Order Service → Gateway (Return order)
   Response gRPC

9. [SÍNCRONA] Gateway → Frontend (HTTP 201 Created)
   Response JSON

10. [ASÍNCRONA] RabbitMQ → Inventory Service (Consume order.created)
    Archivo: inventory/internal/events/consumer.go
    Acción: Actualiza stock disponible

11. [ASÍNCRONA] RabbitMQ → Cart Service (Consume order.created)
    Archivo: cart/events/consumer.py
    Acción: Vacía el carrito del usuario

12. [ASÍNCRONA] Inventory Service → RabbitMQ (Publish inventory.reserved)
    Archivo: inventory/internal/events/publisher.go
    Notifica que inventario fue reservado
```

## Características Principales

### Tecnologías y Patrones

- **Arquitectura de Microservicios**: Servicios independientes y desacoplados
- **gRPC**: Comunicación síncrona eficiente entre servicios (HTTP/2, Protocol Buffers)
- **Event-Driven**: RabbitMQ para comunicación asíncrona y desacoplamiento temporal
- **Polyglot**: Go (performance), Python (productividad), Node.js (ecosistema), React (UI)
- **Containerización**: Docker para cada servicio
- **Orquestación**: Kubernetes con manifiestos completos
- **API Gateway Pattern**: Punto de entrada unificado con autenticación JWT
- **Health Checks**: Endpoints HTTP `/health` en cada servicio

### Funcionalidades de Negocio

- Catálogo de libros con búsqueda y paginación
- Carrito de compras persistente en MongoDB
- Sistema de órdenes con validación de inventario
- Gestión de inventario en tiempo real con reservas
- Autenticación JWT
- Procesamiento de pagos con validación
- Eventos de dominio para sincronización eventual
- Desacoplamiento mediante message broker

## Prerrequisitos

### Herramientas de Desarrollo

- **Docker**
- **Docker Compose**
- **Kubernetes**

### Lenguajes y Runtimes

- **Go** para servicios Catalog, Inventory
- **Python** para servicios Cart, Order, Payment
- **Node.js** para servicios User, Gateway, Frontend
- **Protocol Buffers** protoc compiler

### Bases de Datos

- **PostgreSQL**
- **MongoDB**
- **RabbitMQ**

## Inicio Rápido

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd bookstore-ms
```

### 3. Ejecutar
```bash
cd deploy\local
docker-compose up --build -d
```
### 3. Verificar que Todo Esté Funcionando

```bash
# Verificar contenedores
docker-compose ps

# Verificar logs
docker-compose logs -f

# O revisar en la aplicacion de DockerHub

# Probar health checks
curl http://localhost:8081/health  # Catalog
curl http://localhost:8082/health  # Cart
curl http://localhost:8083/health  # Order
curl http://localhost:8084/health  # User
curl http://localhost:8085/health  # Inventory
curl http://localhost:8086/health  # Payment

# Probar Gateway
curl http://localhost:3000/health

# En la URL de la API Gateway podemos revisar los endpoints que tenemos disponibles por cada microservicio

# Abrir Frontend
# http://localhost:8000
```

### Ventajas de usar Protocol Buffers y gRPC

- **Type Safety**: Tipos definidos en proto se generan en cada lenguaje
- **Compatibilidad**: Mismos mensajes entre Go, Python, Node.js
- **Versionado**: Agregar campos sin romper clientes antiguos
- **Performance**: Serialización binaria más rápida que JSON
- **Streaming**: Soporte para server/client/bidirectional streaming
- **Code Generation**: Cliente y servidor generados automáticamente

## Desarrollo

### Estructura del Proyecto

```
bookstore-ms/
├── contracts/          # Contratos compartidos
│   ├── proto/          # Definiciones Protocol Buffer
│   ├── events/         # Esquemas de eventos JSON
│   └── gen/            # Código generado
├── services/           # Microservicios
│   ├── catalog/
│   ├── cart/
│   ├── order/
│   ├── user/
│   ├── inventory/
│   ├── payment/
│   ├── gateway/
│   └── frontend/
├── deploy/             # Configuraciones de deployment
│   ├── k8s/           # Manifiestos Kubernetes
│   └── local/         # Docker Compose local
├── build.ps1          # Script de build para Windows
└── push-images.ps1    # Script para publicar imágenes
```

## Mapa Completo de Comunicaciones

```
                    ┌─────────────────────────────────────────────────────┐
                    │            FRONTEND (React)                         │
                    │    src/api/*.api.js → HTTP REST                    │
                    └─────────────────────┬───────────────────────────────┘
                                          │ HTTP/REST (puerto 3000)
                                          ↓
                    ┌─────────────────────────────────────────────────────┐
                    │         GATEWAY (Node.js) - Puerto 3000            │
                    │  • Autenticación JWT                                │
                    │  • REST → gRPC translation                          │
                    │  • Usa stubs: contracts/gen/node/                   │
                    └──────┬──────┬──────┬──────┬──────┬─────────────────┘
                           │      │      │      │      │
                gRPC       │      │      │      │      │       gRPC
            ┌──────────────┘      │      │      │      └─────────────────┐
            │                     │      │      │                        │
            ↓                     ↓      ↓      ↓                        ↓
    ┌───────────────┐   ┌────────────────────────────┐        ┌─────────────────┐
    │ User Service  │   │   Catalog Service (Go)     │        │  Inventory (Go) │
    │  (Node.js)    │   │   Puerto gRPC: 50051       │        │  Puerto: 50055  │
    │  Puerto: 50054│   │   Proto: catalog.proto     │        │  Proto: inv.    │
    │               │   │   Stub: gen/go/catalog/    │        │                 │
    │ • VerifyToken │   │   • GetBook                │        │ • GetInventory  │
    │ • Register    │   │   • ListBooks              │        │ • Reserve       │
    │ • Login       │   │   • CreateBook             │        │ • Release       │
    │               │   │   • SearchBooks            │        │                 │
    │ DB: PostgreSQL│   │   DB: PostgreSQL           │        │ DB: PostgreSQL  │
    └───────────────┘   └───────┬────────────────────┘        └────────┬────────┘
                                │ Publica                              │ Publica
                                │ catalog.*                            │ inventory.*
                                ↓                                      ↓
    ┌───────────────┐   ┌─────────────────────────────────────────────────────┐
    │  Cart Service │   │           RabbitMQ (Message Broker)                 │
    │   (Python)    │   │   Exchange: bookstore.events (topic)                │
    │  Puerto: 50052│   │   • Mensajes persistentes                           │
    │               │◄──┤   • Publisher confirms                              │
    │ • GetCart     │   │   Schemas: contracts/events/*.json                  │
    │ • AddItem     │   └─────────────────────────────────────────────────────┘
    │ • RemoveItem  │          ↑                          ↑
    │               │          │ Publica                  │ Consume
    │ DB: MongoDB   │          │ cart.*                   │ order.created
    └───────┬───────┘          │                          │ order.cancelled
            │                  │                          │
            │ gRPC            ↓                          │
            │         ┌────────────────┐                 │
            │         │ Order Service  │                 │
            │         │   (Python)     │                 │
            │         │  Puerto: 50053 │─────────────────┘
            │         │                │  Publica: order.*
            │         │ • CreateOrder  │
            └────────→│ • GetOrder     │
                      │ • ListOrders   │
                      │                │
                      │ Llama vía gRPC:│
                      │ 1. Cart        │────┐
                      │ 2. Inventory   │    │ gRPC
                      │ 3. Payment     │◄───┘ calls
                      │                │
                      │ DB: PostgreSQL │
                      └────────────────┘
                               │ gRPC
                               ↓
                      ┌────────────────┐
                      │ Payment Service│
                      │   (Python)     │
                      │  Puerto: 50056 │
                      │                │
                      │ • ProcessPay   │
                      │ • ValidateCard │
                      │                │
                      │ DB: None       │
                      │ (Stateless)    │
                      └────────────────┘
```

## Resumen de Tecnologías por Capa

### Capa de Comunicación
| Tipo | Tecnología | Puerto | Uso | Archivos Clave |
|------|-----------|--------|-----|----------------|
| **Síncrona** | gRPC (HTTP/2) | 50051-50056 | Request/Response inmediato | `contracts/proto/*.proto` |
| **Asíncrona** | RabbitMQ (AMQP) | 5672 | Eventos, desacoplamiento | `contracts/events/*.json` |
| **HTTP REST** | Express.js | 3000 | Frontend → Gateway | `gateway/src/routes/*.js` |

### Capa de Generación de Código
| Lenguaje | Herramienta | Output | Uso |
|----------|-------------|--------|-----|
| **Go** | protoc-gen-go | `*.pb.go`, `*_grpc.pb.go` | Catalog, Inventory |
| **Python** | grpc-tools | `*_pb2.py`, `*_pb2_grpc.py` | Cart, Order, Payment |
| **Node.js** | @grpc/proto-loader | Runtime loading | User, Gateway |

### Capa de Persistencia
| Servicio | Base de Datos | Justificación |
|----------|---------------|---------------|
| Catalog, Order, User, Inventory | **PostgreSQL** | Datos relacionales, ACID, queries complejas |
| Cart | **MongoDB** | Documentos flexibles, schema-less, escrituras frecuentes |
| Payment | **Ninguna** | Stateless, delega a payment gateway |

## APIs y Contratos

### Protocol Buffers (gRPC)

**Ubicación de contratos**: `contracts/proto/`

- `common.proto` - Tipos compartidos (Money, Pagination, Health)
- `catalog.proto` - API del catálogo de libros
- `cart.proto` - API del carrito de compras
- `order.proto` - API de órdenes
- `user.proto` - API de usuarios y autenticación
- `inventory.proto` - API de inventario
- `payment.proto` - API de pagos

### REST API (Gateway)

El Gateway expone una API REST que traduce a gRPC:

**Autenticación**
```
POST   /api/auth/register      # Registrar usuario
POST   /api/auth/login         # Iniciar sesión
POST   /api/auth/verify        # Verificar token JWT
```

**Catálogo (Público)**
```
GET    /api/catalog/books              # Listar libros
GET    /api/catalog/books/:sku         # Detalle de libro
GET    /api/catalog/books/search       # Buscar libros
```

**Carrito (Protegido)**
```
GET    /api/cart                      # Obtener carrito
POST   /api/cart/items                # Agregar item
DELETE /api/cart/items/:sku           # Eliminar item
DELETE /api/cart                      # Vaciar carrito
```

**Órdenes (Protegido)**
```
POST   /api/orders                    # Crear orden
GET    /api/orders                    # Listar órdenes
GET    /api/orders/:id                # Detalle de orden
PATCH  /api/orders/:id/status         # Actualizar estado
```
## Ciclo Completo de una Request - Trazabilidad

### Ejemplo: Usuario agrega libro al carrito

**Archivos involucrados y flujo de datos:**

```
1. FRONTEND
   Archivo: services/frontend/src/api/cart.api.js
   Código:
   ```javascript
   export const addToCart = async (sku, quantity) => {
     const response = await apiClient.post('/api/cart/items', {
       sku, quantity
     });
     return response.data;
   }
   ```
   Tecnología: Axios HTTP Client
   Tipo: HTTP POST
   Destino: http://gateway:3000/api/cart/items

2. GATEWAY (Recibe HTTP, convierte a gRPC)
   Archivo: services/gateway/src/routes/cart.js
   Código:
   ```javascript
   router.post('/items', authenticate, async (req, res) => {
     const { sku, quantity } = req.body;
     const userId = req.user.userId; // De JWT
     
     // Verificar token con User Service
     await userClient.verifyToken(req.token);
     
     // Obtener detalles del libro de Catalog
     const book = await catalogClient.getBook(sku);
     
     // Agregar al carrito via gRPC
     const cart = await cartClient.addItem({
       userId,
       sku,
       title: book.title,
       price: book.price,
       quantity
     });
     
     res.json(cart);
   });
   ```
   Tecnología: Express.js + gRPC clients
   Tipo: HTTP → gRPC translation
   
3. GATEWAY → USER SERVICE (Autenticación)
   Archivo: services/gateway/src/grpc/clients/userClient.js
   Código:
   ```javascript
   const { user_pb2, user_pb2_grpc } = require('../../contracts/gen/python');
   
   const stub = user_pb2_grpc.UserServiceClient('user:50054');
   const request = user_pb2.VerifyTokenRequest({ token });
   const response = await stub.VerifyToken(request);
   ```
   Proto: contracts/proto/user.proto
   Stub: contracts/gen/node/user/
   Tipo: Comunicación SÍNCRONA (gRPC)
   
4. USER SERVICE (Verifica JWT)
   Archivo: services/user/src/grpc/server.js
   Código:
   ```javascript
   async verifyToken(call, callback) {
     const { token } = call.request;
     try {
       const decoded = jwt.verify(token, JWT_SECRET);
       callback(null, {
         valid: true,
         userId: decoded.userId,
         role: decoded.role
       });
     } catch (err) {
       callback({
         code: grpc.status.UNAUTHENTICATED,
         message: 'Invalid token'
       });
     }
   }
   ```
   Tipo: Respuesta SÍNCRONA
   
5. GATEWAY → CATALOG SERVICE (Detalles del libro)
   Archivo: services/gateway/src/grpc/clients/catalogClient.js
   Proto: contracts/proto/catalog.proto
   Request: GetBookRequest { sku: "BOOK-001" }
   Tipo: Comunicación SÍNCRONA (gRPC)
   
6. CATALOG SERVICE (Consulta BD)
   Archivo: services/catalog/internal/grpc/handler.go
   Código:
   ```go
   func (h *Handler) GetBook(ctx context.Context, 
                             req *pb.GetBookRequest) (*pb.Book, error) {
       book, err := h.repo.GetBook(ctx, req.Sku)
       if err != nil {
           return nil, status.Errorf(codes.NotFound, "not found")
       }
       
       return &pb.Book{
           Sku:    book.SKU,
           Title:  book.Title,
           Author: book.Author,
           Price:  &pb.Money{Amount: book.Price, Currency: "USD"},
       }, nil
   }
   ```
   BD: PostgreSQL
   Query: SELECT * FROM books WHERE sku = $1
   Tipo: Respuesta SÍNCRONA
   
7. GATEWAY → CART SERVICE (Agregar item)
   Archivo: services/gateway/src/grpc/clients/cartClient.js
   Proto: contracts/proto/cart.proto
   Request:
   ```
   AddItemRequest {
     user_id: "user-123",
     sku: "BOOK-001",
     title: "Clean Code",
     price: Money { amount: "29.99", currency: "USD" },
     quantity: 2
   }
   ```
   Tipo: Comunicación SÍNCRONA (gRPC)
   
8. CART SERVICE (Actualiza carrito en MongoDB)
   Archivo: services/cart/cart/grpc_server.py
   Código:
   ```python
   def AddItem(self, request, context):
       cart = self.service.add_item(
           user_id=request.user_id,
           sku=request.sku,
           title=request.title,
           price=Money(request.price.amount, request.price.currency),
           quantity=request.quantity
       )
       return cart_to_proto(cart)
   ```
   Archivo: services/cart/cart/service.py
   BD: MongoDB
   Operación:
   ```python
   self.db.carts.update_one(
       {"user_id": user_id},
       {
           "$push": {"items": item_dict},
           "$set": {"updated_at": datetime.utcnow()}
       },
       upsert=True
   )
   ```
   Tipo: Respuesta SÍNCRONA
   
9. CART SERVICE (Publica evento)
   Archivo: services/cart/cart/events/publisher.py
   Código:
   ```python
   def publish_cart_item_added(user_id, sku, quantity):
       event = {
           "eventType": "cart.item.added",
           "timestamp": datetime.utcnow().isoformat(),
           "data": {
               "userId": user_id,
               "sku": sku,
               "quantity": quantity
           }
       }
       
       channel.basic_publish(
           exchange='bookstore.events',
           routing_key='cart.item.added',
           body=json.dumps(event),
           properties=pika.BasicProperties(
               delivery_mode=2,  # Persistente
           )
       )
   ```
   Destino: RabbitMQ
   Exchange: bookstore.events
   Routing Key: cart.item.added
   Tipo: Comunicación ASÍNCRONA (Fire & Forget)
   
10. GATEWAY → FRONTEND (Response HTTP)
    Código:
    ```javascript
    res.status(200).json({
      userId: "user-123",
      items: [
        {
          sku: "BOOK-001",
          title: "Clean Code",
          quantity: 2,
          price: { amount: "29.99", currency: "USD" },
          subtotal: { amount: "59.98", currency: "USD" }
        }
      ],
      totalPrice: { amount: "59.98", currency: "USD" },
      itemCount: 2
    });
    ```
    Tipo: HTTP Response (JSON)
    Status: 200 OK

TOTAL: 10 pasos
- 6 comunicaciones síncronas (gRPC)
- 1 comunicación asíncrona (RabbitMQ)
- 2 operaciones de base de datos
- 1 response HTTP al cliente
```

### Resumen de Tecnologías en el Flujo

| Paso | Origen | Destino | Protocolo | Archivo |
|------|--------|---------|-----------|---------|
| 1 | Frontend | Gateway | HTTP/REST | `frontend/src/api/cart.api.js` |
| 2-3 | Gateway | User | gRPC | `gateway/src/grpc/clients/userClient.js` |
| 4 | User | Gateway | gRPC | `user/src/grpc/server.js` |
| 5 | Gateway | Catalog | gRPC | `gateway/src/grpc/clients/catalogClient.js` |
| 6 | Catalog | PostgreSQL | SQL | `catalog/internal/repo/repository.go` |
| 7 | Gateway | Cart | gRPC | `gateway/src/grpc/clients/cartClient.js` |
| 8 | Cart | MongoDB | MongoDB Protocol | `cart/cart/db.py` |
| 9 | Cart | RabbitMQ | AMQP | `cart/events/publisher.py` |
| 10 | Gateway | Frontend | HTTP/REST | `gateway/src/routes/cart.js` |

### Push a Registry

```bash
# Configurar registry
export DOCKER_REGISTRY=your-registry.com

# Push todas las imágenes
.\push-images.ps1  # Windows
./push-images.sh   # Linux/Mac
```
## Observabilidad

## Seguridad

### Autenticación JWT

El Gateway maneja autenticación con tokens JWT:

1. Usuario se registra/inicia sesión en `/api/auth/register` o `/api/auth/login`
2. Recibe un token JWT
3. Incluye el token en el header `Authorization: Bearer <token>` para endpoints protegidos

### Variables de Entorno Sensibles

`.env` o secrets de Kubernetes para:

- Contraseñas de base de datos
- Secrets de JWT
- Credenciales de servicios externos
- API keys

## Eventos de Dominio

### Configuración RabbitMQ

**Ubicación**: Todos los servicios se conectan a RabbitMQ en puerto 5672
- **URL**: `amqp://admin:changeme@rabbitmq:5672/`
- **Exchange**: `bookstore.events` (tipo: `topic`)
- **Persistencia**: Mensajes persistentes (delivery_mode=2)
- **Confirmaciones**: Publisher confirms habilitado

### Catalog Events (Publisher: Catalog Service)
**Ubicación**: `services/catalog/internal/events/publisher.go`

**1. `book.created`**
```json
{
  "eventType": "book.created",
  "timestamp": "2025-11-05T10:00:00Z",
  "data": {
    "sku": "BOOK-001",
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "price": { "amount": "29.99", "currency": "USD" }
  }
}
```
- **Routing Key**: `catalog.book.created`
- **Cuándo**: Al crear un libro nuevo
- **Consumidores**: Ninguno (informativo)

**2. `book.updated`**
- **Routing Key**: `catalog.book.updated`
- **Cuándo**: Al actualizar precio, descripción, etc.
- **Consumidores**: Ninguno (informativo)

**3. `book.deleted`**
- **Routing Key**: `catalog.book.deleted`
- **Cuándo**: Al eliminar un libro del catálogo
- **Consumidores**: Ninguno (informativo)

### Cart Events (Publisher: Cart Service)
**Ubicación**: `services/cart/cart/events/publisher.py`

**1. `cart.item.added`**
```json
{
  "eventType": "cart.item.added",
  "timestamp": "2025-11-05T10:30:00Z",
  "data": {
    "userId": "user-123",
    "sku": "BOOK-001",
    "quantity": 2,
    "price": { "amount": "29.99", "currency": "USD" }
  }
}
```
- **Routing Key**: `cart.item.added`
- **Cuándo**: Usuario agrega item al carrito
- **Consumidores**: Ninguno (analítica potencial)

**2. `cart.item.removed`**
- **Routing Key**: `cart.item.removed`
- **Cuándo**: Usuario remueve item del carrito

**3. `cart.cleared`**
- **Routing Key**: `cart.cleared`
- **Cuándo**: Usuario vacía carrito O se completa orden

**Ubicación**: `services/order/order/events/publisher.py`

**1. `order.created` MÁS IMPORTANTE**
```json
{
  "eventType": "order.created",
  "timestamp": "2025-11-05T11:00:00Z",
  "data": {
    "orderId": "order-uuid-123",
    "userId": "user-123",
    "items": [
      {
        "sku": "BOOK-001",
        "quantity": 2,
        "price": { "amount": "29.99", "currency": "USD" }
      }
    ],
    "totalAmount": { "amount": "59.98", "currency": "USD" },
    "status": "pending"
  }
}
```
- **Routing Key**: `order.created`
- **Cuándo**: Orden creada exitosamente (después de reservar inventario y procesar pago)
- **Consumidores**: 
  - **Cart Service** (`cart/events/consumer.py`) → Vacía carrito del usuario
  - **Inventory Service** (`inventory/internal/events/consumer.go`) → Actualiza stock

**2. `order.status.changed`**
- **Routing Key**: `order.status.changed`
- **Cuándo**: Estado cambia (pending→paid→shipped→delivered)
- **Consumidores**: Potencial servicio de notificaciones

**3. `order.cancelled`**
```json
{
  "eventType": "order.cancelled",
  "data": {
    "orderId": "order-uuid-123",
    "items": [{ "sku": "BOOK-001", "quantity": 2 }]
  }
}
```
- **Routing Key**: `order.cancelled`
- **Cuándo**: Usuario o sistema cancela orden
- **Consumidores**: 
  - **Inventory Service** → Libera inventario reservado

### Inventory Events (Publisher: Inventory Service)
**Ubicación**: `services/inventory/internal/events/publisher.go`

**1. `inventory.reserved`**
```json
{
  "eventType": "inventory.reserved",
  "timestamp": "2025-11-05T11:00:00Z",
  "data": {
    "sku": "BOOK-001",
    "quantity": 2,
    "orderId": "order-uuid-123",
    "availableNow": 98
  }
}
```
- **Routing Key**: `inventory.reserved`
- **Cuándo**: Inventory reservado para una orden
- **Consumidores**: Ninguno (auditoría)

**2. `inventory.released`**
- **Routing Key**: `inventory.released`
- **Cuándo**: Reserva liberada (orden cancelada)

**3. `inventory.low_stock` **
```json
{
  "eventType": "inventory.low_stock",
  "data": {
    "sku": "BOOK-001",
    "currentStock": 5,
    "reorderPoint": 10,
    "reorderQuantity": 50
  }
}
```
- **Routing Key**: `inventory.low_stock`
- **Cuándo**: Stock disponible < reorder_point
- **Consumidores**: Potencial servicio de purchasing/alertas

### Tabla de Publishers y Consumers

| Servicio | Publica Eventos | Consume Eventos | Archivos |
|----------|----------------|-----------------|----------|
| **Catalog** | ✅ book.* | ❌ | `internal/events/publisher.go` |
| **Cart** | ✅ cart.* | ✅ order.created | `events/publisher.py`, `events/consumer.py` |
| **Order** | ❌ | ❌ | - |
| **User** | ❌ | ❌ | - |
| **Inventory** | ✅ inventory.* | ✅ order.cancelled | `internal/events/publisher.go`, `internal/events/consumer.go` |
| **Payment** | ❌ | ❌ | - |
| **Gateway** | ❌ | ❌ | - |
| **Frontend** | ❌ | ❌ | - |
