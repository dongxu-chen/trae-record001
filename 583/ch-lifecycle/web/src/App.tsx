import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Policies from '@/pages/Policies';
import Partitions from '@/pages/Partitions';
import Tiering from '@/pages/Tiering';
import Advisor from '@/pages/Advisor';
import Archive from '@/pages/Archive';
import RouterPage from '@/pages/Router';
import Simulator from '@/pages/Simulator';
import Monitor from '@/pages/Monitor';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/partitions" element={<Partitions />} />
          <Route path="/tiering" element={<Tiering />} />
          <Route path="/advisor" element={<Advisor />} />
          <Route path="/archive" element={<Archive />} />
          <Route path="/router" element={<RouterPage />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/monitor" element={<Monitor />} />
        </Route>
      </Routes>
    </Router>
  );
}
