import React, { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import HistoryPage from './pages/HistoryPage'
import DevicesPage from './pages/DevicesPage'
import SettingsPage from './pages/SettingsPage'
import DashboardPage from './pages/DashboardPage'
import QuickPasteModal from './components/QuickPasteModal'
import { useApp } from './context/AppContext'

const App: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { showQuickPaste, setShowQuickPaste } = useApp()

  return (
    <div className="flex h-full bg-gray-50">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<HistoryPage />} />
            <Route path="/devices" element={<DevicesPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
      
      {showQuickPaste && (
        <QuickPasteModal onClose={() => setShowQuickPaste(false)} />
      )}
    </div>
  )
}

export default App
