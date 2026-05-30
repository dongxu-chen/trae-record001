import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import AlertConfig from '@/pages/AlertConfig';
import AlertHistory from '@/pages/AlertHistory';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/config" element={<AlertConfig />} />
          <Route path="/history" element={<AlertHistory />} />
        </Route>
      </Routes>
    </Router>
  );
}
