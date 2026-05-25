import { Routes, Route } from 'react-router-dom';
import BoardList from '@/pages/BoardList';
import BoardDetail from '@/pages/BoardDetail';
import GanttView from '@/pages/GanttView';
import AutomationRules from '@/pages/AutomationRules';
import EfficiencyReport from '@/pages/EfficiencyReport';
import Layout from '@/components/Layout';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<BoardList />} />
        <Route path="/board/:id" element={<BoardDetail />} />
        <Route path="/board/:id/gantt" element={<GanttView />} />
        <Route path="/automation" element={<AutomationRules />} />
        <Route path="/efficiency" element={<EfficiencyReport />} />
      </Route>
    </Routes>
  );
}

export default App;
