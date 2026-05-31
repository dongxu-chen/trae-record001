import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import Editor from '@/pages/Editor';
import Templates from '@/pages/Templates';
import Batch from '@/pages/Batch';
import ExportPage from '@/pages/Export';
import AIDesign from '@/pages/AIDesign';
import BalanceAnalysis from '@/pages/BalanceAnalysis';
import BattleSim from '@/pages/BattleSim';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/editor" element={<Editor />} />
          <Route path="/templates" element={<Templates />} />
          <Route path="/batch" element={<Batch />} />
          <Route path="/export" element={<ExportPage />} />
          <Route path="/ai-design" element={<AIDesign />} />
          <Route path="/balance" element={<BalanceAnalysis />} />
          <Route path="/battle" element={<BattleSim />} />
        </Route>
      </Routes>
    </Router>
  );
}
