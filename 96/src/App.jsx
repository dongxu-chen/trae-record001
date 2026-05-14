import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Timer from './pages/Timer'
import Tasks from './pages/Tasks'
import Settings from './pages/Settings'
import Stats from './pages/Stats'
import './App.css'

function Navigation() {
  const location = useLocation()
  
  const navItems = [
    { path: '/', label: '🍅 番茄时钟', exact: true },
    { path: '/tasks', label: '📋 任务看板' },
    { path: '/stats', label: '📊 统计分析' },
    { path: '/settings', label: '⚙️ 设置' }
  ]

  const isActive = (item) => {
    if (item.exact) {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(item.path)
  }

  return (
    <nav className="nav-container">
      <div className="nav-logo">🍅 Pomodoro</div>
      <div className="nav-links">
        {navItems.map((item) => (
          <Link 
            key={item.path}
            to={item.path} 
            className={`nav-link ${isActive(item) ? 'active' : ''}`}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="app">
        <Navigation />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Timer />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
