import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Store de autenticación usando Zustand
 * Persiste el token y datos del usuario en localStorage
 */
export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      // Establecer usuario y token al iniciar sesión
      setAuth: (token, user) => {
        localStorage.setItem('token', token)
        localStorage.setItem('user', JSON.stringify(user))
        set({ token, user, isAuthenticated: true })
      },

      // Limpiar usuario y token al cerrar sesión
      clearAuth: () => {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        set({ token: null, user: null, isAuthenticated: false })
      },

      // Actualizar datos del usuario
      updateUser: (userData) => {
        set((state) => ({
          user: { ...state.user, ...userData }
        }))
      },

      // Verificar si el usuario es admin
      isAdmin: () => {
        const state = get()
        return state.user?.role === 'ADMIN'
      },

      // Verificar si el usuario es cliente
      isClient: () => {
        const state = get()
        return state.user?.role === 'CLIENT'
      },
    }),
    {
      name: 'auth-storage',
      getStorage: () => localStorage,
    }
  )
)
