import React, { useState, useEffect } from 'react'
import Login from './components/Login'
import CheckinPage from './pages/CheckinPage'
import Toast from './components/Toast'

function App() {
  const [user, setUser] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    const savedUser = localStorage.getItem('checkin_user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
    }
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    localStorage.setItem('checkin_user', JSON.stringify(userData))
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('checkin_user')
  }

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const updateUser = (updates) => {
    const newUser = { ...user, ...updates }
    setUser(newUser)
    localStorage.setItem('checkin_user', JSON.stringify(newUser))
  }

  return (
    <div className="app">
      {toast && <Toast message={toast.message} type={toast.type} />}
      
      {!user ? (
        <Login onLogin={handleLogin} showToast={showToast} />
      ) : (
        <CheckinPage 
          user={user} 
          onLogout={handleLogout} 
          showToast={showToast}
          updateUser={updateUser}
        />
      )}
    </div>
  )
}

export default App
