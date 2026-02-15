import { create } from 'zustand'
import { api } from '../services/api'

interface User {
  id: string
  email: string
  username: string
  full_name?: string
  is_admin?: boolean
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  setToken: (token: string, refreshToken: string) => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('token'),
  refreshToken: localStorage.getItem('refreshToken'),
  user: null,
  
  loadUser: async () => {
    const token = get().token
    if (token) {
      try {
        const userResponse = await api.get('/api/auth/me')
        set({ user: userResponse.data })
      } catch {
        get().logout()
      }
    }
  },
  
  login: async (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await api.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    const { access_token, refresh_token } = response.data
    localStorage.setItem('token', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    
    set({ token: access_token, refreshToken: refresh_token })
    
    const userResponse = await api.get('/api/auth/me')
    set({ user: userResponse.data })
  },
  
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    set({ token: null, refreshToken: null, user: null })
  },
  
  setToken: (token: string, refreshToken: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('refreshToken', refreshToken)
    set({ token, refreshToken })
  },
}))
