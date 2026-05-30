import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/MainLayout'
import RuleList from './pages/RuleList'
import RuleEditor from './pages/RuleEditor'
import RuleVisualEditor from './pages/RuleVisualEditor'
import SimulateTest from './pages/SimulateTest'
import HitAnalysis from './pages/HitAnalysis'
import Dashboard from './pages/Dashboard'
import ConflictDetection from './pages/ConflictDetection'
import ABTest from './pages/ABTest'
import EffectEvaluation from './pages/EffectEvaluation'

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/rules" element={<RuleList />} />
        <Route path="/rules/create" element={<RuleEditor />} />
        <Route path="/rules/edit/:id" element={<RuleEditor />} />
        <Route path="/rules/visual" element={<RuleVisualEditor />} />
        <Route path="/simulate" element={<SimulateTest />} />
        <Route path="/analysis" element={<HitAnalysis />} />
        <Route path="/conflicts" element={<ConflictDetection />} />
        <Route path="/abtest" element={<ABTest />} />
        <Route path="/evaluation" element={<EffectEvaluation />} />
      </Routes>
    </MainLayout>
  )
}

export default App
