import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import Dashboard from '@/pages/Dashboard';
import Vulnerabilities from '@/pages/Vulnerabilities';
import Upgrades from '@/pages/Upgrades';
import Repositories from '@/pages/Repositories';
import ServiceDetail from '@/pages/ServiceDetail';
import CveDetail from '@/pages/CveDetail';
import Health from '@/pages/Health';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/vulnerabilities" element={<Vulnerabilities />} />
          <Route path="/vulnerabilities/:cveId" element={<CveDetail />} />
          <Route path="/upgrades" element={<Upgrades />} />
          <Route path="/repositories" element={<Repositories />} />
          <Route path="/services/:id" element={<ServiceDetail />} />
          <Route path="/health" element={<Health />} />
        </Route>
      </Routes>
    </Router>
  );
}
