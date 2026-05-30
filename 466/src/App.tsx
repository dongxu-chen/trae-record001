import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Rules from "@/pages/Rules";
import RuleEditor from "@/pages/RuleEditor";
import Scores from "@/pages/Scores";
import Alerts from "@/pages/Alerts";
import ImpactAnalysis from "@/pages/ImpactAnalysis";

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/rules/new" element={<RuleEditor />} />
          <Route path="/rules/:id" element={<RuleEditor />} />
          <Route path="/scores" element={<Scores />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/impact" element={<ImpactAnalysis />} />
        </Routes>
      </Layout>
    </Router>
  );
}
