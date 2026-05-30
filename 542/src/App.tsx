import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Workspace from '@/pages/Workspace';
import Report from '@/pages/Report';
import BatchScan from '@/pages/BatchScan';
import UserTesting from '@/pages/UserTesting';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Workspace />} />
          <Route path="/report" element={<Report />} />
          <Route path="/batch-scan" element={<BatchScan />} />
          <Route path="/user-testing" element={<UserTesting />} />
        </Routes>
      </Layout>
    </Router>
  );
}
