import { create } from 'zustand'
import { User } from '@/types'

interface AuthState {
  user: User | null
  token: string | null
  login: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => {
  const savedUser = localStorage.getItem('user')
  const savedToken = localStorage.getItem('token')

  return {
    user: savedUser ? JSON.parse(savedUser) : null,
    token: savedToken,
    login: (user, token) => {
      localStorage.setItem('user', JSON.stringify(user))
      localStorage.setItem('token', token)
      set({ user, token })
    },
    logout: () => {
      localStorage.removeItem('user')
      localStorage.removeItem('token')
      set({ user: null, token: null })
    },
  }
})
