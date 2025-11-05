import { create } from 'zustand'

/**
 * Store del carrito usando Zustand
 */
export const useCartStore = create((set) => ({
  items: [],
  total: 0,

  // Establecer items del carrito
  setItems: (items) => {
    const total = items.reduce((sum, item) => sum + (item.price * item.quantity), 0)
    set({ items, total })
  },

  // Agregar item al carrito
  addItem: (item) => {
    set((state) => {
      const existingItem = state.items.find(i => i.bookId === item.bookId)
      
      let newItems
      if (existingItem) {
        // Incrementar cantidad si ya existe
        newItems = state.items.map(i =>
          i.bookId === item.bookId
            ? { ...i, quantity: i.quantity + item.quantity }
            : i
        )
      } else {
        // Agregar nuevo item
        newItems = [...state.items, item]
      }
      
      const total = newItems.reduce((sum, i) => sum + (i.price * i.quantity), 0)
      return { items: newItems, total }
    })
  },

  // Actualizar cantidad de un item
  updateQuantity: (bookId, quantity) => {
    set((state) => {
      const newItems = state.items.map(item =>
        item.bookId === bookId ? { ...item, quantity } : item
      )
      const total = newItems.reduce((sum, item) => sum + (item.price * item.quantity), 0)
      return { items: newItems, total }
    })
  },

  // Remover item del carrito
  removeItem: (bookId) => {
    set((state) => {
      const newItems = state.items.filter(item => item.bookId !== bookId)
      const total = newItems.reduce((sum, item) => sum + (item.price * item.quantity), 0)
      return { items: newItems, total }
    })
  },

  // Limpiar carrito
  clearCart: () => {
    set({ items: [], total: 0 })
  },
}))
