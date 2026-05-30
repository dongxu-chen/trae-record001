import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Analytics from "@/pages/Analytics";
import Guide from "@/pages/Guide";
import Reserve from "@/pages/Reserve";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/guide" element={<Guide />} />
          <Route path="/reserve" element={<Reserve />} />
        </Route>
      </Routes>
    </Router>
  );
}
