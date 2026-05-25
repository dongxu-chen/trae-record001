import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import IconLibrary from './pages/IconLibrary'
import IconDetail from './pages/IconDetail'
import Categories from './pages/Categories'
import Upload from './pages/Upload'
import Team from './pages/Team'
import AIGenerate from './pages/AIGenerate'
import Analytics from './pages/Analytics'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
      
      {isAuthenticated ? (
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="icons" element={<IconLibrary />} />
          <Route path="icons/:id" element={<IconDetail />} />
          <Route path="categories" element={<Categories />} />
          <Route path="upload" element={<Upload />} />
          <Route path="ai-generate" element={<AIGenerate />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="team" element={<Team />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/login" />} />
      )}
    </Routes>
  )
}

export default App
