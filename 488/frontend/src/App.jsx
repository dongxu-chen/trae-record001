import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Activity, AlertTriangle, History, Settings, BarChart3, Database, Lightbulb, FlaskConical, FileText } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Deadlocks from './pages/Deadlocks'
import HistoryPage from './pages/History'
import Rules from './pages/Rules'
import Statistics from './pages/Statistics'
import Config from './pages/Config'
import Prevention from './pages/Prevention'
import Sandbox from './pages/Sandbox'
import Audit from './pages/Audit'

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h1>死锁检测工具</h1>
            <p>Deadlock Resolver</p>
          </div>
          <nav>
            <ul className="nav-menu">
              <li>
                <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Activity size={20} />
                  <span>仪表板</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/deadlocks" className={({ isActive }) => isActive ? 'active' : ''}>
                  <AlertTriangle size={20} />
                  <span>当前死锁</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>
                  <History size={20} />
                  <span>历史记录</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/rules" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Database size={20} />
                  <span>规则引擎</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/prevention" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Lightbulb size={20} />
                  <span>预防建议</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/sandbox" className={({ isActive }) => isActive ? 'active' : ''}>
                  <FlaskConical size={20} />
                  <span>演练沙箱</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/audit" className={({ isActive }) => isActive ? 'active' : ''}>
                  <FileText size={20} />
                  <span>审计日志</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/statistics" className={({ isActive }) => isActive ? 'active' : ''}>
                  <BarChart3 size={20} />
                  <span>统计分析</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/config" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Settings size={20} />
                  <span>系统配置</span>
                </NavLink>
              </li>
            </ul>
          </nav>
        </aside>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/deadlocks" element={<Deadlocks />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/rules" element={<Rules />} />
            <Route path="/prevention" element={<Prevention />} />
            <Route path="/sandbox" element={<Sandbox />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/config" element={<Config />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
