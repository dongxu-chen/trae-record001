import { Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import AppLayout from '@/components/layout/AppLayout';
import Dashboard from '@/pages/Dashboard';
import Clustering from '@/pages/Clustering';
import Rules from '@/pages/Rules';
import Optimizer from '@/pages/Optimizer';
import Evaluator from '@/pages/Evaluator';
import Report from '@/pages/Report';
import Settings from '@/pages/Settings';

const { Content } = Layout;

function App() {
  return (
    <AppLayout>
      <Content className="p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clustering" element={<Clustering />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/optimizer" element={<Optimizer />} />
          <Route path="/evaluator" element={<Evaluator />} />
          <Route path="/report" element={<Report />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Content>
    </AppLayout>
  );
}

export default App;
