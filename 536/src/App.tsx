import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import TransactionList from "@/pages/TransactionList";
import TransactionDetail from "@/pages/TransactionDetail";
import TraceHome from "@/pages/TraceHome";
import TraceVisualization from "@/pages/TraceVisualization";
import Alerts from "@/pages/Alerts";
import Diagnosis from "@/pages/Diagnosis";
import PressureTest from "@/pages/PressureTest";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<TransactionList />} />
          <Route path="/transactions/:xid" element={<TransactionDetail />} />
          <Route path="/trace" element={<TraceHome />} />
          <Route path="/trace/:traceId" element={<TraceVisualization />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/diagnosis" element={<Diagnosis />} />
          <Route path="/diagnosis/:xid" element={<Diagnosis />} />
          <Route path="/pressure-test" element={<PressureTest />} />
        </Route>
      </Routes>
    </Router>
  );
}
