import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppProvider } from './contexts/AppContext'
import { Header } from './components/Header'
import { LoadingSpinner } from './components/LoadingSpinner'
import { TextTranslation } from './pages/TextTranslation'
import { DocumentTranslation } from './pages/DocumentTranslation'
import { TermManagement } from './pages/TermManagement'
import { TranslationMemoryPage } from './pages/TranslationMemory'
import { WebTranslation } from './pages/WebTranslation'
import { Settings } from './pages/Settings'

const App: React.FC = () => {
  return (
    <AppProvider>
      <div className="min-h-screen bg-gray-100">
        <Header />
        <React.Suspense
          fallback={
            <div className="flex items-center justify-center h-96">
              <LoadingSpinner size="lg" text="加载中..." />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<TextTranslation />} />
            <Route path="/document" element={<DocumentTranslation />} />
            <Route path="/terms" element={<TermManagement />} />
            <Route path="/memory" element={<TranslationMemoryPage />} />
            <Route path="/plugin" element={<WebTranslation />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </React.Suspense>
      </div>
    </AppProvider>
  )
}

export default App
