import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import Login from '@/pages/Login'
import Projects from '@/pages/Projects'
import Annotate from '@/pages/Annotate'
import Statistics from '@/pages/Statistics'
import Layout from '@/components/Layout'

function App() {
  const { user } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/projects" />} />
      
      <Route element={<Layout />}>
        <Route path="/projects" element={user ? <Projects /> : <Navigate to="/login" />} />
        <Route path="/annotate/:projectId" element={user ? <Annotate /> : <Navigate to="/login" />} />
        <Route path="/statistics/:projectId" element={user ? <Statistics /> : <Navigate to="/login" />} />
        <Route path="/" element={<Navigate to={user ? "/projects" : "/login"} />} />
      </Route>
    </Routes>
  )
}

export default App
