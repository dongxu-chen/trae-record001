import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Rules from '@/pages/Rules';
import Tasks from '@/pages/Tasks';
import Reports from '@/pages/Reports';
import Issues from '@/pages/Issues';
import Trends from '@/pages/Trends';
import HealthScorePage from '@/pages/HealthScore';
import AutoFixPage from '@/pages/AutoFix';
import Board from '@/pages/Board';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/issues" element={<Issues />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/health-score" element={<HealthScorePage />} />
          <Route path="/auto-fix" element={<AutoFixPage />} />
          <Route path="/board" element={<Board />} />
        </Route>
      </Routes>
    </Router>
  );
}
